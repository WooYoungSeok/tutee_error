# Verifier results

split `test` · data sha256 `5c344e1d2e71a0b8` · rows 688

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | sft_epoch1 (none) | sft_epoch2 (none) | sft_epoch3 (none) | sft_epoch4 (none) | sft_epoch5 (none) |
| --- | --- | --- | --- | --- | --- |
| accuracy | 0.9520 | 0.9506 | 0.9637 | 0.9695 | 0.9695 |
| macro-F1 | 0.9520 | 0.9506 | 0.9636 | 0.9695 | 0.9695 |
| aligned F1 | 0.9518 | 0.9506 | 0.9644 | 0.9697 | 0.9698 |
| not_aligned F1 | 0.9522 | 0.9506 | 0.9629 | 0.9693 | 0.9692 |
| negative acceptance rate | 0.0436 | 0.0494 | 0.0581 | 0.0378 | 0.0407 |
| positive rejection rate | 0.0523 | 0.0494 | 0.0145 | 0.0233 | 0.0203 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9041 | 0.9041 | 0.9273 | 0.9390 | 0.9390 |
| accuracy 95% CI | [0.9373, 0.9674] | [0.9319, 0.9672] | [0.9482, 0.9775] | [0.9552, 0.9815] | [0.9563, 0.9812] |
| macro-F1 95% CI | [0.9373, 0.9674] | [0.9319, 0.9672] | [0.9482, 0.9775] | [0.9552, 0.9815] | [0.9562, 0.9812] |

## Accuracy by dataset

| dataset | sft_epoch1 | sft_epoch2 | sft_epoch3 | sft_epoch4 | sft_epoch5 |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9678 | 0.9620 | 0.9678 | 0.9737 | 0.9708 |
| mathclean | 0.9348 | 0.9565 | 0.9565 | 0.9565 | 0.9674 |
| mathedu | 0.9244 | 0.9302 | 0.9535 | 0.9535 | 0.9535 |
| stepwise | 0.9634 | 0.9390 | 0.9756 | 1.0000 | 1.0000 |

## Macro-F1 by dataset

| dataset | sft_epoch1 | sft_epoch2 | sft_epoch3 | sft_epoch4 | sft_epoch5 |
| --- | --- | --- | --- | --- | --- |
| eic | 0.9678 | 0.9620 | 0.9678 | 0.9737 | 0.9708 |
| mathclean | 0.9348 | 0.9565 | 0.9565 | 0.9565 | 0.9674 |
| mathedu | 0.9244 | 0.9302 | 0.9534 | 0.9535 | 0.9535 |
| stepwise | 0.9634 | 0.9389 | 0.9756 | 1.0000 | 1.0000 |

