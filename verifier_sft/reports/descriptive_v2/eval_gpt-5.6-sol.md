# Verifier evaluation — gpt-5.6-sol

model `api:gpt-5.6-sol` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9637 | 0.9636 | 0.0581 | 0.0145 | 0.0000 | 0.9273 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9504, 0.9764], macro_f1 [0.9504, 0.9764], pair_accuracy [0.9009, 0.9528]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9443 | 0.9855 | 0.9644 | 344 | 0 |
| not_aligned | 0.9848 | 0.9419 | 0.9629 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9561 | 0.9561 | 0.0643 | 0.0234 | 0.0000 | 0.9123 |
| mathclean | 92 | 0.9565 | 0.9565 | 0.0652 | 0.0217 | 0.0000 | 0.9130 |
| mathedu | 172 | 0.9826 | 0.9826 | 0.0349 | 0.0000 | 0.0000 | 0.9651 |
| stepwise | 82 | 0.9634 | 0.9634 | 0.0732 | 0.0000 | 0.0000 | 0.9268 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 40 | 0.9250 | 0.9250 | 0.0500 | 0.1000 | 0.0000 | 0.8500 |
| eic | confusing_formula_error | 42 | 0.9524 | 0.9523 | 0.0952 | 0.0000 | 0.0000 | 0.9048 |
| eic | counting_error | 36 | 0.9444 | 0.9444 | 0.0556 | 0.0556 | 0.0000 | 0.8889 |
| eic | missing_step | 30 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | operator_error | 34 | 0.9706 | 0.9706 | 0.0588 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 46 | 0.9348 | 0.9345 | 0.1304 | 0.0000 | 0.0000 | 0.8696 |
| eic | referencing_previous_step_value_error | 38 | 0.9211 | 0.9210 | 0.1053 | 0.0526 | 0.0000 | 0.8421 |
| eic | unit_conversion_error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathclean | computing error | 38 | 0.9737 | 0.9737 | 0.0526 | 0.0000 | 0.0000 | 0.9474 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9400 | 0.0800 | 0.0400 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9651 | 0.9651 | 0.0698 | 0.0000 | 0.0000 | 0.9302 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9500 | 0.9499 | 0.1000 | 0.0000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 0.9231 | 0.9226 | 0.1538 | 0.0000 | 0.0000 | 0.8462 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.9474 | 0.4865 | 0.0526 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

