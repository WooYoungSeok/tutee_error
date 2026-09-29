# Verifier evaluation — sft_epoch1_contrast_test

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-51` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.8267 | 0.7895 | 0.3492 | 0.0935 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7476, 0.8956], macro_f1 [0.7055, 0.8612], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8514 | 0.9065 | 0.8780 | 139 | 0 |
| not_aligned | 0.7593 | 0.6508 | 0.7009 | 63 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 124 | 0.7661 | 0.7635 | 0.3387 | 0.1290 | 0.0000 | - |
| audited_own | 78 | 0.9231 | 0.4800 | 1.0000 | 0.0649 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.8298 | 0.7873 | 0.3684 | 0.0840 | 0.0000 | - |
| mathedu | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | 12 | 0.7500 | 0.7483 | 0.2000 | 0.2857 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.9412 | 0.9183 | 0.2222 | 0.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.6667 | 0.6606 | 0.5000 | 0.1429 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.8571 | 0.7638 | 0.5556 | 0.0000 | 0.0000 | - |
| eic | counting_error | 29 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |
| eic | missing_step | 11 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| eic | operator_error | 14 | 0.6429 | 0.6410 | 0.3333 | 0.3750 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.6452 | 0.6198 | 0.4000 | 0.3333 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.7647 | 0.7639 | 0.4000 | 0.0000 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.6667 | 0.4000 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.6000 | 0.5833 | 0.5000 | 0.3333 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

