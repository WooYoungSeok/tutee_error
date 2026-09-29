#!/usr/bin/env bash
# One-time setup of the RL venv (separate from verifier_sft's venv). Run from rl/:  bash setup_server.sh
# The server driver is 535 (CUDA 12.2): CUDA 13 wheels (the PyPI default for torch 2.13 / vLLM 0.30) fail at
# the first kernel, so torch comes from the cu129 index and vLLM from its +cu129 release wheel.
set -euo pipefail
cd "$(dirname "$0")"
RL_VENV="${RL_VENV:-$HOME/venv/rl}"
[ -d "$RL_VENV" ] || python3 -m venv "$RL_VENV"
"$RL_VENV/bin/pip" install -q --upgrade pip uv
"$RL_VENV/bin/uv" pip install --python "$RL_VENV/bin/python" --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cu129 \
  "https://github.com/vllm-project/vllm/releases/download/v0.30.0/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
  -r requirements-lock.txt
source env.sh
python -c "import torch; x=torch.ones(2,device='cuda'); print('torch', torch.__version__, 'cuda ok', torch.cuda.device_count(), 'GPUs')"
python -m pytest tests -q -p no:cacheprovider
