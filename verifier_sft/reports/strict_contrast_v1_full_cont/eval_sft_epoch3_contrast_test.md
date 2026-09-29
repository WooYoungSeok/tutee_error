# Verifier evaluation — sft_epoch3_contrast_test

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-153` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.8465 | 0.8171 | 0.2857 | 0.0935 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7722, 0.9065], macro_f1 [0.7378, 0.8796], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8750 | 0.9065 | 0.8905 | 139 | 0 |
| not_aligned | 0.7759 | 0.7143 | 0.7438 | 63 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 124 | 0.7903 | 0.7894 | 0.2742 | 0.1452 | 0.0000 | - |
| audited_own | 78 | 0.9359 | 0.4834 | 1.0000 | 0.0519 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.8617 | 0.8292 | 0.2982 | 0.0687 | 0.0000 | - |
| mathedu | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | 12 | 0.5833 | 0.5804 | 0.2000 | 0.5714 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.9412 | 0.9183 | 0.2222 | 0.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.6000 | 0.5982 | 0.5000 | 0.2857 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.9143 | 0.8727 | 0.3333 | 0.0000 | 0.0000 | - |
| eic | counting_error | 29 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |
| eic | missing_step | 11 | 0.9091 | 0.8952 | 0.2500 | 0.0000 | 0.0000 | - |
| eic | operator_error | 14 | 0.7143 | 0.7143 | 0.1667 | 0.3750 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.8065 | 0.7786 | 0.3000 | 0.1429 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.7647 | 0.7639 | 0.3000 | 0.1429 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.6667 | 0.4000 | 0.0000 | 1.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.4000 | 0.4000 | 0.5000 | 0.6667 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 0.5000 | 0.3333 | - | 0.5000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

