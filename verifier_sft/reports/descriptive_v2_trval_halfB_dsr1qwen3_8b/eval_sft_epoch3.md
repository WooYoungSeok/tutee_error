# Verifier evaluation — sft_epoch3

model `/home/elicer/tutee_error/verifier_sft/checkpoints/descriptive_verifier_v2_trval_halfB_dsr1qwen3_8b_20260928_090359/checkpoint-294` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9608 | 0.9607 | 0.0552 | 0.0233 | 0.0000 | 0.9244 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9446, 0.9754], macro_f1 [0.9446, 0.9754], pair_accuracy [0.8934, 0.9532]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9465 | 0.9767 | 0.9614 | 344 | 0 |
| not_aligned | 0.9760 | 0.9448 | 0.9601 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9649 | 0.9649 | 0.0468 | 0.0234 | 0.0000 | 0.9298 |
| mathclean | 92 | 0.9674 | 0.9674 | 0.0435 | 0.0217 | 0.0000 | 0.9348 |
| mathedu | 172 | 0.9360 | 0.9359 | 0.1047 | 0.0233 | 0.0000 | 0.8837 |
| stepwise | 82 | 0.9878 | 0.9878 | 0.0000 | 0.0244 | 0.0000 | 0.9756 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9545 | 0.9545 | 0.0909 | 0.0000 | 0.0000 | 0.9091 |
| eic | calculation_error | 40 | 0.9750 | 0.9750 | 0.0500 | 0.0000 | 0.0000 | 0.9500 |
| eic | confusing_formula_error | 42 | 0.9762 | 0.9762 | 0.0476 | 0.0000 | 0.0000 | 0.9524 |
| eic | counting_error | 36 | 0.9722 | 0.9722 | 0.0556 | 0.0000 | 0.0000 | 0.9444 |
| eic | missing_step | 30 | 0.9333 | 0.9333 | 0.0667 | 0.0667 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9706 | 0.9706 | 0.0588 | 0.0000 | 0.0000 | 0.9412 |
| eic | referencing_context_value_error | 46 | 0.9565 | 0.9564 | 0.0000 | 0.0870 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 38 | 0.9474 | 0.9474 | 0.0526 | 0.0526 | 0.0000 | 0.8947 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9737 | 0.9737 | 0.0000 | 0.0526 | 0.0000 | 0.9474 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9600 | 0.9599 | 0.0800 | 0.0000 | 0.0000 | 0.9200 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Careless error | 6 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Comprehension error | 32 | 0.9688 | 0.9687 | 0.0625 | 0.0000 | 0.0000 | 0.9375 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.9070 | 0.9068 | 0.1395 | 0.0465 | 0.0000 | 0.8372 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.9500 | 0.9499 | 0.0000 | 0.1000 | 0.0000 | 0.9000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Misunderstanding of a question | 26 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.9286 | 0.4815 | 0.0714 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 0.9167 | 0.4783 | 0.0833 | - | 0.0000 | - |

