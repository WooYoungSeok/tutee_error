#!/usr/bin/env bash
# GRPO training with the distractor reward on the training GPUs; servers first (rl/scripts/launch_servers.sh CONFIG).
# usage (from distractor_rl/):  bash scripts/run_train.sh configs/student_likeness.yaml --run_name <name> [train.py args]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$(realpath "$1")"; shift
cd "$HERE/../rl"
source env.sh
eval "$(python scripts/server_settings.py "$CONFIG")"
curl -sf "http://127.0.0.1:$ROLLOUT_PORT/health/" > /dev/null || { echo "error: rollout server is not up" >&2; exit 1; }
if ! grep -q "^  variant: verifiable" "$CONFIG"; then   # the verifiable variant uses no reward verifier
  curl -sf "http://127.0.0.1:$VERIFIER_PORT/health" > /dev/null || { echo "error: verifier server is not up" >&2; exit 1; }
fi
export PYTHONPATH="$HERE/src:$PYTHONPATH"
CUDA_VISIBLE_DEVICES=$TRAIN_GPUS exec accelerate launch --config_file "$ACCEL_CONFIG" --num_processes "$NUM_TRAIN" \
  "$HERE/scripts/train.py" --config "$CONFIG" "$@"
