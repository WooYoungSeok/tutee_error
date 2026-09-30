#!/usr/bin/env bash
# Both Student experiments end to end, unattended (from newman_experiment/): for each experiment
#   training servers -> GRPO training (auto-resume from the latest checkpoint, at most MAX_RESUMES times)
#   -> generation + scoring of every snapshot on RL validation (picks the snapshot) and of base + snapshots on test.
# Data (--stage sft/rl) and the verifier SFT / checkpoint choice come first; REQUIRED decisions and approvals are
# checked by the Python scripts (a refusal stops the pipeline). Rerunning skips finished stages.
#
# usage:  bash scripts/run_rl_pipeline.sh [experiment ...]      default: student_likeness diversity
#   run names = newman_<experiment>_<SEED_TAG>_<YYYYmmdd_HHMMSS, Asia/Seoul>; RUN_<experiment>=<name> continues a run
#   logs: logs/pipeline.log, logs/train_<run>.log, logs/eval_<run>.log  (tmux: tmux new -s newman 'bash scripts/run_rl_pipeline.sh')
set -uo pipefail
cd "$(dirname "$0")/.."
source env.sh rl
[ $# -eq 0 ] && set -- student_likeness diversity
MAX_RESUMES=${MAX_RESUMES:-2}
SEED_TAG=${SEED_TAG:-seed42}
mkdir -p logs

log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*" | tee -a logs/pipeline.log; }
die() { log "FAILED: $*"; bash scripts/stop_servers.sh > /dev/null 2>&1; exit 1; }
has_checkpoint() { compgen -G "outputs/$1/checkpoint-*" > /dev/null; }
gpus_free() {
  local t=0
  until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do
    t=$((t + 5)); [ $t -ge 60 ] && die "GPUs still in use: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' ')"
    sleep 5
  done
}
run_name() {
  local var="RUN_$1"
  if [ -n "${!var:-}" ]; then echo "${!var}"; else echo "newman_$1_${SEED_TAG}_$(TZ=Asia/Seoul date '+%Y%m%d_%H%M%S')"; fi
}

train() {  # experiment run
  local run="$2" cfg="configs/$1.yaml" attempt=0 rc resume=()
  [ -f "outputs/$run/final/config.json" ] && { log "$run: already trained"; return 0; }
  has_checkpoint "$run" && resume=(--resume latest)
  while true; do
    bash scripts/stop_servers.sh > /dev/null 2>&1
    gpus_free
    log "$run: launch training servers"
    bash scripts/launch_servers.sh "$cfg" >> logs/pipeline.log 2>&1 || die "$run: launch_servers.sh"
    log "$run: training ${resume[*]:-from scratch} (log: logs/train_$run.log)"
    bash scripts/run_train_student.sh "$cfg" --run_name "$run" "${resume[@]}" 2>&1 | tee -a "logs/train_$run.log"
    rc=${PIPESTATUS[0]}
    [ $rc -eq 0 ] && { log "$run: training done"; return 0; }
    [ $rc -eq 2 ] && die "$run: train_student.py refused to start (see logs/train_$run.log)"
    attempt=$((attempt + 1))
    if [ $attempt -gt "$MAX_RESUMES" ] || ! has_checkpoint "$run"; then die "$run: training exit $rc (logs/train_$run.log)"; fi
    log "$run: training exit $rc; restarting servers and resuming from the latest checkpoint in 5 min ($attempt/$MAX_RESUMES)"
    resume=(--resume latest)
    sleep 300
  done
}

evaluate() {  # experiment run: validation picks the snapshot (user decision 2026-09-30), test reports every model
  local run="$2" cfg="configs/$1.yaml"
  [ -f "outputs/$run/test_eval/summary.json" ] && { log "$run: already evaluated"; return 0; }
  bash scripts/stop_servers.sh > /dev/null 2>&1
  gpus_free
  log "$run: generation (validation: snapshots; test: base + snapshots)"
  python scripts/evaluate_student.py --config "$cfg" --run "outputs/$run" --split validation --stage generate >> "logs/eval_$run.log" 2>&1 \
    || die "$run: validation generation (logs/eval_$run.log)"
  python scripts/evaluate_student.py --config "$cfg" --run "outputs/$run" --split test --include_base --stage generate >> "logs/eval_$run.log" 2>&1 \
    || die "$run: test generation (logs/eval_$run.log)"
  log "$run: launch evaluation servers"
  bash scripts/launch_eval_servers.sh "$cfg" >> logs/pipeline.log 2>&1 || die "$run: launch_eval_servers.sh"
  log "$run: scoring (log: logs/eval_$run.log)"
  python scripts/evaluate_student.py --config "$cfg" --run "outputs/$run" --split validation --stage score >> "logs/eval_$run.log" 2>&1 \
    || die "$run: validation scoring (logs/eval_$run.log)"
  python scripts/evaluate_student.py --config "$cfg" --run "outputs/$run" --split test --include_base --stage score >> "logs/eval_$run.log" 2>&1 \
    || die "$run: test scoring (logs/eval_$run.log)"
  grep -E "^  (base|epoch-)|^best snapshot" "logs/eval_$run.log" | tee -a logs/pipeline.log
  bash scripts/stop_servers.sh > /dev/null 2>&1
}

log "pipeline start: $*"
for exp in "$@"; do
  run=$(run_name "$exp")
  log "$exp: run name $run"
  train "$exp" "$run"
  evaluate "$exp" "$run"
done
log "pipeline done"
