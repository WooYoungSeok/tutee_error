# Verifier evaluation — sft_epoch2_test_augmented

model `/home/elicer/tutee_error/verifier_sft/checkpoints/strict_contrast_v1_halfA_cont_20260929_111602/checkpoint-44` · split `test_augmented` · ablation `none` · 750 rows (344 pairs) · data sha256 `f74a6f9b15cc264b`

Targets are automatic (other-label negatives, no semantic review): these are agreement rates with the automatic targets. Invalid outputs count as wrong.

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 750 | 0.8400 | 0.8328 | 0.0320 | 0.3110 | 0.0000 | 0.6890 |

95% intervals (question-group bootstrap, 1000 samples): accuracy [0.8166, 0.8645], macro_f1 [0.8064, 0.8599], pair_accuracy [0.6374, 0.7397]

| class | precision | recall | F1 | support | invalid |
| --- | --- | --- | --- | --- | --- |
| aligned | 0.9480 | 0.6890 | 0.7980 | 344 | 0 |
| not_aligned | 0.7860 | 0.9680 | 0.8675 | 406 | 0 |

## By row source

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| audited_cross_same_question | 62 | 0.8226 | 0.4513 | 0.1774 | - | 0.0000 | - |
| v2_negative_other_question | 344 | 0.9942 | 0.4985 | 0.0058 | - | 0.0000 | - |
| v2_positive | 344 | 0.6890 | 0.4079 | - | 0.3110 | 0.0000 | - |

## By dataset

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 398 | 0.8719 | 0.8663 | 0.0573 | 0.2222 | 0.0000 | 0.7778 |
| mathclean | 92 | 0.7826 | 0.7718 | 0.0000 | 0.4348 | 0.0000 | 0.5652 |
| mathedu | 173 | 0.8035 | 0.7951 | 0.0000 | 0.3953 | 0.0000 | 0.6047 |
| stepwise | 87 | 0.8276 | 0.8180 | 0.0000 | 0.3659 | 0.0000 | 0.6341 |

## By anchor source label

| group | n | accuracy | macro-F1 | neg. acceptance | pos. rejection | invalid | pair acc. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 53 | 0.9434 | 0.9427 | 0.0968 | 0.0000 | 0.0000 | 1.0000 |
| eic | calculation_error | 48 | 0.7917 | 0.7656 | 0.0357 | 0.4500 | 0.0000 | 0.5500 |
| eic | confusing_formula_error | 51 | 0.8824 | 0.8801 | 0.1333 | 0.0952 | 0.0000 | 0.9048 |
| eic | counting_error | 36 | 0.8611 | 0.8584 | 0.0000 | 0.2778 | 0.0000 | 0.7222 |
| eic | missing_step | 34 | 0.8529 | 0.8419 | 0.0000 | 0.3333 | 0.0000 | 0.6667 |
| eic | operator_error | 40 | 0.8500 | 0.8400 | 0.0435 | 0.2941 | 0.0000 | 0.7059 |
| eic | referencing_context_value_error | 56 | 0.8393 | 0.8301 | 0.0909 | 0.2609 | 0.0000 | 0.7391 |
| eic | referencing_previous_step_value_error | 47 | 0.8511 | 0.8366 | 0.0357 | 0.3158 | 0.0000 | 0.6842 |
| eic | unit_conversion_error | 33 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | computing error | 38 | 0.6842 | 0.6492 | 0.0000 | 0.6316 | 0.0000 | 0.3684 |
| mathclean | expression error | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathclean | logic error | 50 | 0.8400 | 0.8358 | 0.0000 | 0.3200 | 0.0000 | 0.6800 |
| mathedu | Algebraic error | 8 | 0.6250 | 0.5636 | 0.0000 | 0.7500 | 0.0000 | 0.2500 |
| mathedu | Arithmetical error | 14 | 0.7143 | 0.6889 | 0.0000 | 0.5714 | 0.0000 | 0.4286 |
| mathedu | Careless error | 6 | 0.5000 | 0.3333 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| mathedu | Comprehension error | 32 | 0.8125 | 0.8057 | 0.0000 | 0.3750 | 0.0000 | 0.6250 |
| mathedu | Lack of necessary mathematical concepts | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Measurement error | 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| mathedu | Unfinished answer | 23 | 0.9130 | 0.9115 | 0.0000 | 0.1818 | 0.0000 | 0.8182 |
| mathedu | Wrong mathematical operation/concept | 86 | 0.8140 | 0.8073 | 0.0000 | 0.3721 | 0.0000 | 0.6279 |
| stepwise | Calculation error easily solved by a calculator | 11 | 0.9091 | 0.9060 | 0.0000 | 0.2000 | 0.0000 | 0.8000 |
| stepwise | Extra quantity or Missing quantity | 22 | 0.7273 | 0.6857 | 0.0000 | 0.6000 | 0.0000 | 0.4000 |
| stepwise | Missing / Wrong factual knowledge | 18 | 0.8333 | 0.8194 | 0.0000 | 0.3750 | 0.0000 | 0.6250 |
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

