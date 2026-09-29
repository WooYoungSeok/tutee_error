# Verifier evaluation — baseline_contrast_test

model `WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2` · split `contrast_test` · ablation `none` · 202 rows (0 pairs) · data sha256 `937668efa6cb375e`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 202 | 0.7475 | 0.6062 | 0.7619 | 0.0216 | 0.0000 | - |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.6647, 0.8246], macro_f1 [0.5218, 0.6776], pair_accuracy [-, -]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.7391 | 0.9784 | 0.8421 | 139 | 0 |
| not_aligned | 0.8333 | 0.2381 | 0.3704 | 63 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 124 | 0.5968 | 0.5387 | 0.7581 | 0.0484 | 0.0000 | - |
| audited_own | 78 | 0.9872 | 0.4968 | 1.0000 | 0.0000 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 188 | 0.7606 | 0.6175 | 0.7544 | 0.0153 | 0.0000 | - |
| mathedu | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | - |
| stepwise | 12 | 0.5833 | 0.4958 | 0.8000 | 0.1429 | 0.0000 | - |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 34 | 0.8235 | 0.6964 | 0.6667 | 0.0000 | 0.0000 | - |
| eic | calculation_error | 15 | 0.4667 | 0.4000 | 0.8750 | 0.1429 | 0.0000 | - |
| eic | confusing_formula_error | 35 | 0.7714 | 0.5333 | 0.8889 | 0.0000 | 0.0000 | - |
| eic | counting_error | 29 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |
| eic | missing_step | 11 | 0.9091 | 0.8952 | 0.2500 | 0.0000 | 0.0000 | - |
| eic | operator_error | 14 | 0.7143 | 0.6500 | 0.6667 | 0.0000 | 0.0000 | - |
| eic | referencing_context_value_error | 31 | 0.7097 | 0.5620 | 0.8000 | 0.0476 | 0.0000 | - |
| eic | referencing_previous_step_value_error | 17 | 0.5294 | 0.4848 | 0.8000 | 0.0000 | 0.0000 | - |
| eic | unit_conversion_error | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | - |
| mathedu | Unfinished answer | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | - |
| stepwise | Calculation error easily solved by a calculator | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | - |
| stepwise | Extra quantity or Missing quantity | 3 | 0.3333 | 0.2500 | 1.0000 | 0.0000 | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge | 5 | 0.6000 | 0.5833 | 0.5000 | 0.3333 | 0.0000 | - |
| stepwise | Misunderstanding of a question | 2 | 1.0000 | 0.5000 | - | 0.0000 | 0.0000 | - |

## Negatives by anchor <- donor label (n >= 10)

No combination reaches the minimum support.

