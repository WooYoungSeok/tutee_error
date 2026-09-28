# Verifier evaluation — baseline

model `Qwen/Qwen2.5-Math-7B-Instruct` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.0000 | 0.0000 | 0.0029 | 0.0000 | 0.9985 | 0.0000 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.0000, 0.0000], macro_f1 [0.0000, 0.0000], pair_accuracy [0.0000, 0.0000]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.0000 | 0.0000 | 0.0000 | 344 | 344 |
| not_aligned | 0.0000 | 0.0000 | 0.0000 | 344 | 343 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | 92 | 0.0000 | 0.0000 | 0.0217 | 0.0000 | 0.9891 | 0.0000 |
| mathedu | 172 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | 82 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | calculation_error | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | confusing_formula_error | 42 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | counting_error | 36 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | missing_step | 30 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | operator_error | 34 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | referencing_context_value_error | 46 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | referencing_previous_step_value_error | 38 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | unit_conversion_error | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | computing error | 38 | 0.0000 | 0.0000 | 0.0526 | 0.0000 | 0.9737 | 0.0000 |
| mathclean | expression error | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | logic error | 50 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Algebraic error | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Arithmetical error | 14 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Careless error | 6 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Measurement error | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Unfinished answer | 22 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Calculation error easily solved by a calculator | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Misunderstanding of a question | 26 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Unit conversion error | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.0000 | 0.0000 | 0.0526 | - | 0.9474 | - |
| mathclean | logic error <- computing error | 24 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |

