# Verifier results

split `test` · data sha256 `5c344e1d2e71a0b8` · rows 688

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | sft_epoch1 (none) | sft_epoch2 (none) | sft_epoch3 (none) | sft_epoch4 (none) | sft_epoch5 (none) |
| --- | --- | --- | --- | --- | --- |
| accuracy | 0.9375 | 0.9535 | 0.9608 | 0.9622 | 0.9651 |
| macro-F1 | 0.9374 | 0.9535 | 0.9607 | 0.9622 | 0.9651 |
| aligned F1 | 0.9404 | 0.9539 | 0.9614 | 0.9631 | 0.9658 |
| not_aligned F1 | 0.9344 | 0.9531 | 0.9601 | 0.9613 | 0.9644 |
| negative acceptance rate | 0.1105 | 0.0552 | 0.0552 | 0.0610 | 0.0552 |
| positive rejection rate | 0.0145 | 0.0378 | 0.0233 | 0.0145 | 0.0145 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.8779 | 0.9099 | 0.9244 | 0.9244 | 0.9302 |
| accuracy 95% CI | [0.9189, 0.9551] | [0.9364, 0.9695] | [0.9446, 0.9754] | [0.9474, 0.9758] | [0.9507, 0.9775] |
| macro-F1 95% CI | [0.9185, 0.9551] | [0.9364, 0.9695] | [0.9446, 0.9754] | [0.9474, 0.9758] | [0.9507, 0.9775] |

## Accuracy by dataset

| dataset | sft_epoch1 | sft_epoch2 | sft_epoch3 | sft_epoch4 | sft_epoch5 |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9503 | 0.9532 | 0.9649 | 0.9678 | 0.9678 |
| mathclean | 0.9674 | 0.9674 | 0.9674 | 0.9783 | 0.9783 |
| mathedu | 0.9186 | 0.9302 | 0.9360 | 0.9302 | 0.9419 |
| stepwise | 0.8902 | 0.9878 | 0.9878 | 0.9878 | 0.9878 |

## Macro-F1 by dataset

| dataset | sft_epoch1 | sft_epoch2 | sft_epoch3 | sft_epoch4 | sft_epoch5 |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9502 | 0.9532 | 0.9649 | 0.9678 | 0.9678 |
| mathclean | 0.9674 | 0.9674 | 0.9674 | 0.9783 | 0.9783 |
| mathedu | 0.9185 | 0.9302 | 0.9359 | 0.9300 | 0.9417 |
| stepwise | 0.8889 | 0.9878 | 0.9878 | 0.9878 | 0.9878 |

