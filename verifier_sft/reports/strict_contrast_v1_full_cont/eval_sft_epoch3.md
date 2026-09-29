# Verifier evaluation — sft_epoch3

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-153` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9317 | 0.9315 | 0.0174 | 0.1192 | 0.0000 | 0.8663 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9131, 0.9494], macro_f1 [0.9127, 0.9494], pair_accuracy [0.8309, 0.9000]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9806 | 0.8808 | 0.9280 | 344 | 0 |
| not_aligned | 0.8918 | 0.9826 | 0.9350 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9737 | 0.9737 | 0.0175 | 0.0351 | 0.0000 | 0.9474 |
| mathclean | 92 | 0.8913 | 0.8900 | 0.0000 | 0.2174 | 0.0000 | 0.7826 |
| mathedu | 172 | 0.8895 | 0.8887 | 0.0233 | 0.1977 | 0.0000 | 0.7907 |
| stepwise | 82 | 0.8902 | 0.8894 | 0.0244 | 0.1951 | 0.0000 | 0.7805 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 40 | 0.9500 | 0.9500 | 0.0500 | 0.0500 | 0.0000 | 0.9000 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 30 | 0.9333 | 0.9333 | 0.0667 | 0.0667 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9118 | 0.9117 | 0.0588 | 0.1176 | 0.0000 | 0.8235 |
| eic | referencing_context_value_error | 46 | 0.9783 | 0.9783 | 0.0000 | 0.0435 | 0.0000 | 0.9565 |
| eic | referencing_previous_step_value_error | 38 | 0.9737 | 0.9737 | 0.0000 | 0.0526 | 0.0000 | 0.9474 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.8158 | 0.8093 | 0.0000 | 0.3684 | 0.0000 | 0.6316 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.0000 | 0.1200 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| mathedu | Comprehension error | 32 | 0.9062 | 0.9054 | 0.0000 | 0.1875 | 0.0000 | 0.8125 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9545 | 0.9545 | 0.0000 | 0.0909 | 0.0000 | 0.9091 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8837 | 0.8832 | 0.0465 | 0.1860 | 0.0000 | 0.7907 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.8500 | 0.8465 | 0.0000 | 0.3000 | 0.0000 | 0.7000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| stepwise | Misunderstanding of a question | 26 | 0.8462 | 0.8452 | 0.0769 | 0.2308 | 0.0000 | 0.6923 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

