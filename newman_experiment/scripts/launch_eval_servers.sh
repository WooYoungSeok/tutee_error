#!/usr/bin/env bash
# Evaluation servers: the held-out test verifier B (:8002) and, when evaluation.with_reward_verifier is true,
# the reward verifier A (:8001) for the A/B disagreement diagnostic. Stop the training servers first.
# usage (from newman_experiment/):  bash scripts/launch_eval_servers.sh CONFIG
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh rl
CONFIG="${1:?usage: launch_eval_servers.sh CONFIG}"
eval "$(python scripts/server_settings.py "$CONFIG")"
mkdir -p logs

serve() {  # name model served_name gpu port util maxlen
  local name=$1 model=$2 served=$3 gpu=$4 port=$5 util=$6 maxlen=$7 t=0
  [ "$model" != "REQUIRED" ] || { echo "error: the $name checkpoint is REQUIRED in $CONFIG" >&2; exit 1; }
  CUDA_VISIBLE_DEVICES=$gpu nohup vllm serve "$model" --served-model-name "$served" --host 127.0.0.1 --port "$port" \
    --dtype bfloat16 --max-model-len "$maxlen" --gpu-memory-utilization "$util" --enable-prefix-caching \
    > "logs/$name.log" 2>&1 &
  local pid=$!
  echo $pid > "logs/$name.pid"
  until curl -sf "http://127.0.0.1:$port/health" > /dev/null; do
    if ! kill -0 "$pid" 2> /dev/null; then echo "error: $name exited; see logs/$name.log" >&2; tail -30 "logs/$name.log" >&2; exit 1; fi
    t=$((t + 5)); if [ "$t" -ge 900 ]; then echo "error: $name not up after 900s" >&2; exit 1; fi
    sleep 5
  done
  echo "$name up (http://127.0.0.1:$port, GPU $gpu)"
}

serve verifier_b "$EVAL_VERIFIER_MODEL" "$EVAL_VERIFIER_NAME" "$EVAL_VERIFIER_GPU" "$EVAL_VERIFIER_PORT" "$EVAL_VERIFIER_UTIL" "$EVAL_VERIFIER_MAXLEN"
if [ "$EVAL_WITH_REWARD_VERIFIER" = "1" ]; then
  serve verifier_a "$VERIFIER_MODEL" "$VERIFIER_NAME" "$EVAL_REWARD_GPU" "$EVAL_REWARD_PORT" "$EVAL_REWARD_UTIL" "$EVAL_REWARD_MAXLEN"
fi
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
