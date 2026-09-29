# Verifier results

split `test_augmented` · data sha256 `f74a6f9b15cc264b` · rows 750

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline_test_augmented (none) | sft_epoch1_test_augmented (none) | sft_epoch2_test_augmented (none) | sft_epoch3_test_augmented (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.9067 | 0.5413 | 0.8400 | 0.9093 |
| macro-F1 | 0.9067 | 0.3512 | 0.8328 | 0.9083 |
| aligned F1 | 0.9057 | 0.0000 | 0.7980 | 0.8985 |
| not_aligned F1 | 0.9077 | 0.7024 | 0.8675 | 0.9181 |
| negative acceptance rate | 0.1527 | 0.0000 | 0.0320 | 0.0616 |
| positive rejection rate | 0.0233 | 1.0000 | 0.3110 | 0.1250 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9390 | 0.0000 | 0.6890 | 0.8576 |
| accuracy 95% CI | [0.8779, 0.9357] | [0.5247, 0.5575] | [0.8166, 0.8645] | [0.8880, 0.9300] |
| macro-F1 95% CI | [0.8778, 0.9357] | [0.3441, 0.3579] | [0.8064, 0.8599] | [0.8869, 0.9293] |

## Accuracy by dataset

| dataset | baseline_test_augmented | sft_epoch1_test_augmented | sft_epoch2_test_augmented | sft_epoch3_test_augmented |
| --- | --- | --- | --- | --- |
| eic | 0.8668 | 0.5704 | 0.8719 | 0.9246 |
| mathclean | 0.9565 | 0.5000 | 0.7826 | 0.8913 |
| mathedu | 0.9480 | 0.5029 | 0.8035 | 0.8960 |
| stepwise | 0.9540 | 0.5287 | 0.8276 | 0.8851 |

## Macro-F1 by dataset

| dataset | baseline_test_augmented | sft_epoch1_test_augmented | sft_epoch2_test_augmented | sft_epoch3_test_augmented |
| --- | --- | --- | --- | --- |
| eic | 0.8668 | 0.3632 | 0.8663 | 0.9238 |
| mathclean | 0.9565 | 0.3333 | 0.7718 | 0.8900 |
| mathedu | 0.9479 | 0.3346 | 0.7951 | 0.8952 |
| stepwise | 0.9540 | 0.3459 | 0.8180 | 0.8824 |

