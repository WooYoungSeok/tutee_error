"""Dataset adapters: raw source records -> normalized pilot records.

Each adapter yields one :class:`NormalizedRecord` per raw record, including the
records it marks ineligible, so that exclusion reasons can be reported.

No mathematical content is rewritten here. Text is taken verbatim; the only
transformation applied to a solution is joining a list of steps with newlines
(the original list is kept under ``annotations``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from .paths import RAW_DIR
from .util import question_group_id, read_jsonl, sha256_text

# ---------------------------------------------------------------------------
# Normalized record
# ---------------------------------------------------------------------------


@dataclass
class NormalizedRecord:
    sample_id: str
    dataset: str
    source_id: str
    source_file: str
    source_revision: str
    question: str
    incorrect_solution: str
    source_error_label: str
    annotations: dict[str, Any] = field(default_factory=dict)
    question_group_id: str = ""
    stratum: str = ""
    eligible: bool = True
    exclusion_reason: str = ""
    split: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_sample_id(dataset: str, question: str, solution: str, label: str) -> str:
    digest = sha256_text("␟".join([question.strip(), solution.strip(), label.strip()]))
    return f"{dataset}:{digest[:16]}"


def _build(
    dataset: str,
    source_id: str,
    source_file: str,
    revision: str,
    question: Any,
    solution: Any,
    label: Any,
    annotations: dict[str, Any],
    stratum: str,
) -> NormalizedRecord:
    question_text = question if isinstance(question, str) else ""
    solution_text = solution if isinstance(solution, str) else ""
    label_text = label if isinstance(label, str) else ""

    missing = [
        name
        for name, value in (
            ("question", question_text),
            ("incorrect_solution", solution_text),
            ("source_error_label", label_text),
        )
        if not value.strip()
    ]
    record = NormalizedRecord(
        sample_id=make_sample_id(dataset, question_text, solution_text, label_text),
        dataset=dataset,
        source_id=source_id,
        source_file=source_file,
        source_revision=revision,
        question=question_text,
        incorrect_solution=solution_text,
        source_error_label=label_text,
        annotations=annotations,
        question_group_id=question_group_id(question_text) if question_text.strip() else "",
        stratum=stratum,
    )
    if missing:
        record.eligible = False
        record.exclusion_reason = "missing_field:" + ",".join(missing)
    return record


# ---------------------------------------------------------------------------
# Stepwise Verification (eth-lre/verify-then-generate)
# ---------------------------------------------------------------------------

STEPWISE_FILE = "dataset/dataset.json"
STEPWISE_NON_ERROR_LABELS = {"none of the above", "none", "no error"}
STEPWISE_ANNOTATION_KEYS = (
    "incorrect_index",
    "incorrect_step",
    "error_description",
    "reference_solution",
    "dialog_history",
    "student_correct_response",
    "topic",
)


def adapt_stepwise(revision: str = "") -> Iterator[NormalizedRecord]:
    path = RAW_DIR / "stepwise" / STEPWISE_FILE
    rows = json.loads(path.read_text(encoding="utf-8"))
    for index, row in enumerate(rows):
        solution = row.get("student_incorrect_solution")
        annotations = {k: row.get(k) for k in STEPWISE_ANNOTATION_KEYS if k in row}
        if isinstance(solution, list):
            annotations["student_incorrect_solution_steps"] = solution
            solution_text = "\n".join(str(step) for step in solution)
        else:
            solution_text = solution if isinstance(solution, str) else ""
        label = row.get("error_category") or ""
        record = _build(
            dataset="stepwise",
            source_id=f"{STEPWISE_FILE}#{index}",
            source_file=f"data/raw/stepwise/{STEPWISE_FILE}",
            revision=revision,
            question=row.get("problem"),
            solution=solution_text,
            label=label,
            annotations=annotations,
            stratum=label.strip(),
        )
        if record.eligible and label.strip().lower() in STEPWISE_NON_ERROR_LABELS:
            record.eligible = False
            record.exclusion_reason = "non_error_label"
        yield record


# ---------------------------------------------------------------------------
# MathClean (MeiyiQiang/MathClean)
# ---------------------------------------------------------------------------

MATHCLEAN_ELIGIBLE_FILES = (
    "check_type_answer/simple.json",
    "check_type_answer/challenging.json",
)
MATHCLEAN_LABELS = ("logic error", "computing error", "expression error")


def adapt_mathclean(revision: str = "") -> Iterator[NormalizedRecord]:
    for rel in MATHCLEAN_ELIGIBLE_FILES:
        path = RAW_DIR / "mathclean" / rel
        if not path.exists():
            continue
        difficulty = Path(rel).stem  # simple | challenging
        rows = json.loads(path.read_text(encoding="utf-8"))
        for index, row in enumerate(rows):
            label = row.get("type") or ""
            annotations = {
                "extent": row.get("extent"),
                "difficulty_file": difficulty,
                "subset": str(Path(rel).parent),
            }
            record = _build(
                dataset="mathclean",
                source_id=f"{rel}#{index}",
                source_file=f"data/raw/mathclean/{rel}",
                revision=revision,
                question=row.get("question"),
                # `answer` is the solution under evaluation in this file, not a gold answer.
                solution=row.get("answer"),
                label=label,
                annotations=annotations,
                stratum=label.strip(),
            )
            if record.eligible and label.strip().lower() not in MATHCLEAN_LABELS:
                record.eligible = False
                record.exclusion_reason = f"label_outside_error_types:{label}"
            yield record


# ---------------------------------------------------------------------------
# EIC (LittleCirc1e/EIC)
# ---------------------------------------------------------------------------

# The pilot sample reads GSM8K only; the full labeling run adds MathQA through
# config (eic.benchmarks). Other EIC folders (incomplete_*, step_number_*,
# EP_robustness_*) are not read: they repeat these cases or add no new error.
EIC_BENCHMARKS = ("GSM8K", "MathQA")
EIC_DEFAULT_BENCHMARKS = ("GSM8K",)
EIC_CANONICAL_TYPES = (
    "adding_irrelevant_information",
    "calculation_error",
    "confusing_formula_error",
    "counting_error",
    "missing_step",
    "operator_error",
    "referencing_context_value_error",
    "referencing_previous_step_value_error",
    "unit_conversion_error",
)
EIC_ANNOTATION_KEYS = (
    "original_solution",
    "original_answer",
    "transformed_answer",
    "wrong_step",
    "explanation",
    "is_single_error",
)


def eic_root(benchmark: str) -> Path:
    return RAW_DIR / "eic" / "data" / f"generated_cases_{benchmark}"


def adapt_eic(
    revision: str = "", benchmarks: Iterable[str] | None = None
) -> Iterator[NormalizedRecord]:
    for benchmark in benchmarks or EIC_DEFAULT_BENCHMARKS:
        if benchmark not in EIC_BENCHMARKS:
            raise ValueError(f"unknown EIC benchmark: {benchmark}")
        yield from _adapt_eic_benchmark(revision, benchmark)


def _adapt_eic_benchmark(revision: str, benchmark: str) -> Iterator[NormalizedRecord]:
    root = eic_root(benchmark)
    if not root.exists():
        return
    for type_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        # `wrong_step_calculation_error` is a step-position ablation over the same
        # calculation_error label, not one of the nine error types; skipped here
        # and reported in the data inspection report.
        skip_dir = type_dir.name not in EIC_CANONICAL_TYPES
        for path in sorted(type_dir.rglob("generated_cases_clean.jsonl")):
            rel = str(path.relative_to(RAW_DIR / "eic")).replace("\\", "/")
            for index, row in enumerate(read_jsonl(path)):
                label = row.get("wrong_type") or ""
                annotations = {k: row.get(k) for k in EIC_ANNOTATION_KEYS if k in row}
                annotations["type_dir"] = type_dir.name
                annotations["source_benchmark"] = benchmark
                record = _build(
                    dataset="eic",
                    source_id=f"{rel}#{index}",
                    source_file=f"data/raw/eic/{rel}",
                    revision=revision,
                    question=row.get("question"),
                    solution=row.get("transformed_solution"),
                    label=label,
                    annotations=annotations,
                    stratum=label.strip(),
                )
                if record.eligible and skip_dir:
                    record.eligible = False
                    record.exclusion_reason = f"non_error_type_directory:{type_dir.name}"
                elif record.eligible and label.strip() not in EIC_CANONICAL_TYPES:
                    record.eligible = False
                    record.exclusion_reason = f"label_outside_canonical_set:{label}"
                elif record.eligible and row.get("is_single_error") is not True:
                    record.eligible = False
                    record.exclusion_reason = "is_single_error_not_true"
                yield record


# ---------------------------------------------------------------------------
# MathEDU (NYCU-NLP-Lab/MathEDU) + MathQA question texts
# ---------------------------------------------------------------------------

# The records carry no question text: `id` indexes into the concatenation of the
# MathQA train, validation and test splits, exactly as MathEDU's own
# create_finetuned_data.py does (datasets.concatenate_datasets on math_qa).
MATHQA_FILES = ("train.json", "dev.json", "test.json")
MATHEDU_POOL_FILES = (
    "dataset/time_series_split/train.json",
    "dataset/time_series_split/val.json",
    "dataset/time_series_split/test.json",
)
MATHEDU_ANNOTATION_KEYS = (
    "student_id",
    "student_answer",
    "correct_or_not",
    "the_reason_why_student_cant_solve_ch",
    "the_reason_why_student_cant_solve_en",
)
MATHQA_ANNOTATION_KEYS = ("options", "correct", "category", "Rationale")


class MissingQuestionSource(RuntimeError):
    """Raised when the MathQA question texts needed by MathEDU are not available."""


def load_mathqa_index() -> list[dict]:
    """MathQA records in the order MathEDU ids refer to (train + validation + test)."""
    root = RAW_DIR / "mathqa"
    records: list[dict] = []
    for name in MATHQA_FILES:
        path = root / name
        if not path.exists():
            raise MissingQuestionSource(
                f"MathQA file missing: {path}. Run scripts/fetch_sources.py --datasets mathqa"
            )
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def adapt_mathedu(revision: str = "", field_map: dict[str, Any] | None = None) -> Iterator[NormalizedRecord]:
    root = RAW_DIR / "mathedu"
    pool_files = [root / rel for rel in MATHEDU_POOL_FILES]
    if not all(path.exists() for path in pool_files):
        # fall back to a user-supplied drop-in copy described by the config
        yield from adapt_mathedu_custom(revision=revision, field_map=field_map)
        return

    mathqa = load_mathqa_index()
    for path, rel in zip(pool_files, MATHEDU_POOL_FILES):
        split_name = Path(rel).stem
        rows = json.loads(path.read_text(encoding="utf-8"))
        for index, row in enumerate(rows):
            review = row.get("teacher_review") or {}
            errors = review.get("error") or []
            annotations: dict[str, Any] = {
                k: row.get(k) for k in MATHEDU_ANNOTATION_KEYS if k in row
            }
            annotations["mathedu_id"] = row.get("id")
            annotations["mathedu_split_file"] = split_name
            annotations["error_counts"] = review.get("error_counts")
            annotations["teacher_review_errors"] = errors

            qa_index = row.get("id")
            question = ""
            if isinstance(qa_index, int) and 0 <= qa_index < len(mathqa):
                qa = mathqa[qa_index]
                question = qa.get("Problem", "")
                for key in MATHQA_ANNOTATION_KEYS:
                    annotations[f"mathqa_{key.lower()}"] = qa.get(key)

            label = ""
            if len(errors) == 1:
                label = str(errors[0].get("error_type") or "").strip()
                annotations["error_equation"] = errors[0].get("error_equation")
                annotations["teacher_advice_en"] = errors[0].get("teacher_advice_en")
                annotations["teacher_advice_ch"] = errors[0].get("teacher_advice_ch")

            record = _build(
                dataset="mathedu",
                source_id=f"{rel}#{index}",
                source_file=f"data/raw/mathedu/{rel}",
                revision=revision,
                question=question,
                solution=row.get("student_process"),
                label=label,
                annotations=annotations,
                stratum=label,
            )
            reason = ""
            if str(row.get("correct_or_not", "")).strip().lower() != "wrong":
                reason = f"not_an_incorrect_answer:{row.get('correct_or_not')}"
            elif not errors:
                reason = "no_teacher_annotated_error"
            elif len(errors) > 1:
                # A must stay one original label; multi-error cases are reported, not merged.
                reason = f"multiple_annotated_errors:{len(errors)}"
            elif not question.strip():
                reason = "mathqa_question_not_found"
            if reason:
                record.eligible = False
                record.exclusion_reason = reason
            yield record


class MissingFieldMapping(RuntimeError):
    """Raised when MathEDU files exist but the config does not say how to read them."""


def _iter_rows(path: Path) -> Iterator[tuple[int, dict]]:
    if path.suffix.lower() == ".jsonl":
        for index, row in enumerate(read_jsonl(path)):
            yield index, row
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("data", "records", "items", "examples"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise MissingFieldMapping(
            f"{path}: expected a list of records (or a dict holding one); got {type(data).__name__}"
        )
    for index, row in enumerate(data):
        if isinstance(row, dict):
            yield index, row


def adapt_mathedu_custom(revision: str = "", field_map: dict[str, Any] | None = None) -> Iterator[NormalizedRecord]:
    """Generic reader for a user-supplied MathEDU copy described by config.field_map."""
    root = RAW_DIR / "mathedu"
    if not root.exists():
        return
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in {".json", ".jsonl"})
    if not files:
        return
    field_map = field_map or {}
    required = ("question", "incorrect_solution", "source_error_label")
    missing = [key for key in required if not field_map.get(key)]
    if missing:
        discovered: set[str] = set()
        for path in files[:3]:
            for _, row in _iter_rows(path):
                discovered.update(row.keys())
                break
        raise MissingFieldMapping(
            "MathEDU files are present but config mathedu.field_map is incomplete "
            f"(missing: {', '.join(missing)}). Keys found in the files: "
            f"{sorted(discovered)}"
        )
    annotation_keys = field_map.get("annotations") or []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        for index, row in _iter_rows(path):
            label = row.get(field_map["source_error_label"]) or ""
            annotations = {k: row.get(k) for k in annotation_keys if k in row}
            if field_map.get("group_by"):
                annotations[field_map["group_by"]] = row.get(field_map["group_by"])
            yield _build(
                dataset="mathedu",
                source_id=f"{rel}#{index}",
                source_file=f"data/raw/mathedu/{rel}",
                revision=revision,
                question=row.get(field_map["question"]),
                solution=row.get(field_map["incorrect_solution"]),
                label=label if isinstance(label, str) else str(label),
                annotations=annotations,
                stratum=str(label).strip(),
            )


ADAPTERS = {
    "stepwise": adapt_stepwise,
    "mathclean": adapt_mathclean,
    "eic": adapt_eic,
    "mathedu": adapt_mathedu,
}


def normalize_dataset(dataset: str, revision: str = "", config: dict | None = None) -> list[NormalizedRecord]:
    config = config or {}
    if dataset == "mathedu":
        return list(adapt_mathedu(revision=revision, field_map=config.get("field_map")))
    if dataset == "eic":
        return list(adapt_eic(revision=revision, benchmarks=config.get("benchmarks")))
    return list(ADAPTERS[dataset](revision=revision))
