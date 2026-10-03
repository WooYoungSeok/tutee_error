#!/usr/bin/env bash
# Test evaluation of the stopped Newman run's remaining snapshot (user request 2026-10-03), queued behind the
# distractor pipeline that holds the GPUs:
#   wait for distractor_rl/logs/pipeline.log "pipeline done" -> RL test generation (every epoch_checkpoints/epoch-K,
#   i.e. epoch-0.50) -> scoring with gpt-5-nano + test verifier B (+ A diagnostic; no likeness judge on test)
#   -> gpt-5.6-sol as verifier on the incorrect solutions with the Newman verifier SFT messages (2 calls, both aligned).
# usage (from newman_experiment/):  nohup bash scripts/eval_stopped_run_with_sol.sh > logs/eval_stopped_run.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=${RUN:-newman_student_likeness_seed42_20261002_154536}
CFG=configs/student_likeness.yaml
WAIT_FOR=${WAIT_FOR:-distractor_verifiable_seed42_20261003_130011}
log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*"; }

log "waiting for the distractor pipeline ($WAIT_FOR) to finish"
until grep -qE "pipeline done|FAILED: $WAIT_FOR" ../distractor_rl/logs/pipeline.log 2>/dev/null \
      && ! tmux has-session -t distractor 2>/dev/null; do sleep 120; done
log "distractor pipeline finished: $(tail -1 ../distractor_rl/logs/pipeline.log)"
source env.sh rl
bash scripts/stop_servers.sh > /dev/null 2>&1
until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do sleep 30; done

log "generation: $RUN snapshots on RL test"
python scripts/evaluate_student.py --config $CFG --run outputs/$RUN --split test --stage generate || { log "FAILED generation"; exit 1; }
log "scoring servers (verifier B + A)"
bash scripts/launch_eval_servers.sh $CFG || { log "FAILED launch_eval_servers"; exit 1; }
python scripts/evaluate_student.py --config $CFG --run outputs/$RUN --split test --stage score || { bash scripts/stop_servers.sh; log "FAILED scoring"; exit 1; }
bash scripts/stop_servers.sh
for d in outputs/$RUN/test_eval/epoch-*/; do
  ck=$(basename $d)
  log "gpt-5.6-sol verifier: $ck"
  python scripts/score_generations_api_verifier.py --scored outputs/$RUN/test_eval/$ck --model gpt-5.6-sol \
    --out outputs/$RUN/test_eval_api_verifier_gpt-5.6-sol/$ck || { log "FAILED gpt-5.6-sol scoring $ck"; exit 1; }
done
log "done"
