# Verifier evaluation — sft_epoch3

model `/home/elicer/tutee_error/verifier_sft/checkpoints/descriptive_verifier_v2_trval_halfA_20260928_065513/checkpoint-285` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9637 | 0.9636 | 0.0581 | 0.0145 | 0.0000 | 0.9273 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9482, 0.9775], macro_f1 [0.9482, 0.9775], pair_accuracy [0.8964, 0.9551]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9443 | 0.9855 | 0.9644 | 344 | 0 |
| not_aligned | 0.9848 | 0.9419 | 0.9629 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9678 | 0.9678 | 0.0585 | 0.0058 | 0.0000 | 0.9357 |
| mathclean | 92 | 0.9565 | 0.9565 | 0.0217 | 0.0652 | 0.0000 | 0.9130 |
| mathedu | 172 | 0.9535 | 0.9534 | 0.0814 | 0.0116 | 0.0000 | 0.9070 |
| stepwise | 82 | 0.9756 | 0.9756 | 0.0488 | 0.0000 | 0.0000 | 0.9512 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9545 | 0.9545 | 0.0909 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 40 | 0.9000 | 0.8997 | 0.1500 | 0.0500 | 0.0000 | 0.8000 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 30 | 0.9333 | 0.9330 | 0.1333 | 0.0000 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9412 | 0.9410 | 0.1176 | 0.0000 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 46 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | referencing_previous_step_value_error | 38 | 0.9737 | 0.9737 | 0.0526 | 0.0000 | 0.0000 | 0.9474 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9211 | 0.9206 | 0.0000 | 0.1579 | 0.0000 | 0.8421 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9302 | 0.9301 | 0.1163 | 0.0233 | 0.0000 | 0.8605 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9500 | 0.9499 | 0.1000 | 0.0000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.9375 | 0.9373 | 0.1250 | 0.0000 | 0.0000 | 0.8750 |
| stepwise | Misunderstanding of a question | 26 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9583 | 0.4894 | 0.0417 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.9286 | 0.4815 | 0.0714 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

