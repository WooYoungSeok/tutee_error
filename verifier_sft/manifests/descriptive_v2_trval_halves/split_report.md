# Train halves — independent verifiers

Created (UTC): 2026-09-28T06:50:35Z · seed 42 · source `config/descriptive_verifier_v2.json` (train sha256 `b06ce1ead4757ad4`)

Source splits divided: ['train', 'validation']. Half A: trains the Qwen2.5-Math-7B-Instruct verifier on v2 train+validation half A; no validation, every epoch checkpoint kept and chosen afterwards. Half B: trains the deepseek-ai/DeepSeek-R1-0528-Qwen3-8B verifier on v2 train+validation half B; no validation, every epoch checkpoint kept and chosen afterwards. Question groups are disjoint, and every negative's description comes from the same half, so the halves share no training question or error description. Copied unchanged from the source: test.jsonl.

| half | anchors | pair records | question groups | eic | mathclean | mathedu | stepwise |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1511 | 3022 | 1347 | 731 | 212 | 388 | 180 |
| B | 1554 | 3108 | 1347 | 771 | 212 | 392 | 179 |

## Anchors per source label

| dataset | label | A | B |
| --- | --- | --- | --- |
| eic | adding_irrelevant_information | 88 | 90 |
| eic | calculation_error | 94 | 101 |
| eic | confusing_formula_error | 81 | 87 |
| eic | counting_error | 62 | 74 |
| eic | missing_step | 81 | 77 |
| eic | operator_error | 86 | 93 |
| eic | referencing_context_value_error | 83 | 94 |
| eic | referencing_previous_step_value_error | 78 | 79 |
| eic | unit_conversion_error | 78 | 76 |
| mathclean | computing error | 86 | 88 |
| mathclean | expression error | 10 | 9 |
| mathclean | logic error | 116 | 115 |
| mathedu | Algebraic error | 18 | 19 |
| mathedu | Arithmetical error | 31 | 31 |
| mathedu | Careless error | 13 | 12 |
| mathedu | Comprehension error | 72 | 74 |
| mathedu | Lack of necessary mathematical concepts | 6 | 7 |
| mathedu | Measurement error | 5 | 5 |
| mathedu | Unfinished answer | 49 | 49 |
| mathedu | Wrong mathematical operation/concept | 194 | 195 |
| stepwise | Calculation error easily solved by a calculator | 23 | 23 |
| stepwise | Extra quantity or Missing quantity | 47 | 45 |
| stepwise | Missing / Wrong factual knowledge | 31 | 32 |
| stepwise | Misunderstanding of a question | 57 | 56 |
| stepwise | Reached correct solution but proceeded further | 16 | 16 |
| stepwise | Unit conversion error | 6 | 7 |

## Checks

| check | result |
| --- | --- |
| halves together are exactly the source anchors | pass |
| no anchor in both halves | pass |
| no question group in both halves | pass |
| [A] every anchor has one positive and one negative | pass |
| [A] positives identical to the source positives (split set to train) | pass |
| [A] every pair is in split train | pass |
| [A] negative donor from the same half | pass |
| [A] negative donor from the same dataset | pass |
| [A] negative donor label differs (normalized) | pass |
| [A] negative donor from a different question group | pass |
| [A] no pair over 4096 tokens | pass |
| [B] every anchor has one positive and one negative | pass |
| [B] positives identical to the source positives (split set to train) | pass |
| [B] every pair is in split train | pass |
| [B] negative donor from the same half | pass |
| [B] negative donor from the same dataset | pass |
| [B] negative donor label differs (normalized) | pass |
| [B] negative donor from a different question group | pass |
| [B] no pair over 4096 tokens | pass |
