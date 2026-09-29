# Verifier results

split `test` · data sha256 `5c344e1d2e71a0b8` · rows 688

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline (none) | sft_epoch1 (none) | sft_epoch2 (none) | sft_epoch3 (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.9738 | 0.9375 | 0.9273 | 0.9317 |
| macro-F1 | 0.9738 | 0.9373 | 0.9271 | 0.9315 |
| aligned F1 | 0.9740 | 0.9335 | 0.9228 | 0.9280 |
| not_aligned F1 | 0.9737 | 0.9410 | 0.9313 | 0.9350 |
| negative acceptance rate | 0.0320 | 0.0029 | 0.0145 | 0.0174 |
| positive rejection rate | 0.0203 | 0.1221 | 0.1308 | 0.1192 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9506 | 0.8750 | 0.8576 | 0.8663 |
| accuracy 95% CI | [0.9593, 0.9855] | [0.9194, 0.9540] | [0.9080, 0.9451] | [0.9131, 0.9494] |
| macro-F1 95% CI | [0.9593, 0.9855] | [0.9189, 0.9539] | [0.9077, 0.9450] | [0.9127, 0.9494] |

## Accuracy by dataset

| dataset | baseline | sft_epoch1 | sft_epoch2 | sft_epoch3 |
| --- | --- | --- | --- | --- |
| eic | 0.9795 | 0.9708 | 0.9708 | 0.9737 |
| mathclean | 0.9674 | 0.9022 | 0.8804 | 0.8913 |
| mathedu | 0.9593 | 0.9070 | 0.8895 | 0.8895 |
| stepwise | 0.9878 | 0.9024 | 0.8780 | 0.8902 |

## Macro-F1 by dataset

| dataset | baseline | sft_epoch1 | sft_epoch2 | sft_epoch3 |
| --- | --- | --- | --- | --- |
| eic | 0.9795 | 0.9707 | 0.9708 | 0.9737 |
| mathclean | 0.9674 | 0.9012 | 0.8787 | 0.8900 |
| mathedu | 0.9593 | 0.9064 | 0.8887 | 0.8887 |
| stepwise | 0.9878 | 0.9015 | 0.8769 | 0.8894 |

