# Verifier evaluation — sft_epoch2_test_augmented

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_full_cont_20260929_121614/checkpoint-102` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9107 | 0.9095 | 0.0542 | 0.1308 | 0.0000 | 0.8576 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8898, 0.9308], macro_f1 [0.8880, 0.9302], pair_accuracy [0.8209, 0.8920]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9315 | 0.8692 | 0.8992 | 344 | 0 |
| not_aligned | 0.8951 | 0.9458 | 0.9198 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.7258 | 0.4206 | 0.2742 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9855 | 0.4963 | 0.0145 | - | 0.0000 | - |
| v2_positive | 344 | 0.8692 | 0.4650 | - | 0.1308 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.9347 | 0.9338 | 0.0793 | 0.0468 | 0.0000 | 0.9415 |
| mathclean | 92 | 0.8804 | 0.8787 | 0.0000 | 0.2391 | 0.0000 | 0.7609 |
| mathedu | 173 | 0.8902 | 0.8892 | 0.0230 | 0.1977 | 0.0000 | 0.7907 |
| stepwise | 87 | 0.8736 | 0.8711 | 0.0435 | 0.2195 | 0.0000 | 0.7561 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.9623 | 0.9616 | 0.0645 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 48 | 0.8958 | 0.8947 | 0.1429 | 0.0500 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 51 | 0.9412 | 0.9404 | 0.1000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 34 | 0.9118 | 0.9111 | 0.1053 | 0.0667 | 0.0000 | 0.8667 |
| eic | operator_error | 40 | 0.9000 | 0.8977 | 0.0870 | 0.1176 | 0.0000 | 0.8235 |
| eic | referencing_context_value_error | 56 | 0.9107 | 0.9083 | 0.0909 | 0.0870 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 47 | 0.9149 | 0.9117 | 0.0714 | 0.1053 | 0.0000 | 0.8947 |
| eic | unit_conversion_error | 33 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.7895 | 0.7797 | 0.0000 | 0.4211 | 0.0000 | 0.5789 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.0000 | 0.1200 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| mathedu | Comprehension error | 32 | 0.9062 | 0.9054 | 0.0000 | 0.1875 | 0.0000 | 0.8125 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.9565 | 0.9562 | 0.0000 | 0.0909 | 0.0000 | 0.9091 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8837 | 0.8832 | 0.0465 | 0.1860 | 0.0000 | 0.7907 |
| stepwise | Calculation error easily solved by a calculator | 11 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.8636 | 0.8562 | 0.0000 | 0.3000 | 0.0000 | 0.7000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.7778 | 0.7662 | 0.1000 | 0.3750 | 0.0000 | 0.6250 |
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

