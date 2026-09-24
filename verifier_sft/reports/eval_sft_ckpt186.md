# Verifier evaluation — sft_ckpt186

model `checkpoints/descriptive_verifier_v1_20260924_032353/checkpoint-186` · split `test` · ablation `none` · 744 rows (372 pairs) · data sha256 `7f6686621324b2d1`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 744 | 0.9543 | 0.9543 | 0.0618 | 0.0296 | 0.0000 | 0.9113 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9387, 0.9696], macro_f1 [0.9386, 0.9696], pair_accuracy [0.8805, 0.9401]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9401 | 0.9704 | 0.9550 | 372 | 0 |
| not_aligned | 0.9694 | 0.9382 | 0.9536 | 372 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9591 | 0.9590 | 0.0643 | 0.0175 | 0.0000 | 0.9181 |
| mathclean | 92 | 0.9565 | 0.9565 | 0.0217 | 0.0652 | 0.0000 | 0.9348 |
| mathedu | 170 | 0.9412 | 0.9412 | 0.0706 | 0.0471 | 0.0000 | 0.8824 |
| stepwise | 140 | 0.9571 | 0.9571 | 0.0714 | 0.0143 | 0.0000 | 0.9143 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| eic | calculation_error | 40 | 0.9500 | 0.9499 | 0.0000 | 0.1000 | 0.0000 | 0.9000 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 0.9722 | 0.9722 | 0.0556 | 0.0000 | 0.0000 | 0.9444 |
| eic | missing_step | 28 | 0.9643 | 0.9642 | 0.0714 | 0.0000 | 0.0000 | 0.9286 |
| eic | operator_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | referencing_context_value_error | 44 | 0.9091 | 0.9089 | 0.1364 | 0.0455 | 0.0000 | 0.8182 |
| eic | referencing_previous_step_value_error | 40 | 0.9500 | 0.9499 | 0.1000 | 0.0000 | 0.0000 | 0.9000 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.8947 | 0.8944 | 0.0526 | 0.1579 | 0.0000 | 0.8421 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.9286 | 0.9282 | 0.0000 | 0.1429 | 0.0000 | 0.8571 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 20 | 0.9000 | 0.8990 | 0.2000 | 0.0000 | 0.0000 | 0.8000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9419 | 0.9418 | 0.0930 | 0.0233 | 0.0000 | 0.8837 |
| stepwise | Calculation error easily solved by a calculator | 22 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 36 | 0.8889 | 0.8885 | 0.1667 | 0.0556 | 0.0000 | 0.7778 |
| stepwise | Missing / Wrong factual knowledge | 28 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 42 | 0.9524 | 0.9523 | 0.0952 | 0.0000 | 0.0000 | 0.9048 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 17 | 0.9412 | 0.4848 | 0.0588 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 23 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 13 | 0.9231 | 0.4800 | 0.0769 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 13 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge <- Misunderstanding of a question | 10 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

