# Verifier evaluation — sft_epoch1

model `/home/elicer/tutee_error/verifier_sft/checkpoints/descriptive_verifier_v2_trval_halfB_dsr1qwen3_8b_20260928_090359/checkpoint-98` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.9375 | 0.9374 | 0.1105 | 0.0145 | 0.0000 | 0.8779 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.9189, 0.9551], macro_f1 [0.9185, 0.9551], pair_accuracy [0.8412, 0.9123]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.8992 | 0.9855 | 0.9404 | 344 | 0 |
| not_aligned | 0.9839 | 0.8895 | 0.9344 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.9503 | 0.9502 | 0.0994 | 0.0000 | 0.0000 | 0.9006 |
| mathclean | 92 | 0.9674 | 0.9674 | 0.0435 | 0.0217 | 0.0000 | 0.9348 |
| mathedu | 172 | 0.9186 | 0.9185 | 0.1163 | 0.0465 | 0.0000 | 0.8488 |
| stepwise | 82 | 0.8902 | 0.8889 | 0.2195 | 0.0000 | 0.0000 | 0.7805 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| eic | calculation_error | 40 | 0.9000 | 0.8990 | 0.2000 | 0.0000 | 0.0000 | 0.8000 |
| eic | confusing_formula_error | 42 | 0.9762 | 0.9762 | 0.0476 | 0.0000 | 0.0000 | 0.9524 |
| eic | counting_error | 36 | 0.9722 | 0.9722 | 0.0556 | 0.0000 | 0.0000 | 0.9444 |
| eic | missing_step | 30 | 0.9333 | 0.9330 | 0.1333 | 0.0000 | 0.0000 | 0.8667 |
| eic | operator_error | 34 | 0.9412 | 0.9410 | 0.1176 | 0.0000 | 0.0000 | 0.8824 |
| eic | referencing_context_value_error | 46 | 0.9565 | 0.9564 | 0.0870 | 0.0000 | 0.0000 | 0.9130 |
| eic | referencing_previous_step_value_error | 38 | 0.9737 | 0.9737 | 0.0526 | 0.0000 | 0.0000 | 0.9474 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.9474 | 0.9474 | 0.0526 | 0.0526 | 0.0000 | 0.8947 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.9800 | 0.9800 | 0.0400 | 0.0000 | 0.0000 | 0.9600 |
| mathedu | Algebraic error | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Arithmetical error | 14 | 0.9286 | 0.9282 | 0.0000 | 0.1429 | 0.0000 | 0.8571 |
| mathedu | Careless error | 6 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| mathedu | Comprehension error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.1818 | 0.0000 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8837 | 0.8832 | 0.1860 | 0.0465 | 0.0000 | 0.7907 |
| stepwise | Calculation error easily solved by a calculator | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.8500 | 0.8465 | 0.3000 | 0.0000 | 0.0000 | 0.7000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.9375 | 0.9373 | 0.1250 | 0.0000 | 0.0000 | 0.8750 |
| stepwise | Misunderstanding of a question | 26 | 0.8077 | 0.8003 | 0.3846 | 0.0000 | 0.0000 | 0.6154 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.9474 | 0.4865 | 0.0526 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.9583 | 0.4894 | 0.0417 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.9286 | 0.4815 | 0.0714 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 0.7500 | 0.4286 | 0.2500 | - | 0.0000 | - |

