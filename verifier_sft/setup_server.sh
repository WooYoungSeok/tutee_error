#!/usr/bin/env bash
# One-time setup on a fresh Elice GPU server. Run from verifier_sft/:  bash setup_server.sh
# Builds a venv with the exact versions in requirements-lock.txt, then runs the unit tests.
set -euo pipefail
cd "$(dirname "$0")"

TUTEE_VENV="${TUTEE_VENV:-$HOME/venv/tutee}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"

py_version="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
[ "$py_version" = "3.10" ] || echo "warning: python3 is $py_version; the lock file was made with 3.10.14" >&2
[ -x "$CUDA_HOME/bin/nvcc" ] || { echo "error: no nvcc under $CUDA_HOME (set CUDA_HOME)" >&2; exit 1; }

[ -d "$TUTEE_VENV" ] || python3 -m venv "$TUTEE_VENV"
"$TUTEE_VENV/bin/pip" install -q --upgrade pip
"$TUTEE_VENV/bin/pip" install -q -r requirements-lock.txt

source env.sh
python -c "import torch; assert torch.cuda.is_available(); print('torch', torch.__version__, '· GPUs', torch.cuda.device_count())"
python -m pytest tests -q
echo "done. next: source env.sh"
