# Verifier results

split `contrast_test` · data sha256 `937668efa6cb375e` · rows 202

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline_contrast_test (none) | sft_epoch1_contrast_test (none) | sft_epoch2_contrast_test (none) | sft_epoch3_contrast_test (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.7475 | 0.8267 | 0.8416 | 0.8465 |
| macro-F1 | 0.6062 | 0.7895 | 0.8121 | 0.8171 |
| aligned F1 | 0.8421 | 0.8780 | 0.8865 | 0.8905 |
| not_aligned F1 | 0.3704 | 0.7009 | 0.7377 | 0.7438 |
| negative acceptance rate | 0.7619 | 0.3492 | 0.2857 | 0.2857 |
| positive rejection rate | 0.0216 | 0.0935 | 0.1007 | 0.0935 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | - | - | - | - |
| accuracy 95% CI | [0.6647, 0.8246] | [0.7476, 0.8956] | [0.7650, 0.9022] | [0.7722, 0.9065] |
| macro-F1 95% CI | [0.5218, 0.6776] | [0.7055, 0.8612] | [0.7320, 0.8763] | [0.7378, 0.8796] |

## Accuracy by dataset

| dataset | baseline_contrast_test | sft_epoch1_contrast_test | sft_epoch2_contrast_test | sft_epoch3_contrast_test |
| --- | --- | --- | --- | --- |
| eic | 0.7606 | 0.8298 | 0.8564 | 0.8617 |
| mathedu | 0.5000 | 1.0000 | 1.0000 | 1.0000 |
| stepwise | 0.5833 | 0.7500 | 0.5833 | 0.5833 |

## Macro-F1 by dataset

| dataset | baseline_contrast_test | sft_epoch1_contrast_test | sft_epoch2_contrast_test | sft_epoch3_contrast_test |
| --- | --- | --- | --- | --- |
| eic | 0.6175 | 0.7873 | 0.8236 | 0.8292 |
| mathedu | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| stepwise | 0.4958 | 0.7483 | 0.5804 | 0.5804 |

