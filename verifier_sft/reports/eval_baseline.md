# Verifier evaluation — baseline

model `Qwen/Qwen2.5-Math-7B-Instruct` · split `test` · ablation `none` · 744 rows (372 pairs) · data sha256 `7f6686621324b2d1`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 744 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.0000, 0.0000], macro_f1 [0.0000, 0.0000], pair_accuracy [0.0000, 0.0000]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.0000 | 0.0000 | 0.0000 | 372 | 372 |
| not_aligned | 0.0000 | 0.0000 | 0.0000 | 372 | 372 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | 92 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | 170 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | 140 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | calculation_error | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | confusing_formula_error | 42 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | counting_error | 36 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | missing_step | 28 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | operator_error | 36 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | referencing_context_value_error | 44 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | referencing_previous_step_value_error | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| eic | unit_conversion_error | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | computing error | 38 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | expression error | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathclean | logic error | 50 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Algebraic error | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Arithmetical error | 14 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Careless error | 6 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Measurement error | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Unfinished answer | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Calculation error easily solved by a calculator | 22 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Extra quantity or Missing quantity | 36 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Missing / Wrong factual knowledge | 28 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Misunderstanding of a question | 42 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| stepwise | Unit conversion error | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 17 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| mathclean | logic error <- computing error | 23 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 13 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 13 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |
| stepwise | Missing / Wrong factual knowledge <- Misunderstanding of a question | 10 | 0.0000 | 0.0000 | 0.0000 | - | 1.0000 | - |

