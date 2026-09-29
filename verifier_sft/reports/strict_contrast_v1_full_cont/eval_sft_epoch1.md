# Verifier evaluation — sft_epoch1

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-51` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9375 | 0.9373 | 0.0029 | 0.1221 | 0.0000 | 0.8750 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9194, 0.9540], macro_f1 [0.9189, 0.9539], pair_accuracy [0.8388, 0.9081]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9967 | 0.8779 | 0.9335 | 344 | 0 |
| not_aligned | 0.8909 | 0.9971 | 0.9410 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9708 | 0.9707 | 0.0000 | 0.0585 | 0.0000 | 0.9415 |
| mathclean | 92 | 0.9022 | 0.9012 | 0.0000 | 0.1957 | 0.0000 | 0.8043 |
| mathedu | 172 | 0.9070 | 0.9064 | 0.0116 | 0.1744 | 0.0000 | 0.8140 |
| stepwise | 82 | 0.9024 | 0.9015 | 0.0000 | 0.1951 | 0.0000 | 0.8049 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 40 | 0.9750 | 0.9750 | 0.0000 | 0.0500 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 30 | 0.9667 | 0.9666 | 0.0000 | 0.0667 | 0.0000 | 0.9333 |
| eic | operator_error | 34 | 0.9118 | 0.9111 | 0.0000 | 0.1765 | 0.0000 | 0.8235 |
| eic | referencing_context_value_error | 46 | 0.8913 | 0.8900 | 0.0000 | 0.2174 | 0.0000 | 0.7826 |
| eic | referencing_previous_step_value_error | 38 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.8421 | 0.8381 | 0.0000 | 0.3158 | 0.0000 | 0.6842 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.0000 | 0.1200 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| mathedu | Comprehension error | 32 | 0.9375 | 0.9373 | 0.0000 | 0.1250 | 0.0000 | 0.8750 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9091 | 0.0909 | 0.0909 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9186 | 0.9181 | 0.0000 | 0.1628 | 0.0000 | 0.8372 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.8000 | 0.7917 | 0.0000 | 0.4000 | 0.0000 | 0.6000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.9375 | 0.9373 | 0.0000 | 0.1250 | 0.0000 | 0.8750 |
| stepwise | Misunderstanding of a question | 26 | 0.9231 | 0.9226 | 0.0000 | 0.1538 | 0.0000 | 0.8462 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

