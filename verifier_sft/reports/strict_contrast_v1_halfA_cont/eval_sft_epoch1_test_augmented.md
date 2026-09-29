# Verifier evaluation — sft_epoch1_test_augmented

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-22` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.5413 | 0.3512 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.5247, 0.5575], macro_f1 [0.3441, 0.3579], pair_accuracy [0.0000, 0.0000]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.0000 | 0.0000 | 0.0000 | 344 | 0 |
| not_aligned | 0.5413 | 1.0000 | 0.7024 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| v2_positive | 344 | 0.0000 | 0.0000 | - | 1.0000 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.5704 | 0.3632 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | 92 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | 173 | 0.5029 | 0.3346 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | 87 | 0.5287 | 0.3459 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.5849 | 0.3690 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | calculation_error | 48 | 0.5833 | 0.3684 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | confusing_formula_error | 51 | 0.5882 | 0.3704 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | counting_error | 36 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | missing_step | 34 | 0.5588 | 0.3585 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | operator_error | 40 | 0.5750 | 0.3651 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | referencing_context_value_error | 56 | 0.5893 | 0.3708 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | referencing_previous_step_value_error | 47 | 0.5957 | 0.3733 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| eic | unit_conversion_error | 33 | 0.5152 | 0.3400 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | computing error | 38 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | expression error | 4 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | logic error | 50 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Algebraic error | 8 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Arithmetical error | 14 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Careless error | 6 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Measurement error | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Unfinished answer | 23 | 0.5217 | 0.3429 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Calculation error easily solved by a calculator | 11 | 0.5455 | 0.3529 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.5455 | 0.3529 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.5556 | 0.3571 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Misunderstanding of a question | 26 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| stepwise | Unit conversion error | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

