#!/usr/bin/env bash
# One-time additions for the Newman experiment, after the two existing environments exist:
#   (cd ../rl && bash setup_server.sh)             # ~/venv/rl    (vLLM 0.30, TRL 1.14, torch 2.13+cu129)
#   (cd ../verifier_sft && bash setup_server.sh)   # ~/venv/tutee (torch 2.11+cu128, transformers 5.17, DeepSpeed 0.19.7)
# Note: both scripts end with `source env.sh`, which executes ../.env; a line such as `KEY = value` (spaces around =)
# stops them there. Write KEY=value. This directory's env.sh parses .env instead of executing it.
# usage (from newman_experiment/):  bash setup_server.sh
set -euo pipefail
cd "$(dirname "$0")"
RL_VENV="${RL_VENV:-$HOME/venv/rl}"
TUTEE_VENV="${TUTEE_VENV:-$HOME/venv/tutee}"
[ -x "$RL_VENV/bin/python" ] || { echo "error: $RL_VENV missing: run ../rl/setup_server.sh first" >&2; exit 1; }
[ -x "$TUTEE_VENV/bin/python" ] || { echo "error: $TUTEE_VENV missing: run ../verifier_sft/setup_server.sh first" >&2; exit 1; }
"$RL_VENV/bin/pip" install -q -r requirements-extra.txt
"$TUTEE_VENV/bin/pip" install -q -r requirements-extra.txt
source env.sh rl
python -m pytest tests -q -p no:cacheprovider
python scripts/fetch_sources.py || echo "note: upload the mapping workbook before scripts/prepare_data.py --stage sft (see README)"
echo "done. every new shell: source env.sh (RL venv) or source env.sh sft (SFT venv)"
