#!/usr/bin/env bash
# B / gpt-5.6-sol success of the verifiable run's snapshots (user request 2026-10-03), queued behind the auto-stop at step 342.
# Test generation of epoch-0.5 and epoch-1.0, then the FIRST distractor run's scoring (Eedi answer judge = correctness,
# gpt-5-nano low; test verifier B), with the auxiliary term set to BLEU (no judge calls; success rates do not use it),
# then gpt-5.6-sol on the incorrect solutions with the Eedi verifier messages (2 calls, both aligned).
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RUN=$HERE/outputs/distractor_verifiable_seed42_20261003_130011
CFG=${CFG:-$HERE/configs/student_likeness.yaml}
log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*"; }
[ -f "$RUN/test_eval_b/.started" ] && { log "already started elsewhere (parallel run); skipping"; exit 0; }
mkdir -p "$RUN/test_eval_b" && touch "$RUN/test_eval_b/.started"
log "waiting for the auto-stop after step 342"
until grep -q "stopping (user request)" $HERE/logs/stop_after_342.log 2>/dev/null; do sleep 30; done   # log only (pgrep matched unrelated shells)
cd $HERE/../rl && source env.sh
[ -n "${SKIP_GPU_WAIT:-}" ] || until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do sleep 20; done
export PYTHONPATH="$HERE/src:$PYTHONPATH"
CK="$RUN/epoch_checkpoints/epoch-0.5 $RUN/epoch_checkpoints/epoch-1.0"
log "test generation: epoch-0.5, epoch-1.0"
python $HERE/scripts/evaluate.py --config $CFG --override rewards.auxiliary_reward=diversity --checkpoints $CK --out $RUN/test_eval_b --stage generate || { log "FAILED generation"; exit 1; }
log "test verifier B"
bash scripts/launch_eval_server.sh $CFG || { log "FAILED launch_eval_server"; exit 1; }
python $HERE/scripts/evaluate.py --config $CFG --override rewards.auxiliary_reward=diversity --checkpoints $CK --out $RUN/test_eval_b --stage score || { bash scripts/stop_servers.sh; log "FAILED scoring"; exit 1; }
bash scripts/stop_servers.sh
log "gpt-5.6-sol verifier"
python $HERE/scripts/score_api_verifier.py --run $RUN --eval_dir test_eval_b --checkpoints epoch-0.5 epoch-1.0 || { log "FAILED gpt-5.6-sol"; exit 1; }
log "done"
