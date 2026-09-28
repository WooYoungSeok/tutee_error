# Verifier evaluation — baseline_gptparse

model `Qwen/Qwen2.5-Math-7B-Instruct` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.7820 | 0.7808 | 0.2907 | 0.1453 | 0.0000 | 0.5901 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7515, 0.8103], macro_f1 [0.7499, 0.8093], pair_accuracy [0.5364, 0.6402]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.7462 | 0.8547 | 0.7967 | 344 | 0 |
| not_aligned | 0.8299 | 0.7093 | 0.7649 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.8041 | 0.8023 | 0.2924 | 0.0994 | 0.0000 | 0.6199 |
| mathclean | 92 | 0.6957 | 0.6904 | 0.1739 | 0.4348 | 0.0000 | 0.4783 |
| mathedu | 172 | 0.7791 | 0.7747 | 0.3605 | 0.0814 | 0.0000 | 0.5814 |
| stepwise | 82 | 0.7927 | 0.7919 | 0.2683 | 0.1463 | 0.0000 | 0.6098 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.7955 | 0.7953 | 0.1818 | 0.2273 | 0.0000 | 0.5909 |
| eic | calculation_error | 40 | 0.8000 | 0.7995 | 0.2500 | 0.1500 | 0.0000 | 0.6000 |
| eic | confusing_formula_error | 42 | 0.8333 | 0.8309 | 0.2857 | 0.0476 | 0.0000 | 0.6667 |
| eic | counting_error | 36 | 0.8056 | 0.8017 | 0.3333 | 0.0556 | 0.0000 | 0.6111 |
| eic | missing_step | 30 | 0.8667 | 0.8643 | 0.2667 | 0.0000 | 0.0000 | 0.7333 |
| eic | operator_error | 34 | 0.7941 | 0.7896 | 0.3529 | 0.0588 | 0.0000 | 0.5882 |
| eic | referencing_context_value_error | 46 | 0.7609 | 0.7552 | 0.3913 | 0.0870 | 0.0000 | 0.5217 |
| eic | referencing_previous_step_value_error | 38 | 0.8684 | 0.8676 | 0.2105 | 0.0526 | 0.0000 | 0.7368 |
| eic | unit_conversion_error | 32 | 0.7188 | 0.7163 | 0.3750 | 0.1875 | 0.0000 | 0.5625 |
| mathclean | computing error | 38 | 0.6842 | 0.6833 | 0.2632 | 0.3684 | 0.0000 | 0.5263 |
| mathclean | expression error | 4 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | logic error | 50 | 0.7200 | 0.7126 | 0.1200 | 0.4400 | 0.0000 | 0.4800 |
| mathedu | Algebraic error | 8 | 0.8750 | 0.8730 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| mathedu | Arithmetical error | 14 | 0.7857 | 0.7846 | 0.2857 | 0.1429 | 0.0000 | 0.5714 |
| mathedu | Careless error | 6 | 0.6667 | 0.6667 | 0.3333 | 0.3333 | 0.0000 | 0.3333 |
| mathedu | Comprehension error | 32 | 0.9062 | 0.9054 | 0.1875 | 0.0000 | 0.0000 | 0.8125 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| mathedu | Unfinished answer | 22 | 0.8182 | 0.8167 | 0.2727 | 0.0909 | 0.0000 | 0.6364 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.7209 | 0.7081 | 0.4884 | 0.0698 | 0.0000 | 0.4884 |
| stepwise | Calculation error easily solved by a calculator | 10 | 0.9000 | 0.8990 | 0.0000 | 0.2000 | 0.0000 | 0.8000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.7500 | 0.7333 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.8125 | 0.8118 | 0.1250 | 0.2500 | 0.0000 | 0.6250 |
| stepwise | Misunderstanding of a question | 26 | 0.7692 | 0.7636 | 0.3846 | 0.0769 | 0.0000 | 0.6154 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 0.7368 | 0.4242 | 0.2632 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 0.8750 | 0.4667 | 0.1250 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 0.5714 | 0.3636 | 0.4286 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 0.4167 | 0.2941 | 0.5833 | - | 0.0000 | - |

