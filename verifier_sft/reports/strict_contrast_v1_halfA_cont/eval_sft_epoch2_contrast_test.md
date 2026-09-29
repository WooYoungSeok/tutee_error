# Verifier evaluation — sft_epoch2_contrast_test

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-44` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.8119 | 0.7923 | 0.1905 | 0.1871 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7500, 0.8677], macro_f1 [0.7393, 0.8365], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9040 | 0.8129 | 0.8561 | 139 | 0 |
| not_aligned | 0.6623 | 0.8095 | 0.7286 | 63 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.8191 | 0.7954 | 0.2105 | 0.1679 | 0.0000 | - |
| mathedu | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | 12 | 0.6667 | 0.6571 | 0.0000 | 0.5714 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.9118 | 0.8717 | 0.3333 | 0.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.7333 | 0.7000 | 0.0000 | 0.5714 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.8857 | 0.8214 | 0.4444 | 0.0000 | 0.0000 | - |
| eic | counting_error | 29 | 0.9310 | 0.4821 | - | 0.0690 | 0.0000 | - |
| eic | missing_step | 11 | 0.8182 | 0.8167 | 0.0000 | 0.2857 | 0.0000 | - |
| eic | operator_error | 14 | 0.7143 | 0.7083 | 0.0000 | 0.5000 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.6129 | 0.6026 | 0.3000 | 0.4286 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.8235 | 0.8211 | 0.2000 | 0.1429 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.6667 | 0.4000 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.8000 | 0.8000 | 0.0000 | 0.3333 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 0.5000 | 0.3333 | - | 0.5000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

