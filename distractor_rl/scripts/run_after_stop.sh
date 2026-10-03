#!/usr/bin/env bash
# Queued after the auto-stop at step 342 (user requests 2026-10-03), in this order:
#   1) Newman API baselines (gpt-5.6-sol, gpt-5.1 generations on the Newman RL test) scored with test verifier B
#      (gpt-5-nano low verdicts; B n=2 T=0.6, both aligned; single B server on GPU 0, no A diagnostic)
#   2) the verifiable distractor run's epoch-0.5 / epoch-1.0 on the Eedi test: B success and gpt-5.6-sol success
set -uo pipefail
T=/home/elicer/tutee_error
log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*"; }
log "waiting for the auto-stop after step 342"
until grep -q "stopping (user request)" $T/distractor_rl/logs/stop_after_342.log 2>/dev/null; do sleep 20; done   # log only (pgrep matched unrelated shells)
until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do sleep 20; done

log "1) Newman API baselines with verifier B"
cd $T/newman_experiment && source env.sh rl
bash scripts/launch_eval_servers.sh configs/eval_a100_20gb.yaml || { log "FAILED launch B (newman)"; exit 1; }
python scripts/evaluate_student.py --config configs/eval_a100_20gb.yaml --out outputs/api_baselines_verifierB/test_eval \
  --api_dirs outputs/api_baselines/gpt-5.6-sol outputs/api_baselines/gpt-5.1 --stage score || { bash scripts/stop_servers.sh; log "FAILED newman B scoring"; exit 1; }
bash scripts/stop_servers.sh
sleep 15
log "1) done -> newman_experiment/outputs/api_baselines_verifierB/test_eval"

log "2) verifiable distractor snapshots"
bash $T/distractor_rl/scripts/eval_verifiable_snapshots.sh
