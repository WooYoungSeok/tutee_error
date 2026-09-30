#!/usr/bin/env bash
# Verifier SFT on one GPU (DeepSpeed ZeRO-2, optimizer on CPU). One run at a time: a 7-8B run holds ~229 GiB of
# host RAM (verifier_sft README), so A and B are trained one after the other.
# usage (from newman_experiment/):  GPU=0 bash scripts/run_train_verifier.sh CONFIG [train_verifier.py args ...]
set -euo pipefail
cd "$(dirname "$0")/.."
source env.sh sft
CONFIG="$1"; shift
if pgrep -f "scripts/train_verifier.py" > /dev/null; then
  echo "error: another verifier SFT is running (host RAM); wait for it" >&2; exit 1
fi
mkdir -p logs
CUDA_VISIBLE_DEVICES="${GPU:-0}" exec accelerate launch --config_file configs/accelerate_sft_single.yaml \
  scripts/train_verifier.py --config "$CONFIG" "$@"
