#!/usr/bin/env bash
# strict_contrast_v1: continue training a verifier (config model.name) on audited same-question rows, then evaluate.
# Run from verifier_sft/ after the full audit (outputs/strict_contrast_v1/audit/audits.jsonl, 1,807 rows):
#     nohup bash run_strict_contrast_v1.sh [config] > logs/<experiment>.log 2>&1 &
#     config: config/strict_contrast_v1_halfA_cont.json (default) or config/strict_contrast_v1_full_cont.json
# GPU 0 trains; GPU 1 evaluates the untrained verifier meanwhile, then every epoch checkpoint.
# Evaluation sets: test (the v2 test, 688 rows), contrast_test (audited same-question test rows) and
# test_augmented (the v2 test + the audited same-question negatives of the test split).
set -euo pipefail
cd "$(dirname "$0")"
source env.sh
# the half-A verifier is a private hub repo already in the local cache: load it without network calls
# (check_formatting/eval do not read ../.env, so hub lookups would fail with 401)
export HF_HUB_OFFLINE=1

CFG=${1:-config/strict_contrast_v1_halfA_cont.json}
cfg() { python -c "import json, sys; c = json.load(open('$CFG')); print(eval(sys.argv[1]))" "$1"; }
EXP=$(cfg 'c["experiment"]')
INIT=$(cfg 'c["model"]["name"]')
REPORTS=$(cfg 'c["output"]["report_dir"]')
AUDITS=outputs/strict_contrast_v1/audit/audits.jsonl

n=$(wc -l < "$AUDITS")
[ "$n" -eq 1807 ] || { echo "error: $AUDITS has $n rows, expected 1807 (audit not finished?)" >&2; exit 1; }
echo "experiment $EXP · config $CFG · init checkpoint $INIT, cached revision: $(ls ~/.cache/huggingface/hub/models--${INIT/\//--}/snapshots/)"

echo "== $(date -u +%FT%TZ) data"
python build_contrast_sft.py --config "$CFG"
python check_formatting.py --config "$CFG"

echo "== $(date -u +%FT%TZ) baseline (untrained init checkpoint) on GPU 1, in the background"
(
  CUDA_VISIBLE_DEVICES=1 python eval_descriptive_verifier.py --config "$CFG" --model_path "$INIT" --name baseline --split test
  CUDA_VISIBLE_DEVICES=1 python eval_descriptive_verifier.py --config "$CFG" --model_path "$INIT" --name baseline_contrast_test --split contrast_test
  CUDA_VISIBLE_DEVICES=1 python eval_descriptive_verifier.py --config "$CFG" --model_path "$INIT" --name baseline_test_augmented --split test_augmented
) > "logs/${EXP}_baseline.log" 2>&1 &
BASELINE_PID=$!

RUN=checkpoints/${EXP}_$(date +%Y%m%d_%H%M%S)
mkdir -p "$RUN"
echo "== $(date -u +%FT%TZ) training on GPU 0 -> $RUN"
CUDA_VISIBLE_DEVICES=0 accelerate launch --config_file accelerate_config_ds_single.yaml \
    train_descriptive_verifier.py --config "$CFG" --output_dir "$RUN" > "$RUN/train.log" 2>&1

wait "$BASELINE_PID"
echo "== $(date -u +%FT%TZ) epoch checkpoints on GPU 1"
CUDA_VISIBLE_DEVICES=1 python eval_checkpoints.py --config "$CFG" --run_dir "$RUN"
CUDA_VISIBLE_DEVICES=1 python eval_checkpoints.py --config "$CFG" --run_dir "$RUN" --split contrast_test
CUDA_VISIBLE_DEVICES=1 python eval_checkpoints.py --config "$CFG" --run_dir "$RUN" --split test_augmented

epochs=$(ls -d "$RUN"/checkpoint-* | wc -l)
names_test="baseline"; names_contrast="baseline_contrast_test"; names_aug="baseline_test_augmented"
for k in $(seq 1 "$epochs"); do
  names_test+=" sft_epoch$k"; names_contrast+=" sft_epoch${k}_contrast_test"; names_aug+=" sft_epoch${k}_test_augmented"
done
python summarize_results.py --config "$CFG" --out "$REPORTS/verifier_results.md" $names_test
python summarize_results.py --config "$CFG" --out "$REPORTS/verifier_results_contrast_test.md" $names_contrast
python summarize_results.py --config "$CFG" --out "$REPORTS/verifier_results_test_augmented.md" $names_aug
echo "== $(date -u +%FT%TZ) done: $REPORTS/verifier_results{,_contrast_test,_test_augmented}.md"
