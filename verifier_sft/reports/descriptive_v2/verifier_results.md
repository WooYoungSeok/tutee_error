# Verifier results

split `test` · data sha256 `5c344e1d2e71a0b8` · rows 688

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | gpt-5.6-sol (none) | baseline (none) | baseline_gptparse (none) | sft (none) | sft_gptparse (none) |
| --- | --- | --- | --- | --- | --- |
| accuracy | 0.9637 | 0.0000 | 0.7820 | 0.9738 | 0.9738 |
| macro-F1 | 0.9636 | 0.0000 | 0.7808 | 0.9738 | 0.9738 |
| aligned F1 | 0.9644 | 0.0000 | 0.7967 | 0.9740 | 0.9740 |
| not_aligned F1 | 0.9629 | 0.0000 | 0.7649 | 0.9737 | 0.9737 |
| negative acceptance rate | 0.0581 | 0.0029 | 0.2907 | 0.0320 | 0.0320 |
| positive rejection rate | 0.0145 | 0.0000 | 0.1453 | 0.0203 | 0.0203 |
| invalid rate | 0.0000 | 0.9985 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9273 | 0.0000 | 0.5901 | 0.9506 | 0.9506 |
| accuracy 95% CI | [0.9504, 0.9764] | [0.0000, 0.0000] | [0.7515, 0.8103] | [0.9593, 0.9855] | [0.9593, 0.9855] |
| macro-F1 95% CI | [0.9504, 0.9764] | [0.0000, 0.0000] | [0.7499, 0.8093] | [0.9593, 0.9855] | [0.9593, 0.9855] |

## Accuracy by dataset

| dataset | gpt-5.6-sol | baseline | baseline_gptparse | sft | sft_gptparse |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9561 | 0.0000 | 0.8041 | 0.9795 | 0.9795 |
| mathclean | 0.9565 | 0.0000 | 0.6957 | 0.9674 | 0.9674 |
| mathedu | 0.9826 | 0.0000 | 0.7791 | 0.9593 | 0.9593 |
| stepwise | 0.9634 | 0.0000 | 0.7927 | 0.9878 | 0.9878 |

## Macro-F1 by dataset

| dataset | gpt-5.6-sol | baseline | baseline_gptparse | sft | sft_gptparse |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9561 | 0.0000 | 0.8023 | 0.9795 | 0.9795 |
| mathclean | 0.9565 | 0.0000 | 0.6904 | 0.9674 | 0.9674 |
| mathedu | 0.9826 | 0.0000 | 0.7747 | 0.9593 | 0.9593 |
| stepwise | 0.9634 | 0.0000 | 0.7919 | 0.9878 | 0.9878 |

