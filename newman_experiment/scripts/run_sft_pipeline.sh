#!/usr/bin/env bash
# Verifier SFT end to end, unattended (from newman_experiment/):
#   train A on TRAIN_GPU -> train B on TRAIN_GPU while A is evaluated on EVAL_GPU -> evaluate B.
# One training at a time (a 7-8B run holds ~229 GiB of host RAM); evaluation beside it needs a few GB.
# A finished stage (run dir with epoch-5 / test_eval/summary.json) is skipped when RUN_A / RUN_B name an existing run.
#
# usage:  tmux new -s newman_sft 'bash scripts/run_sft_pipeline.sh'
#   TRAIN_GPU=0 EVAL_GPU=1 (default); RUN_A=<run name> / RUN_B=<run name> continue or evaluate existing runs
#   CFG_A / CFG_B: verifier configs (default configs/verifier_half_{a,b}.yaml; data v3: configs/verifier_half_{a,b}_v3.yaml),
#   run names start with the config's `experiment`; PIPELINE_LOG (default logs/sft_pipeline.log)
#   logs: $PIPELINE_LOG, logs/train_<run>.log, logs/eval_<run>.log
set -uo pipefail
cd "$(dirname "$0")/.."
TRAIN_GPU=${TRAIN_GPU:-0}
EVAL_GPU=${EVAL_GPU:-1}
CFG_A=${CFG_A:-configs/verifier_half_a.yaml}
CFG_B=${CFG_B:-configs/verifier_half_b.yaml}
PIPELINE_LOG=${PIPELINE_LOG:-logs/sft_pipeline.log}
mkdir -p logs

log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*" | tee -a "$PIPELINE_LOG"; }
experiment() { grep -E '^experiment:' "$1" | awk '{print $2}'; }
stamp() { TZ=Asia/Seoul date '+%Y%m%d_%H%M%S'; }

train() {  # config run_name
  local cfg=$1 run=$2
  if [ -d "outputs/$run/epoch_checkpoints/epoch-5" ]; then log "$run: already trained"; return 0; fi
  log "$run: training ($cfg, GPU $TRAIN_GPU, log logs/train_$run.log)"
  GPU=$TRAIN_GPU bash scripts/run_train_verifier.sh "$cfg" --run_name "$run" > "logs/train_$run.log" 2>&1
  local rc=$?
  [ $rc -eq 0 ] && log "$run: training done" || log "FAILED: $run training exit $rc (logs/train_$run.log)"
  return $rc
}

evaluate() {  # config run_name
  local cfg=$1 run=$2
  if [ -f "outputs/$run/test_eval/summary.json" ]; then log "$run: already evaluated"; return 0; fi
  log "$run: evaluation on GPU $EVAL_GPU (log logs/eval_$run.log)"
  (source env.sh sft && CUDA_VISIBLE_DEVICES=$EVAL_GPU python scripts/eval_verifier.py --config "$cfg" \
      --run_dir "outputs/$run" --include_base) > "logs/eval_$run.log" 2>&1
  local rc=$?
  [ $rc -eq 0 ] && log "$run: $(grep '^best:' "logs/eval_$run.log")" || log "FAILED: $run evaluation exit $rc (logs/eval_$run.log)"
  return $rc
}

RUN_A=${RUN_A:-$(experiment "$CFG_A")_seed42_$(stamp)}
log "sft pipeline start: A=$RUN_A ($CFG_A, $CFG_B)"
train "$CFG_A" "$RUN_A" || exit 1
evaluate "$CFG_A" "$RUN_A" &
EVAL_A=$!
RUN_B=${RUN_B:-$(experiment "$CFG_B")_seed42_$(stamp)}
log "B run name: $RUN_B"
train "$CFG_B" "$RUN_B"; rc_b=$?
wait $EVAL_A; rc_a=$?
[ $rc_b -eq 0 ] && evaluate "$CFG_B" "$RUN_B"; rc_eb=$?
log "sft pipeline done: A train ok, A eval exit $rc_a, B train exit $rc_b, B eval exit $rc_eb"
