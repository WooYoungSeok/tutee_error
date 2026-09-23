"""Source registry and provenance-recording downloader.

Every file is downloaded from a pinned revision when the host exposes one, and
recorded with its URL, revision, byte size and SHA-256 in
``data/raw/source_manifest.json``.
"""

from __future__ import annotations

import fnmatch
import json
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import PROJECT_ROOT, RAW_DIR, SOURCE_MANIFEST
from .util import read_json, sha256_bytes, utc_now, write_json

USER_AGENT = "errdesc-pilot/0.1 (research data collection)"
TIMEOUT = 120


@dataclass
class SourceSpec:
    dataset: str
    kind: str  # github | hf_dataset | manual
    repo: str = ""
    ref: str = ""
    files: list[str] = field(default_factory=list)  # exact paths or glob patterns
    homepage: str = ""
    note: str = ""


SOURCES: dict[str, SourceSpec] = {
    "stepwise": SourceSpec(
        dataset="stepwise",
        kind="github",
        repo="eth-lre/verify-then-generate",
        ref="main",
        files=["dataset/dataset.json"],
        homepage="https://github.com/eth-lre/verify-then-generate",
    ),
    "mathclean": SourceSpec(
        dataset="mathclean",
        kind="hf_dataset",
        repo="MeiyiQiang/MathClean",
        ref="main",
        files=["*.json"],  # all json files in the repo; eligibility is decided later
        homepage="https://huggingface.co/datasets/MeiyiQiang/MathClean",
    ),
    "eic": SourceSpec(
        dataset="eic",
        kind="github",
        repo="LittleCirc1e/EIC",
        ref="master",
        files=[
            "data/generated_cases_GSM8K/*/*/generated_cases_clean.jsonl",
            "data/generated_cases_MathQA/*/*/generated_cases_clean.jsonl",
        ],
        homepage="https://github.com/LittleCirc1e/EIC",
    ),
    "mathedu": SourceSpec(
        dataset="mathedu",
        kind="github",
        repo="NYCU-NLP-Lab/MathEDU",
        ref="main",
        files=["dataset/*/*.json", "dataset/*/*/*.json", "README.md"],
        homepage="https://github.com/NYCU-NLP-Lab/MathEDU",
        note=(
            "Student records only. The question text lives in MathQA: the record "
            "id indexes concat(MathQA train, validation, test) - see the mathqa entry."
        ),
    ),
    "mathqa": SourceSpec(
        dataset="mathqa",
        kind="zip_url",
        repo="https://math-qa.github.io/math-QA/data/MathQA.zip",
        files=["train.json", "dev.json", "test.json"],
        homepage="https://math-qa.github.io/math-QA/",
        note="Question source for MathEDU; not sampled on its own.",
    ),
}


def _request(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read()


def _get_json(url: str) -> Any:
    return json.loads(_request(url, accept="application/json"))


def resolve_github(spec: SourceSpec) -> tuple[str, list[str]]:
    """Return (commit_sha, matched_paths) for the files selected by the spec."""
    commit = _get_json(f"https://api.github.com/repos/{spec.repo}/commits/{spec.ref}")
    sha = commit["sha"]
    tree = _get_json(f"https://api.github.com/repos/{spec.repo}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError(f"{spec.repo}: git tree listing was truncated")
    paths = [e["path"] for e in tree["tree"] if e["type"] == "blob"]
    matched = [p for p in paths if any(fnmatch.fnmatch(p, pat) for pat in spec.files)]
    return sha, sorted(matched)


def resolve_hf(spec: SourceSpec) -> tuple[str, list[str]]:
    info = _get_json(f"https://huggingface.co/api/datasets/{spec.repo}?full=true")
    sha = info["sha"]
    names = [s["rfilename"] for s in info.get("siblings", [])]
    matched = [
        name
        for name in names
        if any(
            fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(Path(name).name, pat)
            for pat in spec.files
        )
    ]
    return sha, sorted(matched)


def fetch_zip(spec: SourceSpec, dataset: str, force: bool) -> dict[str, Any]:
    """Download a zip archive once and extract the named members."""
    import io
    import zipfile

    entry: dict[str, Any] = {"files": []}
    target_dir = RAW_DIR / dataset
    missing = [name for name in spec.files if not (target_dir / name).exists()]
    if missing or force:
        data = _request(spec.repo)
        entry["archive"] = {
            "url": spec.repo,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            for name in spec.files:
                members = [n for n in names if n == name or n.endswith("/" + name)]
                members = [n for n in members if not n.startswith("__MACOSX/")]
                if not members:
                    raise RuntimeError(f"{spec.repo}: member not found in archive: {name}")
                payload = archive.read(members[0])
                target = target_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
    for name in spec.files:
        target = target_dir / name
        payload = target.read_bytes()
        entry["files"].append(
            {
                "path": name,
                "local_path": _rel(target),
                "url": f"{spec.repo}#{name}",
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "status": "extracted" if (missing or force) else "cached",
            }
        )
    return entry


def file_url(spec: SourceSpec, revision: str, path: str) -> str:
    if spec.kind == "github":
        return f"https://raw.githubusercontent.com/{spec.repo}/{revision}/{path}"
    if spec.kind == "hf_dataset":
        return f"https://huggingface.co/datasets/{spec.repo}/resolve/{revision}/{path}"
    raise ValueError(f"no download URL for kind={spec.kind}")


def local_path(dataset: str, path: str) -> Path:
    return RAW_DIR / dataset / path


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def load_source_manifest() -> dict:
    if SOURCE_MANIFEST.exists():
        return read_json(SOURCE_MANIFEST)
    return {"datasets": {}}


def save_source_manifest(manifest: dict) -> None:
    write_json(SOURCE_MANIFEST, manifest)


def fetch_dataset(dataset: str, force: bool = False) -> dict:
    """Download one dataset and return its provenance manifest entry."""
    spec = SOURCES[dataset]
    entry: dict[str, Any] = {
        "dataset": dataset,
        "kind": spec.kind,
        "repo": spec.repo,
        "homepage": spec.homepage,
        "fetched_at_utc": utc_now(),
        "files": [],
    }

    if spec.kind == "manual":
        root = RAW_DIR / dataset
        present = sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
        entry["status"] = "user_supplied" if present else "unavailable"
        entry["note"] = spec.note
        for path in present:
            data = path.read_bytes()
            entry["files"].append(
                {
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "local_path": _rel(path),
                    "url": "(user supplied)",
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "status": "user_supplied",
                }
            )
        return entry

    if spec.kind == "zip_url":
        zip_entry = fetch_zip(spec, dataset, force)
        entry.update(zip_entry)
        entry["note"] = spec.note
        entry["status"] = "ok" if entry["files"] else "no_files_matched"
        return entry

    if spec.kind == "github":
        revision, matched = resolve_github(spec)
    elif spec.kind == "hf_dataset":
        revision, matched = resolve_hf(spec)
    else:  # pragma: no cover - guarded by the registry
        raise ValueError(spec.kind)

    entry["revision"] = revision
    if spec.note:
        entry["note"] = spec.note
    for path in matched:
        url = file_url(spec, revision, path)
        target = local_path(dataset, path)
        if target.exists() and not force:
            data = target.read_bytes()
            status = "cached"
        else:
            data = _request(url)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            status = "downloaded"
        entry["files"].append(
            {
                "path": path,
                "local_path": _rel(target),
                "url": url,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "status": status,
            }
        )
    entry["status"] = "ok" if entry["files"] else "no_files_matched"
    return entry
