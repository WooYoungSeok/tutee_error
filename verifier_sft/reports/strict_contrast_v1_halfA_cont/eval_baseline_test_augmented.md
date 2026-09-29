# Verifier evaluation — baseline_test_augmented

model `WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2-trval-halfA` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.9067 | 0.9067 | 0.1527 | 0.0233 | 0.0000 | 0.9390 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8779, 0.9357], macro_f1 [0.8778, 0.9357], pair_accuracy [0.9104, 0.9630]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8442 | 0.9767 | 0.9057 | 344 | 0 |
| not_aligned | 0.9773 | 0.8473 | 0.9077 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.2097 | 0.1733 | 0.7903 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9622 | 0.4904 | 0.0378 | - | 0.0000 | - |
| v2_positive | 344 | 0.9767 | 0.4941 | - | 0.0233 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.8668 | 0.8668 | 0.2203 | 0.0175 | 0.0000 | 0.9474 |
| mathclean | 92 | 0.9565 | 0.9565 | 0.0217 | 0.0652 | 0.0000 | 0.9130 |
| mathedu | 173 | 0.9480 | 0.9479 | 0.0805 | 0.0233 | 0.0000 | 0.9070 |
| stepwise | 87 | 0.9540 | 0.9540 | 0.0870 | 0.0000 | 0.0000 | 1.0000 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.8302 | 0.8302 | 0.2903 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 48 | 0.8333 | 0.8330 | 0.2500 | 0.0500 | 0.0000 | 0.9000 |
| eic | confusing_formula_error | 51 | 0.8431 | 0.8431 | 0.2667 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 34 | 0.8824 | 0.8824 | 0.2105 | 0.0000 | 0.0000 | 0.9333 |
| eic | operator_error | 40 | 0.8500 | 0.8500 | 0.2609 | 0.0000 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 56 | 0.8393 | 0.8388 | 0.2424 | 0.0435 | 0.0000 | 0.9565 |
| eic | referencing_previous_step_value_error | 47 | 0.8298 | 0.8291 | 0.2500 | 0.0526 | 0.0000 | 0.9474 |
| eic | unit_conversion_error | 33 | 0.9697 | 0.9697 | 0.0588 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9211 | 0.9206 | 0.0000 | 0.1579 | 0.0000 | 0.8421 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.8696 | 0.8686 | 0.2500 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9302 | 0.9302 | 0.0930 | 0.0465 | 0.0000 | 0.8605 |
| stepwise | Calculation error easily solved by a calculator | 11 | 0.9091 | 0.9091 | 0.1667 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.9091 | 0.9091 | 0.1667 | 0.0000 | 0.0000 | 1.0000 |
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

