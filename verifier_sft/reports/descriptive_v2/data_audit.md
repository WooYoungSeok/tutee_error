# Data audit — descriptive_verifier_v2

Created (UTC): 2026-09-24T05:28:07Z · seed 42 · config sha256 `c91041c2b366a39c`

Targets are assigned automatically (own description = aligned, description from a case with a different source label = not_aligned). No semantic review of negatives was done; metrics on these pairs measure agreement with the automatic targets, not human-verified alignment.

## 1. Inputs

| input | path | sha256 |
| --- | --- | --- |
| pool | ../data/full/pool.jsonl | `7ee70b28469dac44` |
| descriptions | ../outputs/runs/v4__gpt-5.6-luna__full/parsed.jsonl | `bab3fe4e1dd0f854` |
| description_run_meta | ../outputs/runs/v4__gpt-5.6-luna__full/run_meta.json | `9054cf276d2fc0ed` |
| prompt_dev_manifest | ../data/manifest/sample_manifest.jsonl | `2f14aebb4473b284` |

Descriptions: model `gpt-5.6-luna`, prompt v4 (`28ef5467bbbac5ce`), run `v4__gpt-5.6-luna__full`.

## 2. Case selection

| dataset | cases | description_status:ambiguous | description_status:label_conflict | duplicate_record | missing_essential_information | multi_label_solution | eligible |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eic | 1722 | 0 | 38 | 7 | 0 | 4 | 1673 |
| mathclean | 610 | 5 | 132 | 0 | 3 | 0 | 470 |
| mathedu | 888 | 1 | 21 | 0 | 0 | 0 | 866 |
| stepwise | 766 | 0 | 77 | 0 | 0 | 289 | 400 |
| total | 3986 | 6 | 268 | 7 | 3 | 293 | 3409 |

Held out for missing essential information (found by keyword scan for figure/diagram/graph/table references without [asy] code, then read manually):

- `mathclean:3fa3a27b6b350aa5`: question refers to 'a more complex figure' that is not included
- `mathclean:5420672e35b7999b`: vertex labels B and G depend on a cube figure that is not included
- `mathclean:2018d169dd6fe205`: the sales graph the question refers to is not included

multi_label_solution: every case of a solution whose pool records carry more than one normalized source label (e.g. Stepwise annotated by several teachers) is dropped before splitting, so each kept solution has one label as in MathEdu. Solutions {'eic': 2, 'stepwise': 145}, their pool records {'eic': 4, 'stepwise': 328}, of which not already excluded for another reason {'eic': 4, 'stepwise': 289}.

Duplicate records removed: 7 (same dataset, question and solution after NFKC/lowercase/whitespace removal, same normalized label; the smallest sample_id is kept).

## 3. Question groups

- groups: 2992 (key: NFKC, lowercase, all whitespace and punctuation removed); the description pipeline's key (case and whitespace only) gives 3051
- cases per group: {1: 2684, 2: 219, 3: 71, 4: 16, 5: 2}
- groups spanning sources: {'eic-GSM8K + stepwise': 35, 'eic-MathQA + mathedu': 15}
- groups where one solution carries several source labels: 0 (multi-label solutions are excluded; see section 2)

## 4. Split

Question-group split {'train': 0.8, 'validation': 0.1, 'test': 0.1}, stratified by dataset | benchmark | normalized source label of the group's most frequent case. Groups containing a question from the 40 prompt-development (dev) cases are forced into train: 33 groups. The earlier 160 holdout cases were not viewed or used for prompt changes, so they are treated as unused.

| dataset | cases | train | validation | test | groups |
| --- | --- | --- | --- | --- | --- |
| eic | 1673 | 1331 (79.6%) | 171 (10.2%) | 171 (10.2%) | 1307 |
| mathclean | 470 | 378 (80.4%) | 46 (9.8%) | 46 (9.8%) | 470 |
| mathedu | 866 | 694 (80.1%) | 86 (9.9%) | 86 (9.9%) | 865 |
| stepwise | 400 | 321 (80.2%) | 38 (9.5%) | 41 (10.2%) | 400 |
| total | 3409 | 2724 (79.9%) | 341 (10.0%) | 344 (10.1%) | 2992 |

Cases per source label and split:

| dataset | source label | cases | train | validation | test | note |
| --- | --- | --- | --- | --- | --- | --- |
| eic | adding_irrelevant_information | 200 | 159 | 19 | 22 |  |
| eic | calculation_error | 215 | 174 | 21 | 20 |  |
| eic | confusing_formula_error | 189 | 147 | 21 | 21 |  |
| eic | counting_error | 154 | 124 | 12 | 18 |  |
| eic | missing_step | 173 | 138 | 20 | 15 |  |
| eic | operator_error | 196 | 160 | 19 | 17 |  |
| eic | referencing_context_value_error | 200 | 155 | 22 | 23 |  |
| eic | referencing_previous_step_value_error | 176 | 139 | 18 | 19 |  |
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
| mathedu | Unfinished answer | 109 | 88 | 10 | 11 |  |
| mathedu | Wrong mathematical operation/concept | 432 | 345 | 44 | 43 |  |
| stepwise | Calculation error easily solved by a calculator | 51 | 41 | 5 | 5 |  |
| stepwise | Extra quantity or Missing quantity | 102 | 83 | 9 | 10 |  |
| stepwise | Missing / Wrong factual knowledge | 71 | 56 | 7 | 8 |  |
| stepwise | Misunderstanding of a question | 126 | 101 | 12 | 13 |  |
| stepwise | Reached correct solution but proceeded further | 36 | 28 | 4 | 4 |  |
| stepwise | Unit conversion error | 14 | 12 | 1 | 1 | sparse |

`sparse` = fewer than 3 cases in validation or test; per-label results there are not reliable.

## 5. Negatives

| split | anchors | kept pairs | no candidate | over length | pair records (2 per anchor) |
| --- | --- | --- | --- | --- | --- |
| train | 2724 | 2724 | 0 | 0 | 5448 |
| validation | 341 | 341 | 0 | 0 | 682 |
| test | 344 | 344 | 0 | 0 | 688 |

- distinct donors: 2149; most reuse of one donor: 6
- negatives whose description text equals the anchor's own description: 0 (kept: no similarity-based exclusion by design)

**eic**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 adding_irrelevant_information |  | 27 | 21 | 24 | 22 | 28 | 33 | 22 | 23 |
| L2 calculation_error | 35 |  | 26 | 27 | 22 | 28 | 28 | 26 | 23 |
| L3 confusing_formula_error | 19 | 29 |  | 16 | 27 | 25 | 18 | 27 | 28 |
| L4 counting_error | 20 | 22 | 14 |  | 20 | 22 | 23 | 18 | 15 |
| L5 missing_step | 18 | 22 | 23 | 21 |  | 22 | 30 | 19 | 18 |
| L6 operator_error | 27 | 23 | 26 | 24 | 19 |  | 25 | 25 | 27 |
| L7 referencing_context_value_error | 33 | 24 | 34 | 13 | 31 | 21 |  | 19 | 25 |
| L8 referencing_previous_step_value_error | 17 | 27 | 22 | 18 | 25 | 26 | 20 |  | 21 |
| L9 unit_conversion_error | 25 | 20 | 24 | 16 | 20 | 26 | 18 | 21 |  |

**mathclean**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 |
| --- | --- | --- | --- |
| L1 computing error |  | 21 | 172 |
| L2 expression error | 10 |  | 11 |
| L3 logic error | 231 | 25 |  |

**mathedu**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 Algebraic error |  | 6 | 1 | 5 | 1 |  | 6 | 22 |
| L2 Arithmetical error | 1 |  | 4 | 12 | 1 | 1 | 9 | 41 |
| L3 Careless error | 3 | 1 |  | 5 | 1 |  | 8 | 10 |
| L4 Comprehension error | 6 | 11 | 11 |  | 4 | 4 | 22 | 104 |
| L5 Lack of necessary mathematical concepts |  |  | 2 | 4 |  |  | 1 | 7 |
| L6 Measurement error | 2 |  |  | 3 |  |  | 3 | 3 |
| L7 Unfinished answer | 5 | 12 | 8 | 19 | 3 | 1 |  | 61 |
| L8 Wrong mathematical operation/concept | 52 | 79 | 31 | 150 | 13 | 11 | 96 |  |

**stepwise**: anchor label (rows) × donor label (columns), all splits

| anchor \ donor | L1 | L2 | L3 | L4 | L5 | L6 |
| --- | --- | --- | --- | --- | --- | --- |
| L1 Calculation error easily solved by a calculator |  | 15 | 14 | 16 | 6 |  |
| L2 Extra quantity or Missing quantity | 11 |  | 31 | 39 | 16 | 5 |
| L3 Missing / Wrong factual knowledge | 20 | 19 |  | 22 | 8 | 2 |
| L4 Misunderstanding of a question | 22 | 39 | 33 |  | 22 | 10 |
| L5 Reached correct solution but proceeded further | 6 | 6 | 11 | 12 |  | 1 |
| L6 Unit conversion error | 2 | 4 | 3 | 4 | 1 |  |

## 6. Length

Tokenizer `Qwen/Qwen2.5-Math-7B-Instruct`; counts include the chat template, system prompt and assistant label. Limit 4096 (the model's max_position_embeddings).

| split | min | median | p99 | max |
| --- | --- | --- | --- | --- |
| train | 198 | 326 | 1512 | 2666 |
| validation | 194 | 328 | 1444 | 2582 |
| test | 190 | 324 | 1396 | 1566 |

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

