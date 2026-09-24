# Verifier evaluation — gpt-5.6-sol

model `api:gpt-5.6-sol` · split `test` · ablation `none` · 744 rows (372 pairs) · data sha256 `7f6686621324b2d1`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 744 | 0.9718 | 0.9718 | 0.0457 | 0.0108 | 0.0000 | 0.9435 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9590, 0.9836], macro_f1 [0.9590, 0.9836], pair_accuracy [0.9180, 0.9671]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9558 | 0.9892 | 0.9723 | 372 | 0 |
| not_aligned | 0.9889 | 0.9543 | 0.9713 | 372 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9678 | 0.9678 | 0.0526 | 0.0117 | 0.0000 | 0.9357 |
| mathclean | 92 | 0.9674 | 0.9674 | 0.0435 | 0.0217 | 0.0000 | 0.9348 |
| mathedu | 170 | 0.9824 | 0.9823 | 0.0353 | 0.0000 | 0.0000 | 0.9647 |
| stepwise | 140 | 0.9714 | 0.9714 | 0.0429 | 0.0143 | 0.0000 | 0.9429 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9773 | 0.9773 | 0.0455 | 0.0000 | 0.0000 | 0.9545 |
| eic | calculation_error | 40 | 0.9750 | 0.9750 | 0.0000 | 0.0500 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 42 | 0.9524 | 0.9523 | 0.0952 | 0.0000 | 0.0000 | 0.9048 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 28 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | operator_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | referencing_context_value_error | 44 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| eic | referencing_previous_step_value_error | 40 | 0.9500 | 0.9500 | 0.0500 | 0.0500 | 0.0000 | 0.9000 |
| eic | unit_conversion_error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathclean | computing error | 38 | 0.9737 | 0.9737 | 0.0526 | 0.0000 | 0.0000 | 0.9474 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9600 | 0.9600 | 0.0400 | 0.0400 | 0.0000 | 0.9200 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9651 | 0.9651 | 0.0698 | 0.0000 | 0.0000 | 0.9302 |
| stepwise | Calculation error easily solved by a calculator | 22 | 0.9091 | 0.9091 | 0.0909 | 0.0909 | 0.0000 | 0.8182 |
| stepwise | Extra quantity or Missing quantity | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Missing / Wrong factual knowledge | 28 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 42 | 0.9524 | 0.9523 | 0.0952 | 0.0000 | 0.0000 | 0.9048 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 17 | 0.9412 | 0.4848 | 0.0588 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 23 | 0.9565 | 0.4889 | 0.0435 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 13 | 0.9231 | 0.4800 | 0.0769 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 13 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge <- Misunderstanding of a question | 10 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

