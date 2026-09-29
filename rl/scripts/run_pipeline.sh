#!/usr/bin/env bash
# Both experiments end to end, unattended (from rl/):
#   prepare Eedi data -> for each experiment: training servers -> GRPO training -> test verifier -> test evaluation
# A training run that aborts (e.g. a reward API failure after its retries) is resumed from its latest
# checkpoint after the servers are restarted, at most MAX_RESUMES times. Rerunning skips finished stages.
#
# usage (from rl/):  bash scripts/run_pipeline.sh [experiment ...]      default: diversity student_likeness
#   WAIT_FOR_DATA=1   wait until the Eedi files appear in data/raw/ (and stop growing) before starting
#   run names (output dir and W&B run) = <experiment>_<SEED_TAG>_<YYYYmmdd_HHMMSS at start>;
#   RUN_<experiment>=<name> continues or evaluates an existing run instead (e.g. RUN_diversity=diversity_seed42_20260930_010203)
#   a GRPO training already running (scripts/train.py) is waited for before anything starts
#   logs: logs/pipeline.log (stages), logs/train_<run>.log, logs/eval_<run>.log
set -uo pipefail
cd "$(dirname "$0")/.."
source env.sh
[ $# -eq 0 ] && set -- diversity student_likeness
MAX_RESUMES=${MAX_RESUMES:-2}
SEED_TAG=${SEED_TAG:-seed42}
mkdir -p logs

log() { echo "$(date '+%F %T') $*" | tee -a logs/pipeline.log; }
die() { log "FAILED: $*"; bash scripts/stop_servers.sh > /dev/null 2>&1; exit 1; }
has_checkpoint() { compgen -G "outputs/$1/checkpoint-*" > /dev/null; }
gpus_free() {  # after stop_servers.sh: every GPU must be empty (a stray vLLM engine would OOM the next stage)
  local t=0
  until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do
    t=$((t + 5)); [ $t -ge 60 ] && die "GPUs still in use: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' ')"
    sleep 5
  done
}

run_name() {  # one timestamped name per experiment and pipeline invocation
  local var="RUN_$1"
  if [ -n "${!var:-}" ]; then echo "${!var}"; else echo "$1_${SEED_TAG}_$(date '+%Y%m%d_%H%M%S')"; fi
}

wait_running_training() {
  pgrep -f "scripts/train.py" > /dev/null || return 0
  log "waiting for the GRPO training that is already running"
  while pgrep -f "scripts/train.py" > /dev/null; do sleep 60; done
  log "running training finished"
}

wait_for_data() {
  log "waiting for data/raw/train_model_inputs.jsonl + (train_privileged_annotations.jsonl or all_judgements.csv)"
  until [ -f data/raw/train_model_inputs.jsonl ] && { [ -f data/raw/train_privileged_annotations.jsonl ] || [ -f data/raw/all_judgements.csv ]; }; do
    sleep 10
  done
  local prev="" cur
  while cur=$(stat -c '%n:%s' data/raw/* | tr '\n' ' '); [ "$cur" != "$prev" ]; do prev=$cur; sleep 20; done  # uploads finished
  log "found: $cur"
}

prepare() {
  [ -f data/prepared/meta.json ] && { log "data/prepared exists"; return 0; }
  [ "${WAIT_FOR_DATA:-0}" = "1" ] && wait_for_data
  log "prepare Eedi data"
  python scripts/prepare_eedi.py 2>&1 | tee -a logs/pipeline.log
  [ "${PIPESTATUS[0]}" -eq 0 ] || die "prepare_eedi.py"
}

train() {  # experiment run_name
  local run="$2" cfg="configs/$1.yaml" attempt=0 rc resume=()
  [ -f "outputs/$run/final/config.json" ] && { log "$run: already trained"; return 0; }
  has_checkpoint "$run" && resume=(--resume latest)
  while true; do
    bash scripts/stop_servers.sh > /dev/null 2>&1
    gpus_free
    log "$run: launch training servers"
    bash scripts/launch_servers.sh "$cfg" >> logs/pipeline.log 2>&1 || die "$run: launch_servers.sh"
    log "$run: training ${resume[*]:-from scratch} (log: logs/train_$run.log)"
    bash scripts/run_train.sh "$cfg" --run_name "$run" "${resume[@]}" >> "logs/train_$run.log" 2>&1
    rc=$?
    [ $rc -eq 0 ] && { log "$run: training done"; return 0; }
    attempt=$((attempt + 1))
    if [ $attempt -gt "$MAX_RESUMES" ] || ! has_checkpoint "$run"; then die "$run: training exit $rc (logs/train_$run.log)"; fi
    log "$run: training exit $rc; restarting servers and resuming from the latest checkpoint in 5 min ($attempt/$MAX_RESUMES)"
    resume=(--resume latest)
    sleep 300
  done
}

evaluate() {  # experiment run_name
  local run="$2" cfg="configs/$1.yaml"
  [ -f "outputs/$run/test_eval/summary.json" ] && { log "$run: already evaluated"; return 0; }
  bash scripts/stop_servers.sh > /dev/null 2>&1
  gpus_free
  log "$run: launch test verifier"
  bash scripts/launch_eval_server.sh "$cfg" >> logs/pipeline.log 2>&1 || die "$run: launch_eval_server.sh"
  log "$run: test evaluation (log: logs/eval_$run.log)"
  python scripts/evaluate.py --config "$cfg" --run "outputs/$run" --include_base >> "logs/eval_$run.log" 2>&1 \
    || die "$run: evaluate.py (logs/eval_$run.log)"
  grep -E "^  (base|epoch-)|^best epoch" "logs/eval_$run.log" | tee -a logs/pipeline.log
  bash scripts/stop_servers.sh > /dev/null 2>&1
}

log "pipeline start: $*"
wait_running_training
prepare
for exp in "$@"; do
  run=$(run_name "$exp")
  log "$exp: run name $run"
  train "$exp" "$run"
  evaluate "$exp" "$run"
done
log "pipeline done"
