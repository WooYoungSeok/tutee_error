# Verifier evaluation — gpt-5.6-sol_test_augmented

model `api:gpt-5.6-sol` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9613 | 0.9612 | 0.0616 | 0.0116 | 0.0000 | 0.9302 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9482, 0.9738], macro_f1 [0.9481, 0.9737], pair_accuracy [0.9043, 0.9546]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9315 | 0.9884 | 0.9591 | 344 | 0 |
| not_aligned | 0.9896 | 0.9384 | 0.9633 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.9194 | 0.4790 | 0.0806 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9419 | 0.4850 | 0.0581 | - | 0.0000 | - |
| v2_positive | 344 | 0.9884 | 0.4971 | - | 0.0116 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.9523 | 0.9517 | 0.0705 | 0.0175 | 0.0000 | 0.9181 |
| mathclean | 92 | 0.9565 | 0.9565 | 0.0652 | 0.0217 | 0.0000 | 0.9130 |
| mathedu | 173 | 0.9827 | 0.9827 | 0.0345 | 0.0000 | 0.0000 | 0.9651 |
| stepwise | 87 | 0.9655 | 0.9655 | 0.0652 | 0.0000 | 0.0000 | 0.9268 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.9811 | 0.9807 | 0.0323 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 48 | 0.9583 | 0.9571 | 0.0357 | 0.0500 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 51 | 0.9020 | 0.9014 | 0.1667 | 0.0000 | 0.0000 | 0.9048 |
| eic | counting_error | 36 | 0.9722 | 0.9722 | 0.0556 | 0.0000 | 0.0000 | 0.9444 |
| eic | missing_step | 34 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | operator_error | 40 | 0.9750 | 0.9746 | 0.0435 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 56 | 0.9286 | 0.9277 | 0.1212 | 0.0000 | 0.0000 | 0.8261 |
| eic | referencing_previous_step_value_error | 47 | 0.9149 | 0.9117 | 0.0714 | 0.1053 | 0.0000 | 0.7895 |
| eic | unit_conversion_error | 33 | 0.9697 | 0.9697 | 0.0588 | 0.0000 | 0.0000 | 0.9375 |
| mathclean | computing error | 38 | 0.9737 | 0.9737 | 0.0526 | 0.0000 | 0.0000 | 0.9474 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9400 | 0.0800 | 0.0400 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9651 | 0.9651 | 0.0698 | 0.0000 | 0.0000 | 0.9302 |
| stepwise | Calculation error easily solved by a calculator | 11 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.9545 | 0.9545 | 0.0833 | 0.0000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 0.9231 | 0.9226 | 0.1538 | 0.0000 | 0.0000 | 0.8462 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.9474 | 0.4865 | 0.0526 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.9286 | 0.4815 | 0.0714 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

