#!/usr/bin/env bash
# Follow-up chain of 2026-10-01 (user requests), unattended, from newman_experiment/:
#   1. wait for the data-v2 SFT pipeline (logs/sft_pipeline.log: "sft pipeline done")
#   2. upload the v2 best A/B to HF private (background) and start the data-v3 SFT pipeline (configs/verifier_half_{a,b}_v3.yaml)
#   3. on EVAL_GPU while v3 trains: evaluate the v2 best A/B on the v3 test and on the first (all-type negatives) test
#   4. after the v3 pipeline: upload the v3 best A/B, evaluate them on the v2 test and on the all-type test
# Cross-test results go to <run>/test_eval_{v2_test,v3_test,alltype_test}/<best>/ (own test_eval/ is never touched).
# usage: tmux new -d -s newman_chain 'bash scripts/run_verifier_v2_v3_chain.sh'   log: logs/verifier_v2_v3_chain.log
set -uo pipefail
cd "$(dirname "$0")/.."
EVAL_GPU=${EVAL_GPU:-1}
LOG=logs/verifier_v2_v3_chain.log
V2_TEST=data/prepared/sft
V3_TEST=data/prepared_v3/sft
ALLTYPE_TEST=data/prepared/sft_all_type_negatives_test
log() { echo "$(TZ=Asia/Seoul date '+%F %T') $*" | tee -a "$LOG"; }

wait_for() {  # pipeline log -> waits for done / FAILED; returns 1 on failure
  until grep -qE "sft pipeline done|FAILED" "$1" 2>/dev/null; do sleep 60; done
  ! grep -q FAILED "$1"
}
runs_of() {  # pipeline log -> "RUN_A RUN_B" of its last start
  local a b
  a=$(grep "sft pipeline start: A=" "$1" | tail -1 | sed -E 's/.*A=([^ ]+).*/\1/')
  b=$(grep "B run name:" "$1" | tail -1 | sed -E 's/.*B run name: ([^ ]+).*/\1/')
  echo "$a $b"
}
best_of() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['best_checkpoint'])" "outputs/$1/test_eval/summary.json"; }

upload() {  # run...
  for r in "$@"; do
    (source env.sh sft && python scripts/upload_verifier_hf.py --run_dir "outputs/$r") >> logs/hf_upload_chain.log 2>&1 \
      && log "uploaded $r ($(grep '^done:' logs/hf_upload_chain.log | tail -1))" || log "FAILED upload $r (logs/hf_upload_chain.log)"
  done
}
cross_eval() {  # config run data_dir eval_dir
  local cfg=$1 run=$2 data=$3 dir=$4 best
  best=$(best_of "$run")
  log "$run/$best on $data -> $dir (GPU $EVAL_GPU)"
  (source env.sh sft && CUDA_VISIBLE_DEVICES=$EVAL_GPU python scripts/eval_verifier.py --config "$cfg" --run_dir "outputs/$run" \
      --only "$best" --eval_dir "$dir" --override "data_dir=$data" --no_wandb) > "logs/eval_${run}_${dir}.log" 2>&1 \
    && log "  $(grep -E '^   accuracy' "logs/eval_${run}_${dir}.log")" || log "FAILED cross eval $run $dir (logs/eval_${run}_${dir}.log)"
}

log "chain start: waiting for the v2 pipeline"
wait_for logs/sft_pipeline.log || { log "v2 pipeline FAILED: chain stops"; exit 1; }
read -r A2 B2 < <(runs_of logs/sft_pipeline.log)
log "v2 done: A=$A2 B=$B2"
upload "$A2" "$B2" &
UP2=$!
CFG_A=configs/verifier_half_a_v3.yaml CFG_B=configs/verifier_half_b_v3.yaml PIPELINE_LOG=logs/sft_pipeline_v3.log \
  bash scripts/run_sft_pipeline.sh > logs/sft_pipeline_v3.stdout 2>&1 &
V3=$!
log "v3 pipeline started (logs/sft_pipeline_v3.log)"
cross_eval configs/verifier_half_a.yaml "$A2" "$V3_TEST" test_eval_v3_test
cross_eval configs/verifier_half_b.yaml "$B2" "$V3_TEST" test_eval_v3_test
cross_eval configs/verifier_half_a.yaml "$A2" "$ALLTYPE_TEST" test_eval_alltype_test
cross_eval configs/verifier_half_b.yaml "$B2" "$ALLTYPE_TEST" test_eval_alltype_test
wait $UP2
wait $V3
wait_for logs/sft_pipeline_v3.log || { log "v3 pipeline FAILED: chain stops"; exit 1; }
read -r A3 B3 < <(runs_of logs/sft_pipeline_v3.log)
log "v3 done: A=$A3 B=$B3"
upload "$A3" "$B3" &
UP3=$!
cross_eval configs/verifier_half_a_v3.yaml "$A3" "$V2_TEST" test_eval_v2_test
cross_eval configs/verifier_half_b_v3.yaml "$B3" "$V2_TEST" test_eval_v2_test
cross_eval configs/verifier_half_a_v3.yaml "$A3" "$ALLTYPE_TEST" test_eval_alltype_test
cross_eval configs/verifier_half_b_v3.yaml "$B3" "$ALLTYPE_TEST" test_eval_alltype_test
wait $UP3
log "chain done"
