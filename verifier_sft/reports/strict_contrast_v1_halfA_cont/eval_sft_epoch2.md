# Verifier evaluation — sft_epoch2

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-44` · split `test` · ablation `none` · 688 rows (344 pairs) · data sha256 `5c344e1d2e71a0b8`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 688 | 0.8416 | 0.8378 | 0.0058 | 0.3110 | 0.0000 | 0.6890 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8155, 0.8686], macro_f1 [0.8094, 0.8663], pair_accuracy [0.6374, 0.7397]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9916 | 0.6890 | 0.8130 | 344 | 0 |
| not_aligned | 0.7617 | 0.9942 | 0.8625 | 344 | 0 |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 342 | 0.8830 | 0.8817 | 0.0117 | 0.2222 | 0.0000 | 0.7778 |
| mathclean | 92 | 0.7826 | 0.7718 | 0.0000 | 0.4348 | 0.0000 | 0.5652 |
| mathedu | 172 | 0.8023 | 0.7943 | 0.0000 | 0.3953 | 0.0000 | 0.6047 |
| stepwise | 82 | 0.8171 | 0.8107 | 0.0000 | 0.3659 | 0.0000 | 0.6341 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 44 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 40 | 0.7500 | 0.7396 | 0.0500 | 0.4500 | 0.0000 | 0.5500 |
| eic | confusing_formula_error | 42 | 0.9524 | 0.9523 | 0.0000 | 0.0952 | 0.0000 | 0.9048 |
| eic | counting_error | 36 | 0.8611 | 0.8584 | 0.0000 | 0.2778 | 0.0000 | 0.7222 |
| eic | missing_step | 30 | 0.8333 | 0.8286 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| eic | operator_error | 34 | 0.8235 | 0.8211 | 0.0588 | 0.2941 | 0.0000 | 0.7059 |
| eic | referencing_context_value_error | 46 | 0.8696 | 0.8673 | 0.0000 | 0.2609 | 0.0000 | 0.7391 |
| eic | referencing_previous_step_value_error | 38 | 0.8421 | 0.8381 | 0.0000 | 0.3158 | 0.0000 | 0.6842 |
| eic | unit_conversion_error | 32 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.6842 | 0.6492 | 0.0000 | 0.6316 | 0.0000 | 0.3684 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.8400 | 0.8358 | 0.0000 | 0.3200 | 0.0000 | 0.6800 |
| mathedu | Algebraic error | 8 | 0.6250 | 0.5636 | 0.0000 | 0.7500 | 0.0000 | 0.2500 |
| mathedu | Arithmetical error | 14 | 0.7143 | 0.6889 | 0.0000 | 0.5714 | 0.0000 | 0.4286 |
| mathedu | Careless error | 6 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.8125 | 0.8057 | 0.0000 | 0.3750 | 0.0000 | 0.6250 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 22 | 0.9091 | 0.9083 | 0.0000 | 0.1818 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8140 | 0.8073 | 0.0000 | 0.3721 | 0.0000 | 0.6279 |
| stepwise | Calculation error easily solved by a calculator | 10 | 0.9000 | 0.8990 | 0.0000 | 0.2000 | 0.0000 | 0.8000 |
| stepwise | Extra quantity or Missing quantity | 20 | 0.7000 | 0.6703 | 0.0000 | 0.6000 | 0.0000 | 0.4000 |
| stepwise | Missing / Wrong factual knowledge | 16 | 0.8125 | 0.8057 | 0.0000 | 0.3750 | 0.0000 | 0.6250 |
| stepwise | Misunderstanding of a question | 26 | 0.8077 | 0.8003 | 0.0000 | 0.3846 | 0.0000 | 0.6154 |
| stepwise | Reached correct solution but proceeded further | 8 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| stepwise | Unit conversion error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Negatives by anchor <- donor label (n >= 10)

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | computing error <- logic error | 19 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathclean | logic error <- computing error | 24 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Comprehension error | 14 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |
| mathedu | Wrong mathematical operation/concept <- Unfinished answer | 12 | 1.0000 | 0.5000 | 0.0000 | - | 0.0000 | - |

