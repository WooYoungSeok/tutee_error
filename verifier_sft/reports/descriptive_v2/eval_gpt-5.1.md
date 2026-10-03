# Verifier evaluation — gpt-5.1

model `api:gpt-5.1` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9201 | 0.9201 | 0.0756 | 0.0843 | 0.0000 | 0.8430 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8988, 0.9392], macro_f1 [0.8988, 0.9392], pair_accuracy [0.8006, 0.8807]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9238 | 0.9157 | 0.9197 | 344 | 0 |
| not_aligned | 0.9164 | 0.9244 | 0.9204 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9269 | 0.9269 | 0.0819 | 0.0643 | 0.0000 | 0.8596 |
| mathclean | 92 | 0.9239 | 0.9238 | 0.0435 | 0.1087 | 0.0000 | 0.8478 |
| mathedu | 172 | 0.9012 | 0.9011 | 0.0814 | 0.1163 | 0.0000 | 0.8023 |
| stepwise | 82 | 0.9268 | 0.9268 | 0.0732 | 0.0732 | 0.0000 | 0.8537 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9545 | 0.9545 | 0.0909 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 40 | 0.8750 | 0.8743 | 0.0500 | 0.2000 | 0.0000 | 0.7500 |
| eic | confusing_formula_error | 42 | 0.9762 | 0.9762 | 0.0476 | 0.0000 | 0.0000 | 0.9524 |
| eic | counting_error | 36 | 0.9167 | 0.9166 | 0.0556 | 0.1111 | 0.0000 | 0.8333 |
| eic | missing_step | 30 | 0.9667 | 0.9666 | 0.0667 | 0.0000 | 0.0000 | 0.9333 |
| eic | operator_error | 34 | 0.9412 | 0.9410 | 0.1176 | 0.0000 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 46 | 0.9130 | 0.9129 | 0.1304 | 0.0435 | 0.0000 | 0.8261 |
| eic | referencing_previous_step_value_error | 38 | 0.8421 | 0.8417 | 0.1053 | 0.2105 | 0.0000 | 0.7368 |
| eic | unit_conversion_error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathclean | computing error | 38 | 0.8684 | 0.8676 | 0.0526 | 0.2105 | 0.0000 | 0.7368 |
| mathclean | expression error | 4 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 0.9286 | 0.9282 | 0.0000 | 0.1429 | 0.0000 | 0.8571 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9062 | 0.9062 | 0.1250 | 0.0625 | 0.0000 | 0.8125 |
| mathedu | Lack of necessary mathematical concepts | 2 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9545 | 0.9545 | 0.0000 | 0.0909 | 0.0000 | 0.9091 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8721 | 0.8721 | 0.1163 | 0.1395 | 0.0000 | 0.7442 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9000 | 0.8990 | 0.2000 | 0.0000 | 0.0000 | 0.8000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| stepwise | Misunderstanding of a question | 26 | 0.9231 | 0.9231 | 0.0769 | 0.0769 | 0.0000 | 0.8462 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.9474 | 0.4865 | 0.0526 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9583 | 0.4894 | 0.0417 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |

