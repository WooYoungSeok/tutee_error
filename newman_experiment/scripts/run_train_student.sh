#!/usr/bin/env bash
# GRPO training on the training GPUs (servers first: scripts/launch_servers.sh CONFIG).
# usage (from newman_experiment/):  bash scripts/run_train_student.sh CONFIG [train_student.py args ...]
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh rl
CONFIG="$1"; shift
eval "$(python scripts/server_settings.py "$CONFIG")"
curl -sf "http://127.0.0.1:$ROLLOUT_PORT/health/" > /dev/null \
  || { echo "error: rollout server is not up (bash scripts/launch_servers.sh $CONFIG)" >&2; exit 1; }
if [ "$MOCK_REWARDS" != "1" ]; then
  curl -sf "http://127.0.0.1:$VERIFIER_PORT/health" > /dev/null \
    || { echo "error: reward verifier A is not up (bash scripts/launch_servers.sh $CONFIG)" >&2; exit 1; }
fi
mkdir -p logs
CUDA_VISIBLE_DEVICES=$TRAIN_GPUS exec accelerate launch --config_file "$ACCEL_CONFIG" --num_processes "$NUM_TRAIN" \
  scripts/train_student.py --config "$CONFIG" "$@"
