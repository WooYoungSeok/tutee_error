# Verifier evaluation — baseline_test_augmented

model `WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9133 | 0.9133 | 0.1429 | 0.0203 | 0.0000 | 0.9506 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8849, 0.9409], macro_f1 [0.8848, 0.9409], pair_accuracy [0.9250, 0.9717]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8532 | 0.9797 | 0.9120 | 344 | 0 |
| not_aligned | 0.9803 | 0.8571 | 0.9146 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.2419 | 0.1948 | 0.7581 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9680 | 0.4919 | 0.0320 | - | 0.0000 | - |
| v2_positive | 344 | 0.9797 | 0.4949 | - | 0.0203 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.8769 | 0.8768 | 0.2070 | 0.0117 | 0.0000 | 0.9591 |
| mathclean | 92 | 0.9674 | 0.9674 | 0.0217 | 0.0435 | 0.0000 | 0.9348 |
| mathedu | 173 | 0.9538 | 0.9537 | 0.0690 | 0.0233 | 0.0000 | 0.9302 |
| stepwise | 87 | 0.9425 | 0.9425 | 0.0870 | 0.0244 | 0.0000 | 0.9756 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.8491 | 0.8490 | 0.2581 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 48 | 0.8333 | 0.8333 | 0.2857 | 0.0000 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 51 | 0.8431 | 0.8431 | 0.2667 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 34 | 0.9412 | 0.9410 | 0.1053 | 0.0000 | 0.0000 | 0.9333 |
| eic | operator_error | 40 | 0.8750 | 0.8749 | 0.2174 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 56 | 0.8214 | 0.8205 | 0.2424 | 0.0870 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 47 | 0.8511 | 0.8508 | 0.2500 | 0.0000 | 0.0000 | 1.0000 |
| eic | unit_conversion_error | 33 | 0.9697 | 0.9697 | 0.0588 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9474 | 0.9472 | 0.0000 | 0.1053 | 0.0000 | 0.8947 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.8696 | 0.8686 | 0.2500 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9535 | 0.9535 | 0.0465 | 0.0465 | 0.0000 | 0.9302 |
| stepwise | Calculation error easily solved by a calculator | 11 | 0.9091 | 0.9091 | 0.1667 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.8636 | 0.8634 | 0.1667 | 0.1000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.9444 | 0.9443 | 0.1000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9583 | 0.4894 | 0.0417 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

