# Verifier evaluation — sft

model `checkpoints/descriptive_verifier_v2_halfA_20260928_025029/final` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9477 | 0.9476 | 0.0930 | 0.0116 | 0.0000 | 0.8953 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9311, 0.9630], macro_f1 [0.9309, 0.9630], pair_accuracy [0.8622, 0.9260]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9140 | 0.9884 | 0.9497 | 344 | 0 |
| not_aligned | 0.9873 | 0.9070 | 0.9455 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9532 | 0.9532 | 0.0819 | 0.0117 | 0.0000 | 0.9064 |
| mathclean | 92 | 0.9348 | 0.9347 | 0.1087 | 0.0217 | 0.0000 | 0.8696 |
| mathedu | 172 | 0.9186 | 0.9182 | 0.1512 | 0.0116 | 0.0000 | 0.8372 |
| stepwise | 82 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| eic | calculation_error | 40 | 0.9750 | 0.9750 | 0.0500 | 0.0000 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 42 | 0.9762 | 0.9762 | 0.0476 | 0.0000 | 0.0000 | 0.9524 |
| eic | counting_error | 36 | 0.9444 | 0.9443 | 0.1111 | 0.0000 | 0.0000 | 0.8889 |
| eic | missing_step | 30 | 0.9333 | 0.9330 | 0.1333 | 0.0000 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9412 | 0.9410 | 0.1176 | 0.0000 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 46 | 0.9565 | 0.9565 | 0.0435 | 0.0435 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 38 | 0.9474 | 0.9474 | 0.0526 | 0.0526 | 0.0000 | 0.8947 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9211 | 0.9210 | 0.1053 | 0.0526 | 0.0000 | 0.8421 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.1200 | 0.0000 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9062 | 0.9054 | 0.1875 | 0.0000 | 0.0000 | 0.8125 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9070 | 0.9062 | 0.1860 | 0.0000 | 0.0000 | 0.8140 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.8947 | 0.4722 | 0.1053 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.8750 | 0.4667 | 0.1250 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.7857 | 0.4400 | 0.2143 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

