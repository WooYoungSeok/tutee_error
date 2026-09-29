# Verifier results

split `test_augmented` · data sha256 `f74a6f9b15cc264b` · rows 750

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline_test_augmented (none) | sft_epoch1_test_augmented (none) | sft_epoch2_test_augmented (none) | sft_epoch3_test_augmented (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.9133 | 0.9147 | 0.9107 | 0.9147 |
| macro-F1 | 0.9133 | 0.9136 | 0.9095 | 0.9137 |
| aligned F1 | 0.9120 | 0.9042 | 0.8992 | 0.9045 |
| not_aligned F1 | 0.9146 | 0.9231 | 0.9198 | 0.9229 |
| negative acceptance rate | 0.1429 | 0.0542 | 0.0542 | 0.0567 |
| positive rejection rate | 0.0203 | 0.1221 | 0.1308 | 0.1192 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9506 | 0.8750 | 0.8576 | 0.8663 |
| accuracy 95% CI | [0.8849, 0.9409] | [0.8924, 0.9361] | [0.8898, 0.9308] | [0.8944, 0.9351] |
| macro-F1 95% CI | [0.8848, 0.9409] | [0.8907, 0.9354] | [0.8880, 0.9302] | [0.8928, 0.9346] |

## Accuracy by dataset

| dataset | baseline_test_augmented | sft_epoch1_test_augmented | sft_epoch2_test_augmented | sft_epoch3_test_augmented |
| --- | --- | --- | --- | --- |
| eic | 0.8769 | 0.9246 | 0.9347 | 0.9372 |
| mathclean | 0.9674 | 0.9022 | 0.8804 | 0.8913 |
| mathedu | 0.9538 | 0.9075 | 0.8902 | 0.8902 |
| stepwise | 0.9425 | 0.8966 | 0.8736 | 0.8851 |

## Macro-F1 by dataset

| dataset | baseline_test_augmented | sft_epoch1_test_augmented | sft_epoch2_test_augmented | sft_epoch3_test_augmented |
| --- | --- | --- | --- | --- |
| eic | 0.8768 | 0.9236 | 0.9338 | 0.9364 |
| mathclean | 0.9674 | 0.9012 | 0.8787 | 0.8900 |
| mathedu | 0.9537 | 0.9068 | 0.8892 | 0.8892 |
| stepwise | 0.9425 | 0.8945 | 0.8711 | 0.8832 |

