#!/usr/bin/env bash
# Distractor-reward GRPO end to end, unattended (rl/scripts/run_pipeline.sh's train + evaluate with this reward):
#   servers -> training (auto-resume from the latest checkpoint, at most MAX_RESUMES times)
#   -> test generation + scoring of base and every snapshot with the half-B verifier (best = highest mean test reward).
# usage (from distractor_rl/):  tmux new -s distractor 'CONFIG=configs/verifiable.yaml bash scripts/run_pipeline.sh'
#   run name = distractor_student_likeness_seed42_<YYYYmmdd_HHMMSS, Asia/Seoul>; RUN=<name> continues a run
#   logs: distractor_rl/logs/{pipeline,train_<run>,eval_<run>}.log
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$(realpath "${CONFIG:-$HERE/configs/student_likeness.yaml}")"
RL="$HERE/../rl"
MAX_RESUMES=${MAX_RESUMES:-2}
EXP=$(grep -m1 "^experiment:" "$CFG" | awk '{print $2}')
RUN=${RUN:-${EXP}_seed42_$(TZ=Asia/Seoul date '+%Y%m%d_%H%M%S')}
SKIP=0; grep -q "^  variant: verifiable" "$CFG" && SKIP=1   # no reward verifier server
OUT="$HERE/outputs/$RUN"
LOGS="$HERE/logs"
mkdir -p "$LOGS"
cd "$RL"
source env.sh

log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*" | tee -a "$LOGS/pipeline.log"; }
die() { log "FAILED: $*"; bash scripts/stop_servers.sh > /dev/null 2>&1; exit 1; }
has_checkpoint() { compgen -G "$OUT/checkpoint-*" > /dev/null; }
gpus_free() {
  local t=0
  until nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 1000 {busy=1} END {exit busy}'; do
    t=$((t + 5)); [ $t -ge 60 ] && die "GPUs still in use: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' ')"
    sleep 5
  done
}

train() {
  local attempt=0 rc resume=()
  [ -f "$OUT/final/config.json" ] && { log "$RUN: already trained"; return 0; }
  has_checkpoint && resume=(--resume latest)
  while true; do
    bash scripts/stop_servers.sh > /dev/null 2>&1
    gpus_free
    log "$RUN: launch training servers"
    SKIP_VERIFIER=$SKIP bash scripts/launch_servers.sh "$CFG" >> "$LOGS/pipeline.log" 2>&1 || die "$RUN: launch_servers.sh"
    log "$RUN: training ${resume[*]:-from scratch} (log: logs/train_$RUN.log)"
    bash "$HERE/scripts/run_train.sh" "$CFG" --run_name "$RUN" "${resume[@]}" 2>&1 | tee -a "$LOGS/train_$RUN.log"
    rc=${PIPESTATUS[0]}
    [ $rc -eq 0 ] && { log "$RUN: training done"; return 0; }
    attempt=$((attempt + 1))
    if [ $attempt -gt "$MAX_RESUMES" ] || ! has_checkpoint; then die "$RUN: training exit $rc (logs/train_$RUN.log)"; fi
    log "$RUN: training exit $rc; resuming from the latest checkpoint in 5 min ($attempt/$MAX_RESUMES)"
    resume=(--resume latest)
    sleep 300
  done
}

evaluate() {
  [ -f "$OUT/test_eval/summary.json" ] && { log "$RUN: already evaluated"; return 0; }
  bash scripts/stop_servers.sh > /dev/null 2>&1
  gpus_free
  log "$RUN: launch test verifier (rl/scripts/evaluate.py checks it is up; the verifiable variant does not call it)"
  bash scripts/launch_eval_server.sh "$CFG" >> "$LOGS/pipeline.log" 2>&1 || die "$RUN: launch_eval_server.sh"
  log "$RUN: test evaluation (log: logs/eval_$RUN.log)"
  PYTHONPATH="$HERE/src:$PYTHONPATH" python "$HERE/scripts/evaluate.py" --config "$CFG" --run "$OUT" --include_base \
    >> "$LOGS/eval_$RUN.log" 2>&1 || die "$RUN: evaluate.py (logs/eval_$RUN.log)"
  bash scripts/stop_servers.sh > /dev/null 2>&1
  log "$RUN: evaluation done -> $OUT/test_eval/summary.json"
}

log "pipeline start: $RUN"
train
evaluate
log "pipeline done"
