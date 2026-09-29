# Verifier evaluation — sft_epoch1_test_augmented

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-51` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9147 | 0.9136 | 0.0542 | 0.1221 | 0.0000 | 0.8750 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8924, 0.9361], macro_f1 [0.8907, 0.9354], pair_accuracy [0.8388, 0.9081]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9321 | 0.8779 | 0.9042 | 344 | 0 |
| not_aligned | 0.9014 | 0.9458 | 0.9231 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.6613 | 0.3981 | 0.3387 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9971 | 0.4993 | 0.0029 | - | 0.0000 | - |
| v2_positive | 344 | 0.8779 | 0.4675 | - | 0.1221 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.9246 | 0.9236 | 0.0881 | 0.0585 | 0.0000 | 0.9415 |
| mathclean | 92 | 0.9022 | 0.9012 | 0.0000 | 0.1957 | 0.0000 | 0.8043 |
| mathedu | 173 | 0.9075 | 0.9068 | 0.0115 | 0.1744 | 0.0000 | 0.8140 |
| stepwise | 87 | 0.8966 | 0.8945 | 0.0217 | 0.1951 | 0.0000 | 0.8049 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.9623 | 0.9616 | 0.0645 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 48 | 0.8958 | 0.8947 | 0.1429 | 0.0500 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 51 | 0.9020 | 0.9014 | 0.1667 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 34 | 0.9706 | 0.9699 | 0.0000 | 0.0667 | 0.0000 | 0.9333 |
| eic | operator_error | 40 | 0.8750 | 0.8711 | 0.0870 | 0.1765 | 0.0000 | 0.8235 |
| eic | referencing_context_value_error | 56 | 0.8393 | 0.8328 | 0.1212 | 0.2174 | 0.0000 | 0.7826 |
| eic | referencing_previous_step_value_error | 47 | 0.9362 | 0.9351 | 0.1071 | 0.0000 | 0.0000 | 1.0000 |
| eic | unit_conversion_error | 33 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.8421 | 0.8381 | 0.0000 | 0.3158 | 0.0000 | 0.6842 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.0000 | 0.1200 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| mathedu | Comprehension error | 32 | 0.9375 | 0.9373 | 0.0000 | 0.1250 | 0.0000 | 0.8750 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.9130 | 0.9129 | 0.0833 | 0.0909 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9186 | 0.9181 | 0.0000 | 0.1628 | 0.0000 | 0.8372 |
| stepwise | Calculation error easily solved by a calculator | 11 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.8182 | 0.8036 | 0.0000 | 0.4000 | 0.0000 | 0.6000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.8889 | 0.8875 | 0.1000 | 0.1250 | 0.0000 | 0.8750 |
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

