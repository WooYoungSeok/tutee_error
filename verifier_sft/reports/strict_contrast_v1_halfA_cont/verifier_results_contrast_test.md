# Verifier results

split `contrast_test` · data sha256 `937668efa6cb375e` · rows 202

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline_contrast_test (none) | sft_epoch1_contrast_test (none) | sft_epoch2_contrast_test (none) | sft_epoch3_contrast_test (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.7327 | 0.3119 | 0.8119 | 0.8614 |
| macro-F1 | 0.5792 | 0.2377 | 0.7923 | 0.8307 |
| aligned F1 | 0.8333 | 0.0000 | 0.8561 | 0.9028 |
| not_aligned F1 | 0.3250 | 0.4755 | 0.7286 | 0.7586 |
| negative acceptance rate | 0.7937 | 0.0000 | 0.1905 | 0.3016 |
| positive rejection rate | 0.0288 | 1.0000 | 0.1871 | 0.0647 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | - | - | - | - |
| accuracy 95% CI | [0.6432, 0.8187] | [0.2146, 0.4093] | [0.7500, 0.8677] | [0.7976, 0.9150] |
| macro-F1 95% CI | [0.4964, 0.6592] | [0.1767, 0.2904] | [0.7393, 0.8365] | [0.7566, 0.8883] |

## Accuracy by dataset

| dataset | baseline_contrast_test | sft_epoch1_contrast_test | sft_epoch2_contrast_test | sft_epoch3_contrast_test |
| --- | --- | --- | --- | --- |
| eic | 0.7447 | 0.3032 | 0.8191 | 0.8670 |
| mathedu | 0.5000 | 0.5000 | 1.0000 | 1.0000 |
| stepwise | 0.5833 | 0.4167 | 0.6667 | 0.7500 |

## Macro-F1 by dataset

| dataset | baseline_contrast_test | sft_epoch1_contrast_test | sft_epoch2_contrast_test | sft_epoch3_contrast_test |
| --- | --- | --- | --- | --- |
| eic | 0.5877 | 0.2327 | 0.7954 | 0.8329 |
| mathedu | 0.3333 | 0.3333 | 1.0000 | 1.0000 |
| stepwise | 0.4958 | 0.2941 | 0.6571 | 0.7483 |

