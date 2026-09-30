#!/usr/bin/env bash
# Training servers on the inference GPU, started one after the other (two vLLM instances must not profile
# memory at the same time):
#   verifier A : `vllm serve` of the frozen reward verifier (skipped with mock rewards)
#   rollout    : `trl vllm-serve` of the policy; the trainer pushes new weights every step
# usage (from newman_experiment/):  bash scripts/launch_servers.sh CONFIG      stop: bash scripts/stop_servers.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh rl
CONFIG="${1:?usage: launch_servers.sh CONFIG}"
eval "$(python scripts/server_settings.py "$CONFIG")"
mkdir -p logs

wait_http() {  # url name pid timeout_s
  local url=$1 name=$2 pid=$3 limit=$4 t=0
  until curl -sf "$url" > /dev/null; do
    if ! kill -0 "$pid" 2> /dev/null; then echo "error: $name exited; see logs/$name.log" >&2; tail -30 "logs/$name.log" >&2; exit 1; fi
    t=$((t + 5)); if [ "$t" -ge "$limit" ]; then echo "error: $name not up after ${limit}s" >&2; exit 1; fi
    sleep 5
  done
  echo "$name up ($url)"
}

if [ "$MOCK_REWARDS" != "1" ]; then
  [ "$VERIFIER_MODEL" != "REQUIRED" ] || { echo "error: verifier.checkpoint is REQUIRED in $CONFIG" >&2; exit 1; }
  CUDA_VISIBLE_DEVICES=$VERIFIER_GPU nohup vllm serve "$VERIFIER_MODEL" \
    --served-model-name "$VERIFIER_NAME" --host 127.0.0.1 --port "$VERIFIER_PORT" \
    --dtype bfloat16 --max-model-len "$VERIFIER_MAXLEN" --gpu-memory-utilization "$VERIFIER_UTIL" \
    --enable-prefix-caching > logs/verifier_a.log 2>&1 &
  echo $! > logs/verifier_a.pid
  wait_http "http://127.0.0.1:$VERIFIER_PORT/health" verifier_a "$(cat logs/verifier_a.pid)" 900
fi

CUDA_VISIBLE_DEVICES=$ROLLOUT_GPU nohup trl vllm-serve --model "$POLICY_MODEL" \
  --host 127.0.0.1 --port "$ROLLOUT_PORT" --gpu_memory_utilization "$ROLLOUT_UTIL" \
  --max_model_len "$ROLLOUT_MAXLEN" --enable_prefix_caching true --dtype bfloat16 \
  > logs/rollout.log 2>&1 &
echo $! > logs/rollout.pid
wait_http "http://127.0.0.1:$ROLLOUT_PORT/health/" rollout "$(cat logs/rollout.pid)" 900
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
