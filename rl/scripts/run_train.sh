#!/usr/bin/env bash
# Launch GRPO training on the training GPUs (servers must already be up: scripts/launch_servers.sh).
# usage (from rl/):  bash scripts/run_train.sh CONFIG [train.py args ...]
#   e.g. bash scripts/run_train.sh configs/diversity.yaml --run_name diversity_seed42
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh
CONFIG="$1"; shift
eval "$(python scripts/server_settings.py "$CONFIG")"
curl -sf "http://127.0.0.1:$ROLLOUT_PORT/health/" > /dev/null \
  || { echo "error: rollout server is not up (bash scripts/launch_servers.sh $CONFIG)" >&2; exit 1; }
if ! grep -q "mock_reward_clients: true" "$CONFIG"; then
  curl -sf "http://127.0.0.1:$VERIFIER_PORT/health" > /dev/null \
    || { echo "error: verifier server is not up (bash scripts/launch_servers.sh $CONFIG)" >&2; exit 1; }
fi
mkdir -p logs
CUDA_VISIBLE_DEVICES=$TRAIN_GPUS exec accelerate launch --config_file "$ACCEL_CONFIG" --num_processes "$NUM_TRAIN" \
  scripts/train.py --config "$CONFIG" "$@"
