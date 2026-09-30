# Source before running anything in newman_experiment/:
#   source env.sh        RL venv (~/venv/rl): data preparation, GRPO, vLLM servers, Student evaluation, tests
#   source env.sh sft    SFT venv (~/venv/tutee): verifier full-parameter SFT and its HF evaluation
# Both venvs come from ../rl/setup_server.sh and ../verifier_sft/setup_server.sh (+ setup_server.sh here).
# Secrets are read from tutee_error/.env by parsing KEY=VALUE lines (`KEY = VALUE` too); the file is never executed.
_newman_role="${1:-rl}"
case "$_newman_role" in
  rl) _newman_venv="${RL_VENV:-$HOME/venv/rl}" ;;
  sft) _newman_venv="${TUTEE_VENV:-$HOME/venv/tutee}" ;;
  *) echo "usage: source env.sh [rl|sft]" >&2; return 1 ;;
esac
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"   # DeepSpeed cpu_adam JIT
export PATH="$CUDA_HOME/bin:$PATH"
export HF_HOME="${HF_HOME:-$HOME/hf_cache}"
export HF_XET_HIGH_PERFORMANCE=1
export TOKENIZERS_PARALLELISM=false
export VLLM_USE_FLASHINFER_SAMPLER=0   # driver 535 cannot load FlashInfer cubins built by nvcc 12.8 (see ../rl/env.sh)
_newman_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$_newman_here/src:$_newman_here/../rl/src${PYTHONPATH:+:$PYTHONPATH}"
source "$_newman_venv/bin/activate"
if [ -f "$_newman_here/../.env" ]; then
  eval "$(python - "$_newman_here/../.env" <<'PY'
import shlex, sys
from pathlib import Path
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = (s.strip() for s in line.split("=", 1))
    if key.isidentifier():
        print(f"export {key}={shlex.quote(value.strip(chr(34)).strip(chr(39)))}")
PY
)"
fi
unset _newman_role _newman_venv _newman_here
