# SFT data — strict_contrast_v1_full_cont

Created (UTC): 2026-09-29T12:16:03Z · positives `audited_only` · half all · audits sha256 `34a00cc79f960873`

Targets are the gpt-5.6-sol audit verdicts (no human review); unclear rows dropped.

## train

rows 1604 · targets {'aligned': 976, 'not_aligned': 628} · question groups 276 · datasets {'eic': 1507, 'mathedu': 37, 'stepwise': 60} · 2×2 contrast blocks 264

| row source → target | rows |
| --- | --- |
| audited_cross_same_question → aligned | 336 |
| audited_cross_same_question → not_aligned | 621 |
| audited_own → aligned | 640 |
| audited_own → not_aligned | 7 |

## contrast_test

rows 202 · targets {'aligned': 139, 'not_aligned': 63} · question groups 32 · datasets {'eic': 188, 'mathedu': 2, 'stepwise': 12} · 2×2 contrast blocks 22

| row source → target | rows |
| --- | --- |
| audited_cross_same_question → aligned | 62 |
| audited_cross_same_question → not_aligned | 62 |
| audited_own → aligned | 77 |
| audited_own → not_aligned | 1 |

## test_augmented

rows 750: the v2 test unchanged + the audited same-question negatives of the test split

| row source → target | rows |
| --- | --- |
| v2_positive → aligned | 344 |
| v2_negative_other_question → not_aligned | 344 |
| audited_cross_same_question → not_aligned | 62 |

Unclear rows dropped: {'B|cross_same_question': 1}

## Checks

| check | result |
| --- | --- |
| no train question group in the contrast test | pass |
| no train question group in the v2 test | pass |
| no train question group from the other half | pass |
| train negatives are audited rows only | pass |
| pair ids unique | pass |
| augmented test: added rows repeat no v2 test row | pass |
| augmented test: added rows are negatives on v2 test solutions | pass |
| augmented test: pair ids unique | pass |
