# Verifier evaluation — baseline_gptparse

model `Qwen/Qwen2.5-Math-7B-Instruct` · split `test` · ablation `none` · 744 rows (372 pairs) · data sha256 `7f6686621324b2d1`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 744 | 0.7849 | 0.7839 | 0.2849 | 0.1452 | 0.0000 | 0.5860 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.7598, 0.8118], macro_f1 [0.7582, 0.8111], pair_accuracy [0.5392, 0.6383]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.7500 | 0.8548 | 0.7990 | 372 | 0 |
| not_aligned | 0.8313 | 0.7151 | 0.7688 | 372 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.8246 | 0.8235 | 0.2515 | 0.0994 | 0.0000 | 0.6550 |
| mathclean | 92 | 0.6739 | 0.6637 | 0.1522 | 0.5000 | 0.0000 | 0.4348 |
| mathedu | 170 | 0.7412 | 0.7329 | 0.4353 | 0.0824 | 0.0000 | 0.4941 |
| stepwise | 140 | 0.8143 | 0.8129 | 0.2714 | 0.1000 | 0.0000 | 0.6286 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 0.8864 | 0.8863 | 0.0909 | 0.1364 | 0.0000 | 0.7727 |
| eic | calculation_error | 40 | 0.8000 | 0.7995 | 0.2500 | 0.1500 | 0.0000 | 0.6000 |
| eic | confusing_formula_error | 42 | 0.8095 | 0.8056 | 0.3333 | 0.0476 | 0.0000 | 0.6190 |
| eic | counting_error | 36 | 0.8611 | 0.8601 | 0.2222 | 0.0556 | 0.0000 | 0.7222 |
| eic | missing_step | 28 | 0.8571 | 0.8542 | 0.2857 | 0.0000 | 0.0000 | 0.7143 |
| eic | operator_error | 36 | 0.8333 | 0.8328 | 0.2222 | 0.1111 | 0.0000 | 0.6667 |
| eic | referencing_context_value_error | 44 | 0.7727 | 0.7708 | 0.3182 | 0.1364 | 0.0000 | 0.5909 |
| eic | referencing_previous_step_value_error | 40 | 0.8000 | 0.7954 | 0.3500 | 0.0500 | 0.0000 | 0.6000 |
| eic | unit_conversion_error | 32 | 0.8125 | 0.8125 | 0.1875 | 0.1875 | 0.0000 | 0.6250 |
| mathclean | computing error | 38 | 0.6579 | 0.6519 | 0.2105 | 0.4737 | 0.0000 | 0.4211 |
| mathclean | expression error | 4 | 0.2500 | 0.2000 | 0.5000 | 1.0000 | 0.0000 | 0.0000 |
| mathclean | logic error | 50 | 0.7200 | 0.7083 | 0.0800 | 0.4800 | 0.0000 | 0.4800 |
| mathedu | Algebraic error | 8 | 0.7500 | 0.7333 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| mathedu | Arithmetical error | 14 | 0.7857 | 0.7846 | 0.2857 | 0.1429 | 0.0000 | 0.5714 |
| mathedu | Careless error | 6 | 0.5000 | 0.4857 | 0.6667 | 0.3333 | 0.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.8125 | 0.8118 | 0.2500 | 0.1250 | 0.0000 | 0.6250 |
| mathedu | Lack of necessary mathematical concepts | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| mathedu | Measurement error | 2 | 0.5000 | 0.3333 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| mathedu | Unfinished answer | 20 | 0.8000 | 0.7917 | 0.4000 | 0.0000 | 0.0000 | 0.6000 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.7209 | 0.7014 | 0.5349 | 0.0233 | 0.0000 | 0.4651 |
| stepwise | Calculation error easily solved by a calculator | 22 | 0.8182 | 0.8120 | 0.3636 | 0.0000 | 0.0000 | 0.6364 |
| stepwise | Extra quantity or Missing quantity | 36 | 0.8056 | 0.7979 | 0.3889 | 0.0000 | 0.0000 | 0.6111 |
| stepwise | Missing / Wrong factual knowledge | 28 | 0.8929 | 0.8927 | 0.1429 | 0.0714 | 0.0000 | 0.7857 |
| stepwise | Misunderstanding of a question | 42 | 0.7857 | 0.7856 | 0.1905 | 0.2381 | 0.0000 | 0.5714 |
| stepwise | Reached correct solution but proceeded further | 8 | 0.7500 | 0.7500 | 0.2500 | 0.2500 | 0.0000 | 0.5000 |
| stepwise | Unit conversion error | 4 | 0.7500 | 0.7333 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 17 | 0.7647 | 0.4333 | 0.2353 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 23 | 0.9130 | 0.4773 | 0.0870 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 13 | 0.6923 | 0.4091 | 0.3077 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 13 | 0.2308 | 0.1875 | 0.7692 | - | 0.0000 | - |
| stepwise | Missing / Wrong factual knowledge <- Misunderstanding of a question | 10 | 0.8000 | 0.4444 | 0.2000 | - | 0.0000 | - |

