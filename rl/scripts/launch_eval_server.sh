#!/usr/bin/env bash
# Start the held-out test verifier (half B) for scripts/evaluate.py and wait until it answers.
# Stop the training servers first (bash scripts/stop_servers.sh): the default GPU is the inference GPU.
#
# usage (from rl/):  bash scripts/launch_eval_server.sh [config]      GPU=1 bash ... to put it elsewhere
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh
CONFIG="${1:-configs/common.yaml}"
eval "$(python scripts/server_settings.py "$CONFIG")"
GPU="${GPU:-$EVAL_VERIFIER_GPU}"
mkdir -p logs

CUDA_VISIBLE_DEVICES=$GPU nohup vllm serve "$EVAL_VERIFIER_MODEL" \
  --served-model-name "$EVAL_VERIFIER_NAME" --host 127.0.0.1 --port "$EVAL_VERIFIER_PORT" \
  --dtype bfloat16 --max-model-len "$EVAL_VERIFIER_MAXLEN" --gpu-memory-utilization "$EVAL_VERIFIER_UTIL" \
  --enable-prefix-caching \
  > logs/eval_verifier.log 2>&1 &
pid=$!
echo $pid > logs/eval_verifier.pid
t=0
until curl -sf "http://127.0.0.1:$EVAL_VERIFIER_PORT/health" > /dev/null; do
  if ! kill -0 "$pid" 2> /dev/null; then echo "error: test verifier exited; see logs/eval_verifier.log" >&2; tail -30 logs/eval_verifier.log >&2; exit 1; fi
  t=$((t + 5)); if [ "$t" -ge 900 ]; then echo "error: test verifier not up after 900s" >&2; exit 1; fi
  sleep 5
done
echo "test verifier up (http://127.0.0.1:$EVAL_VERIFIER_PORT, GPU $GPU)"
