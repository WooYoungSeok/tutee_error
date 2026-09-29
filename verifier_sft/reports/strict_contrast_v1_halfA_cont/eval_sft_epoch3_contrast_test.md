# Verifier evaluation — sft_epoch3_contrast_test

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-66` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.8614 | 0.8307 | 0.3016 | 0.0647 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7976, 0.9150], macro_f1 [0.7566, 0.8883], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8725 | 0.9353 | 0.9028 | 139 | 0 |
| not_aligned | 0.8302 | 0.6984 | 0.7586 | 63 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.8670 | 0.8329 | 0.3158 | 0.0534 | 0.0000 | - |
| mathedu | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | 12 | 0.7500 | 0.7483 | 0.2000 | 0.2857 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.9118 | 0.8717 | 0.3333 | 0.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.7333 | 0.7321 | 0.2500 | 0.2857 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.8857 | 0.8214 | 0.4444 | 0.0000 | 0.0000 | - |
| eic | counting_error | 29 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |
| eic | missing_step | 11 | 0.8182 | 0.7708 | 0.5000 | 0.0000 | 0.0000 | - |
| eic | operator_error | 14 | 0.6429 | 0.6410 | 0.3333 | 0.3750 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.8387 | 0.8103 | 0.3000 | 0.0952 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.8824 | 0.8819 | 0.2000 | 0.0000 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.6667 | 0.4000 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.6000 | 0.5833 | 0.5000 | 0.3333 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

