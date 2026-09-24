# Source before running anything in verifier_sft/:  source env.sh
# Activates the venv made by setup_server.sh and exposes the CUDA toolkit that
# DeepSpeed needs to JIT-compile cpu_adam (ds_config.json offloads the optimizer to CPU).
TUTEE_VENV="${TUTEE_VENV:-$HOME/venv/tutee}"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
export PATH="$CUDA_HOME/bin:$PATH"
source "$TUTEE_VENV/bin/activate"
