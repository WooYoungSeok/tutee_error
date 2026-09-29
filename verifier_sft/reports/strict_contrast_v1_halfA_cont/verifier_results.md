# Verifier results

split `test` · data sha256 `5c344e1d2e71a0b8` · rows 688

Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs (no_solution, description_only) are shortcut diagnostics, not model conditions.

| metric | baseline (none) | sft_epoch1 (none) | sft_epoch2 (none) | sft_epoch3 (none) |
| --- | --- | --- | --- | --- |
| accuracy | 0.9695 | 0.5000 | 0.8416 | 0.9273 |
| macro-F1 | 0.9695 | 0.3333 | 0.8378 | 0.9271 |
| aligned F1 | 0.9697 | 0.0000 | 0.8130 | 0.9233 |
| not_aligned F1 | 0.9693 | 0.6667 | 0.8625 | 0.9309 |
| negative acceptance rate | 0.0378 | 0.0000 | 0.0058 | 0.0203 |
| positive rejection rate | 0.0233 | 1.0000 | 0.3110 | 0.1250 |
| invalid rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| pair accuracy | 0.9390 | 0.0000 | 0.6890 | 0.8576 |
| accuracy 95% CI | [0.9552, 0.9815] | [0.5000, 0.5000] | [0.8155, 0.8686] | [0.9083, 0.9468] |
| macro-F1 95% CI | [0.9552, 0.9815] | [0.3333, 0.3333] | [0.8094, 0.8663] | [0.9081, 0.9467] |

## Accuracy by dataset

| dataset | baseline | sft_epoch1 | sft_epoch2 | sft_epoch3 |
| --- | --- | --- | --- | --- |
| eic | 0.9737 | 0.5000 | 0.8830 | 0.9620 |
| mathclean | 0.9565 | 0.5000 | 0.7826 | 0.8913 |
| mathedu | 0.9535 | 0.5000 | 0.8023 | 0.8953 |
| stepwise | 1.0000 | 0.5000 | 0.8171 | 0.8902 |

## Macro-F1 by dataset

| dataset | baseline | sft_epoch1 | sft_epoch2 | sft_epoch3 |
| --- | --- | --- | --- | --- |
| eic | 0.9737 | 0.3333 | 0.8817 | 0.9620 |
| mathclean | 0.9565 | 0.3333 | 0.7718 | 0.8900 |
| mathedu | 0.9535 | 0.3333 | 0.7943 | 0.8947 |
| stepwise | 1.0000 | 0.3333 | 0.8107 | 0.8889 |

