# Verifier evaluation — sft_epoch3_test_augmented

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-66` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9093 | 0.9083 | 0.0616 | 0.1250 | 0.0000 | 0.8576 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8880, 0.9300], macro_f1 [0.8869, 0.9293], pair_accuracy [0.8200, 0.8944]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9233 | 0.8750 | 0.8985 | 344 | 0 |
| not_aligned | 0.8986 | 0.9384 | 0.9181 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.7097 | 0.4151 | 0.2903 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9797 | 0.4949 | 0.0203 | - | 0.0000 | - |
| v2_positive | 344 | 0.8750 | 0.4667 | - | 0.1250 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.9246 | 0.9238 | 0.0969 | 0.0468 | 0.0000 | 0.9240 |
| mathclean | 92 | 0.8913 | 0.8900 | 0.0000 | 0.2174 | 0.0000 | 0.7826 |
| mathedu | 173 | 0.8960 | 0.8952 | 0.0230 | 0.1860 | 0.0000 | 0.8023 |
| stepwise | 87 | 0.8851 | 0.8824 | 0.0217 | 0.2195 | 0.0000 | 0.7805 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.9057 | 0.9051 | 0.1613 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 48 | 0.8958 | 0.8936 | 0.1071 | 0.1000 | 0.0000 | 0.8500 |
| eic | confusing_formula_error | 51 | 0.9020 | 0.9006 | 0.1333 | 0.0476 | 0.0000 | 0.9524 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 34 | 0.8529 | 0.8497 | 0.1053 | 0.2000 | 0.0000 | 0.8000 |
| eic | operator_error | 40 | 0.9000 | 0.8990 | 0.1304 | 0.0588 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 56 | 0.9107 | 0.9093 | 0.1212 | 0.0435 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 47 | 0.9787 | 0.9781 | 0.0357 | 0.0000 | 0.0000 | 1.0000 |
| eic | unit_conversion_error | 33 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.8158 | 0.8093 | 0.0000 | 0.3684 | 0.0000 | 0.6316 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9400 | 0.9398 | 0.0000 | 0.1200 | 0.0000 | 0.8800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 0.6667 | 0.6250 | 0.0000 | 0.6667 | 0.0000 | 0.3333 |
| mathedu | Comprehension error | 32 | 0.9688 | 0.9687 | 0.0000 | 0.0625 | 0.0000 | 0.9375 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.9565 | 0.9565 | 0.0833 | 0.0000 | 0.0000 | 0.9091 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8837 | 0.8827 | 0.0233 | 0.2093 | 0.0000 | 0.7907 |
| stepwise | Calculation error easily solved by a calculator | 11 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.8636 | 0.8562 | 0.0000 | 0.3000 | 0.0000 | 0.7000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.8333 | 0.8286 | 0.1000 | 0.2500 | 0.0000 | 0.7500 |
| stepwise | Misunderstanding of a question | 26 | 0.8462 | 0.8424 | 0.0000 | 0.3077 | 0.0000 | 0.6923 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

