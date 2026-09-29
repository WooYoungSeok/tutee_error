# Source before running anything in rl/:  source env.sh
# RL venv (vLLM 0.30 + TRL 1.14 on torch 2.13+cu129: the driver here is 535 / CUDA 12.2, so CUDA 13 wheels
# cannot run), CUDA toolkit for DeepSpeed's cpu_adam JIT, shared HF cache, and secrets from tutee_error/.env.
RL_VENV="${RL_VENV:-$HOME/venv/rl}"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
export PATH="$CUDA_HOME/bin:$PATH"
export HF_HOME="${HF_HOME:-$HOME/hf_cache}"
export HF_XET_HIGH_PERFORMANCE=1
export TOKENIZERS_PARALLELISM=false
# Driver 535 (CUDA 12.2) cannot load cubins JIT-built by nvcc 12.8 (FlashInfer: "device kernel image is invalid").
# vLLM then uses its Triton top-k/top-p + Gumbel sampler; with top_k=-1, top_p=1 FlashInfer is not used anyway.
export VLLM_USE_FLASHINFER_SAMPLER=0
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
source "$RL_VENV/bin/activate"
_env_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"
if [ -f "$_env_file" ]; then set -a; source "$_env_file"; set +a; fi
unset _env_file
