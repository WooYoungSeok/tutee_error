# Train halves — independent verifiers

Created (UTC): 2026-09-28T02:49:53Z · seed 42 · source `config/descriptive_verifier_v2.json` (train sha256 `b06ce1ead4757ad4`)

Half A trains the Qwen2.5-Math-7B-Instruct verifier; half B is reserved for a separate verifier. Question groups are disjoint, and every negative's description comes from the same half, so the halves share no training question or error description. Validation and test are the source files, unchanged.

| half | anchors | pair records | question groups | eic | mathclean | mathedu | stepwise |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1343 | 2686 | 1198 | 647 | 189 | 345 | 162 |
| B | 1381 | 2762 | 1198 | 684 | 189 | 349 | 159 |

## Anchors per source label

| dataset | label | A | B |
| --- | --- | --- | --- |
| eic | adding_irrelevant_information | 79 | 80 |
| eic | calculation_error | 83 | 91 |
| eic | confusing_formula_error | 72 | 75 |
| eic | counting_error | 56 | 68 |
| eic | missing_step | 71 | 67 |
| eic | operator_error | 77 | 83 |
| eic | referencing_context_value_error | 71 | 84 |
| eic | referencing_previous_step_value_error | 70 | 69 |
| eic | unit_conversion_error | 68 | 67 |
| mathclean | computing error | 77 | 78 |
| mathclean | expression error | 9 | 8 |
| mathclean | logic error | 103 | 103 |
| mathedu | Algebraic error | 16 | 17 |
| mathedu | Arithmetical error | 28 | 27 |
| mathedu | Careless error | 11 | 11 |
| mathedu | Comprehension error | 64 | 66 |
| mathedu | Lack of necessary mathematical concepts | 6 | 6 |
| mathedu | Measurement error | 4 | 5 |
| mathedu | Unfinished answer | 44 | 44 |
| mathedu | Wrong mathematical operation/concept | 172 | 173 |
| stepwise | Calculation error easily solved by a calculator | 21 | 20 |
| stepwise | Extra quantity or Missing quantity | 42 | 41 |
| stepwise | Missing / Wrong factual knowledge | 28 | 28 |
| stepwise | Misunderstanding of a question | 51 | 50 |
| stepwise | Reached correct solution but proceeded further | 14 | 14 |
| stepwise | Unit conversion error | 6 | 6 |

## Checks

| check | result |
| --- | --- |
| halves together are exactly the source train anchors | pass |
| no anchor in both halves | pass |
| no question group in both halves | pass |
| [A] every anchor has one positive and one negative | pass |
| [A] positives identical to the source positives | pass |
| [A] negative donor from the same half | pass |
| [A] negative donor from the same dataset | pass |
| [A] negative donor label differs (normalized) | pass |
| [A] negative donor from a different question group | pass |
| [A] no pair over 4096 tokens | pass |
| [B] every anchor has one positive and one negative | pass |
| [B] positives identical to the source positives | pass |
| [B] negative donor from the same half | pass |
| [B] negative donor from the same dataset | pass |
| [B] negative donor label differs (normalized) | pass |
| [B] negative donor from a different question group | pass |
| [B] no pair over 4096 tokens | pass |
