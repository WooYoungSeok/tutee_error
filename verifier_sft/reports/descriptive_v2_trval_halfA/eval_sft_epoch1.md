# Verifier evaluation — sft_epoch1

model `/home/elicer/tutee_error/verifier_sft/checkpoints/descriptive_verifier_v2_trval_halfA_20260928_065513/checkpoint-95` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9520 | 0.9520 | 0.0436 | 0.0523 | 0.0000 | 0.9041 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9373, 0.9674], macro_f1 [0.9373, 0.9674], pair_accuracy [0.8746, 0.9347]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9560 | 0.9477 | 0.9518 | 344 | 0 |
| not_aligned | 0.9481 | 0.9564 | 0.9522 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9678 | 0.9678 | 0.0292 | 0.0351 | 0.0000 | 0.9357 |
| mathclean | 92 | 0.9348 | 0.9348 | 0.0435 | 0.0870 | 0.0000 | 0.8696 |
| mathedu | 172 | 0.9244 | 0.9244 | 0.0930 | 0.0581 | 0.0000 | 0.8488 |
| stepwise | 82 | 0.9634 | 0.9634 | 0.0000 | 0.0732 | 0.0000 | 0.9268 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9091 | 0.9089 | 0.1364 | 0.0455 | 0.0000 | 0.8182 |
| eic | calculation_error | 40 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | confusing_formula_error | 42 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | counting_error | 36 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | missing_step | 30 | 0.9333 | 0.9333 | 0.0667 | 0.0667 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9706 | 0.9706 | 0.0588 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 46 | 0.9348 | 0.9345 | 0.0000 | 0.1304 | 0.0000 | 0.8696 |
| eic | referencing_previous_step_value_error | 38 | 0.9737 | 0.9737 | 0.0000 | 0.0526 | 0.0000 | 0.9474 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9474 | 0.9472 | 0.0000 | 0.1053 | 0.0000 | 0.8947 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9200 | 0.9200 | 0.0800 | 0.0800 | 0.0000 | 0.8400 |
| mathedu | Algebraic error | 8 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| mathedu | Arithmetical error | 14 | 0.8571 | 0.8542 | 0.0000 | 0.2857 | 0.0000 | 0.7143 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9375 | 0.9373 | 0.1250 | 0.0000 | 0.0000 | 0.8750 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9302 | 0.9302 | 0.0930 | 0.0465 | 0.0000 | 0.8605 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9500 | 0.9499 | 0.0000 | 0.1000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.9375 | 0.9373 | 0.0000 | 0.1250 | 0.0000 | 0.8750 |
| stepwise | Misunderstanding of a question | 26 | 0.9615 | 0.9615 | 0.0000 | 0.0769 | 0.0000 | 0.9231 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.9286 | 0.4815 | 0.0714 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

