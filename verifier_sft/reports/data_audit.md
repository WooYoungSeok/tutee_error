# Data audit — descriptive_verifier_v1

Created (UTC): 2026-09-23T13:18:59Z · seed 42 · config sha256 `ffa49fcffd4969d8`

Targets are assigned automatically (own description = aligned, description from a case with a different source label = not_aligned). No semantic review of negatives was done; metrics on these pairs measure agreement with the automatic targets, not human-verified alignment.

## 1. Inputs

| input | path | sha256 |
| --- | --- | --- |
| pool | ../data/full/pool.jsonl | `5d7c784aba6487bd` |
| descriptions | ../outputs/runs/v4__gpt-5.6-luna__full/parsed.jsonl | `3cb03e02e6f97253` |
| description_run_meta | ../outputs/runs/v4__gpt-5.6-luna__full/run_meta.json | `ce668d1db683f4ea` |
| prompt_dev_manifest | ../data/manifest/sample_manifest.jsonl | `4a1e56b2a5cf5358` |

Descriptions: model `gpt-5.6-luna`, prompt v4 (`28ef5467bbbac5ce`), run `v4__gpt-5.6-luna__full`.

## 2. Case selection

| dataset | cases | description_status:ambiguous | description_status:label_conflict | duplicate_record | missing_essential_information | eligible |
| --- | --- | --- | --- | --- | --- | --- |
| eic | 1722 | 0 | 38 | 7 | 0 | 1677 |
| mathclean | 610 | 5 | 132 | 0 | 3 | 470 |
| mathedu | 888 | 1 | 21 | 0 | 0 | 866 |
| stepwise | 766 | 0 | 77 | 0 | 0 | 689 |
| total | 3986 | 6 | 268 | 7 | 3 | 3702 |

Held out for missing essential information (found by keyword scan for figure/diagram/graph/table references without [asy] code, then read manually):

- `mathclean:3fa3a27b6b350aa5`: question refers to 'a more complex figure' that is not included
- `mathclean:5420672e35b7999b`: vertex labels B and G depend on a cube figure that is not included
- `mathclean:2018d169dd6fe205`: the sales graph the question refers to is not included

Duplicate records removed: 7 (same dataset, question and solution after NFKC/lowercase/whitespace removal, same normalized label; the smallest sample_id is kept).

## 3. Question groups

- groups: 3114 (key: NFKC, lowercase, all whitespace and punctuation removed); the description pipeline's key (case and whitespace only) gives 3176
- cases per group: {1: 2682, 2: 300, 3: 110, 4: 20, 5: 2}
- groups spanning sources: {'eic-GSM8K + stepwise': 48, 'eic-MathQA + mathedu': 15}
- groups where one solution carries several source labels (e.g. Stepwise annotated by several teachers): 123. Each such case keeps its own positive; they share a group, so they never serve as each other's negative.

## 4. Split

Question-group split {'train': 0.8, 'validation': 0.1, 'test': 0.1}, stratified by dataset | benchmark | normalized source label of the group's most frequent case. Groups containing a question from the 40 prompt-development (dev) cases are forced into train: 37 groups. The earlier 160 holdout cases were not viewed or used for prompt changes, so they are treated as unused.

| dataset | cases | train | validation | test | groups |
| --- | --- | --- | --- | --- | --- |
| eic | 1677 | 1339 (79.8%) | 167 (10.0%) | 171 (10.2%) | 1307 |
| mathclean | 470 | 378 (80.4%) | 46 (9.8%) | 46 (9.8%) | 470 |
| mathedu | 866 | 696 (80.4%) | 85 (9.8%) | 85 (9.8%) | 865 |
| stepwise | 689 | 556 (80.7%) | 63 (9.1%) | 70 (10.2%) | 535 |
| total | 3702 | 2969 (80.2%) | 361 (9.8%) | 372 (10.0%) | 3114 |

Cases per source label and split:

| dataset | source label | cases | train | validation | test | note |
| --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 200 | 159 | 19 | 22 |  |
| eic | calculation_error | 216 | 175 | 21 | 20 |  |
| eic | confusing_formula_error | 189 | 147 | 21 | 21 |  |
| eic | counting_error | 154 | 123 | 13 | 18 |  |
| eic | missing_step | 173 | 141 | 18 | 14 |  |
| eic | operator_error | 196 | 159 | 19 | 18 |  |
| eic | referencing_context_value_error | 201 | 159 | 20 | 22 |  |
| eic | referencing_previous_step_value_error | 178 | 141 | 17 | 20 |  |
| eic | unit_conversion_error | 170 | 135 | 19 | 16 |  |
| mathclean | computing error | 193 | 155 | 19 | 19 |  |
| mathclean | expression error | 21 | 17 | 2 | 2 | sparse |
| mathclean | logic error | 256 | 206 | 25 | 25 |  |
| mathedu | Algebraic error | 41 | 33 | 4 | 4 |  |
| mathedu | Arithmetical error | 69 | 55 | 7 | 7 |  |
| mathedu | Careless error | 28 | 22 | 3 | 3 |  |
| mathedu | Comprehension error | 162 | 130 | 16 | 16 |  |
| mathedu | Lack of necessary mathematical concepts | 14 | 12 | 1 | 1 | sparse |
| mathedu | Measurement error | 11 | 9 | 1 | 1 | sparse |
| mathedu | Unfinished answer | 109 | 89 | 10 | 10 |  |
| mathedu | Wrong mathematical operation/concept | 432 | 346 | 43 | 43 |  |
| stepwise | Calculation error easily solved by a calculator | 95 | 74 | 10 | 11 |  |
| stepwise | Extra quantity or Missing quantity | 174 | 141 | 15 | 18 |  |
| stepwise | Missing / Wrong factual knowledge | 126 | 102 | 10 | 14 |  |
| stepwise | Misunderstanding of a question | 217 | 176 | 20 | 21 |  |
| stepwise | Reached correct solution but proceeded further | 52 | 42 | 6 | 4 |  |
| stepwise | Unit conversion error | 25 | 21 | 2 | 2 | sparse |

`sparse` = fewer than 3 cases in validation or test; per-label results there are not reliable.

## 5. Negatives

| split | anchors | kept pairs | no candidate | over length | pair records (2 per anchor) |
| --- | --- | --- | --- | --- | --- |
| train | 2969 | 2969 | 0 | 0 | 5938 |
| validation | 361 | 361 | 0 | 0 | 722 |
| test | 372 | 372 | 0 | 0 | 744 |

- distinct donors: 2313; most reuse of one donor: 7
- negatives whose description text equals the anchor's own description: 0 (kept: no similarity-based exclusion by design)

**eic**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 adding_irrelevant_information |  | 23 | 28 | 24 | 24 | 24 | 42 | 17 | 18 |
| L2 calculation_error | 30 |  | 27 | 17 | 31 | 33 | 32 | 28 | 18 |
| L3 confusing_formula_error | 28 | 25 |  | 17 | 27 | 19 | 24 | 28 | 21 |
| L4 counting_error | 19 | 19 | 28 |  | 23 | 16 | 17 | 17 | 15 |
| L5 missing_step | 25 | 30 | 31 | 19 |  | 19 | 17 | 18 | 14 |
| L6 operator_error | 21 | 35 | 36 | 18 | 26 |  | 23 | 16 | 21 |
| L7 referencing_context_value_error | 24 | 35 | 32 | 29 | 21 | 20 |  | 25 | 15 |
| L8 referencing_previous_step_value_error | 18 | 21 | 29 | 24 | 23 | 21 | 27 |  | 15 |
| L9 unit_conversion_error | 13 | 27 | 18 | 20 | 17 | 28 | 25 | 22 |  |

**mathclean**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 |
| --- | --- | --- | --- |
| L1 computing error |  | 14 | 179 |
| L2 expression error | 6 |  | 15 |
| L3 logic error | 234 | 22 |  |

**mathedu**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 Algebraic error |  | 3 | 1 | 12 |  | 1 | 5 | 19 |
| L2 Arithmetical error | 4 |  | 3 | 11 | 1 | 2 | 7 | 41 |
| L3 Careless error | 1 | 3 |  | 6 |  |  | 7 | 11 |
| L4 Comprehension error | 13 | 12 | 7 |  | 4 | 5 | 27 | 94 |
| L5 Lack of necessary mathematical concepts |  | 2 | 1 | 2 |  |  | 2 | 7 |
| L6 Measurement error | 1 |  |  | 1 |  |  | 1 | 8 |
| L7 Unfinished answer | 10 | 12 | 1 | 25 | 3 | 2 |  | 56 |
| L8 Wrong mathematical operation/concept | 63 | 83 | 27 | 135 | 7 | 10 | 107 |  |

**stepwise**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 |
| --- | --- | --- | --- | --- | --- | --- |
| L1 Calculation error easily solved by a calculator |  | 27 | 21 | 37 | 9 | 1 |
| L2 Extra quantity or Missing quantity | 27 |  | 40 | 78 | 20 | 9 |
| L3 Missing / Wrong factual knowledge | 15 | 33 |  | 58 | 15 | 5 |
| L4 Misunderstanding of a question | 51 | 79 | 56 |  | 21 | 10 |
| L5 Reached correct solution but proceeded further | 7 | 19 | 6 | 18 |  | 2 |
| L6 Unit conversion error | 6 | 3 | 4 | 7 | 5 |  |

## 6. Length

Tokenizer `Qwen/Qwen2.5-Math-7B-Instruct`; counts include the chat template, system prompt and assistant label. Limit 4096 (the model's max_position_embeddings).

| split | min | median | p99 | max |
| --- | --- | --- | --- | --- |
| train | 198 | 331 | 1483 | 2665 |
| validation | 196 | 335 | 1285 | 2582 |
| test | 190 | 328 | 1228 | 1564 |

Pairs dropped for length: 0.

## 7. Checks

| check | result | detail |
| --- | --- | --- |
| each question group lies in one split | pass | 0 groups in several splits |
| negative donor from the same split | pass |  |
| negative donor from the same dataset | pass |  |
| negative donor label differs (normalized) | pass |  |
| negative donor from a different question group | pass |  |
| positive donor is the anchor itself | pass |  |
| every kept anchor has one positive and one negative | pass |  |
| all anchors and donors have description status ok | pass |  |
| no empty question / solution / description | pass |  |
| no prompt-development (dev 40) question group in test | pass | 0 cases |
| no pair over 4096 tokens | pass | 0 pairs |

