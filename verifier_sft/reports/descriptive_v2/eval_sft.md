# Verifier evaluation — sft

model `checkpoints/descriptive_verifier_v2_20260924_055214/final` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9738 | 0.9738 | 0.0320 | 0.0203 | 0.0000 | 0.9506 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9593, 0.9855], macro_f1 [0.9593, 0.9855], pair_accuracy [0.9250, 0.9717]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9684 | 0.9797 | 0.9740 | 344 | 0 |
| not_aligned | 0.9794 | 0.9680 | 0.9737 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9795 | 0.9795 | 0.0292 | 0.0117 | 0.0000 | 0.9591 |
| mathclean | 92 | 0.9674 | 0.9674 | 0.0217 | 0.0435 | 0.0000 | 0.9348 |
| mathedu | 172 | 0.9593 | 0.9593 | 0.0581 | 0.0233 | 0.0000 | 0.9302 |
| stepwise | 82 | 0.9878 | 0.9878 | 0.0000 | 0.0244 | 0.0000 | 0.9756 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9545 | 0.9545 | 0.0909 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 40 | 0.9750 | 0.9750 | 0.0500 | 0.0000 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 30 | 0.9667 | 0.9666 | 0.0667 | 0.0000 | 0.0000 | 0.9333 |
| eic | operator_error | 34 | 0.9706 | 0.9706 | 0.0588 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 46 | 0.9565 | 0.9564 | 0.0000 | 0.0870 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 38 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9474 | 0.9472 | 0.0000 | 0.1053 | 0.0000 | 0.8947 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9535 | 0.9535 | 0.0465 | 0.0465 | 0.0000 | 0.9302 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9500 | 0.9499 | 0.0000 | 0.1000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9583 | 0.4894 | 0.0417 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

