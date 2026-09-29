# Verifier evaluation — sft_epoch1_contrast_test

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-22` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.3119 | 0.2377 | 0.0000 | 1.0000 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.2146, 0.4093], macro_f1 [0.1767, 0.2904], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.0000 | 0.0000 | 0.0000 | 139 | 0 |
| not_aligned | 0.3119 | 1.0000 | 0.4755 | 63 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.3032 | 0.2327 | 0.0000 | 1.0000 | 0.0000 | - |
| mathedu | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | 12 | 0.4167 | 0.2941 | 0.0000 | 1.0000 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.2647 | 0.2093 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.5333 | 0.3478 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.2571 | 0.2045 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | counting_error | 29 | 0.0000 | 0.0000 | - | 1.0000 | 0.0000 | - |
| eic | missing_step | 11 | 0.3636 | 0.2667 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | operator_error | 14 | 0.4286 | 0.3000 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.3226 | 0.2439 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.5882 | 0.3704 | 0.0000 | 1.0000 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.6667 | 0.4000 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.4000 | 0.2857 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 0.0000 | 0.0000 | - | 1.0000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

