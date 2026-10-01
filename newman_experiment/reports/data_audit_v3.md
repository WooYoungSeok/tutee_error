# Newman data audit (sft)

Created 2026-10-01T14:25:58+09:00 (Asia/Seoul) · seed 42 · git `7c7c02879b73` · mapping verified: **True**

Targets of the SFT pairs are automatic (own type = aligned, another type of the same source dataset = not_aligned); negatives are not semantically reviewed (plan 5.4).

## 1. Inputs

| input | path | sha256 |
| --- | --- | --- |
| pool | data/full/pool.jsonl | `7ee70b28469dac44` |
| descriptions | outputs/runs/v4__gpt-5.6-luna__full/parsed.jsonl | `bab3fe4e1dd0f854` |
| gsm8k_train | newman_experiment/data/raw/gsm8k/train.parquet | `ea82612ea9582142` |
| gsm8k_test | newman_experiment/data/raw/gsm8k/test.parquet | `ee7b8da9e381df27` |
| unit_allowlist | newman_experiment/data/unit_conversion_allowlist_gsm8k.json | `15eea4c537da6498` |
| taxonomy | newman_experiment/configs/taxonomy.yaml | `9b7cc796466492a7` |
| mapping_workbook | data/raw/Newman_relabeling_영석_마무리 (1).xlsx | `9324bac2d5112d3b` |

## 2. Newman mapping (workbook column D)

| dataset | name (column A) | type id | row | column D | applied | definition (column B) |
| --- | --- | --- | --- | --- | --- | --- |
| eic | adding irrelevant information | eic.adding_irrelevant_information | 21 | Reading | reading | yes |
| eic | Calculation Error | eic.calculation_error | 13 | Process Skills | process_skills | yes |
| eic | confusing formula error | eic.confusing_formula_error | 20 | Transformation | transformation | yes |
| eic | Counting Error | eic.counting_error | 14 | 제외 - 100 | excluded | - |
| eic | Missing Step | eic.missing_step | 19 | 제외 - 100*2 | excluded | - |
| eic | Operator Error | eic.operator_error | 18 | Transformation | transformation | yes |
| eic | referencing context value error | eic.referencing_context_value_error | 15 | Reading | reading | yes |
| eic | referencing previous step value error | eic.referencing_previous_step_value_error | 16 | Process Skills | process_skills | yes |
| eic | Unit Conversion Error | eic.unit_conversion_error | 17 | Transformation | transformation | yes |
| mathclean | Computing error | mathclean.computing_error | 12 | Process Skills | process_skills | yes |
| mathclean | Expression error | mathclean.expression_error | 10 | 제외(200) | excluded | - |
| mathclean | Logic error | mathclean.logic_error | 11 | Transformation | transformation | yes |
| mathedu | Algebraic error | mathedu.algebraic_error | 7 | Process Skills | process_skills | yes |
| mathedu | Arithmetical error | mathedu.arithmetical_error | 6 | Process Skills | process_skills | yes |
| mathedu | Careless Error | mathedu.careless_error | 8 | 제외(20) | excluded | - |
| mathedu | Comprehension error | mathedu.comprehension_error | 3 | Comprehension | comprehension | yes |
| mathedu | Lack of Necessary Mathematical Concepts | mathedu.lack_of_necessary_mathematical_concepts | 5 | 제외(57) - 빈칸이라서 | excluded | - |
| mathedu | Measurement error | mathedu.measurement_error | 9 | Transformation(9) | transformation | yes |
| mathedu | Unfinished answer | mathedu.unfinished_answer | 4 | 제외(85) | excluded | - |
| mathedu | Wrong Mathematical Operation/Concept | mathedu.wrong_mathematical_operation_concept | 2 | Transformation | transformation | yes |
| stepwise | Calculation error easily solved by a calculator | stepwise.calculation_error_easily_solved_by_a_calculator | 22 | Process Skills | process_skills | (none) |
| stepwise | Extra quantity or Missing quantity | stepwise.extra_quantity_or_missing_quantity | 23 | 제외 - 100*2 | excluded | - |
| stepwise | Missing / Wrong factual knowledge | stepwise.missing_or_wrong_factual_knowledge | 24 | 제외 - 100*2 | excluded | - |
| stepwise | Misunderstanding of a question | stepwise.misunderstanding_of_a_question | 25 | Comprehension | comprehension | (none) |
| stepwise | Reached correct solution but proceeded further | stepwise.reached_correct_solution_but_proceeded_further | 26 | 제외 - 100*2 | excluded | - |
| stepwise | Unit conversion error | stepwise.unit_conversion_error | 27 | 제외 - 100*2 | excluded | - |

## 3. Case selection (pool records)

| dataset | description_status:ambiguous | description_status:label_conflict | duplicate_record | eligible | missing_essential_information | multi_label_solution | newman_excluded_type:eic.counting_error | newman_excluded_type:eic.missing_step | newman_excluded_type:mathclean.expression_error | newman_excluded_type:mathedu.careless_error | newman_excluded_type:mathedu.lack_of_necessary_mathematical_concepts | newman_excluded_type:mathedu.unfinished_answer | newman_excluded_type:stepwise.extra_quantity_or_missing_quantity | newman_excluded_type:stepwise.missing_or_wrong_factual_knowledge | newman_excluded_type:stepwise.reached_correct_solution_but_proceeded_further | newman_excluded_type:stepwise.unit_conversion_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eic |  | 38 | 7 | 1346 |  | 4 | 154 | 173 |  |  |  |  |  |  |  |  |
| mathclean | 5 | 132 |  | 449 | 3 |  |  |  | 21 |  |  |  |  |  |  |  |
| mathedu | 1 | 21 |  | 715 |  |  |  |  |  | 28 | 14 | 109 |  |  |  |  |
| stepwise |  | 77 |  | 162 |  | 315 |  |  |  |  |  |  | 100 | 64 | 35 | 13 |

Student solutions with more than one error label (pool or raw normalized records; user instruction 2026-09-30) are excluded: solutions {'eic': 2, 'stepwise': 173}, of which found only through raw labels outside the pool {'stepwise': 28}; their records {'eic': 4, 'stepwise': 356}.

Eligible cases per adopted type (a count of solutions, not of the 16 types):

| dataset | type | stage | cases |
| --- | --- | --- | --- |
| eic | eic.adding_irrelevant_information | reading | 200 |
| eic | eic.calculation_error | process_skills | 215 |
| eic | eic.confusing_formula_error | transformation | 189 |
| eic | eic.operator_error | transformation | 196 |
| eic | eic.referencing_context_value_error | reading | 200 |
| eic | eic.referencing_previous_step_value_error | process_skills | 176 |
| eic | eic.unit_conversion_error | transformation | 170 |
| mathclean | mathclean.computing_error | process_skills | 193 |
| mathclean | mathclean.logic_error | transformation | 256 |
| mathedu | mathedu.algebraic_error | process_skills | 41 |
| mathedu | mathedu.arithmetical_error | process_skills | 69 |
| mathedu | mathedu.comprehension_error | comprehension | 162 |
| mathedu | mathedu.measurement_error | transformation | 11 |
| mathedu | mathedu.wrong_mathematical_operation_concept | transformation | 432 |
| stepwise | stepwise.calculation_error_easily_solved_by_a_calculator | process_skills | 46 |
| stepwise | stepwise.misunderstanding_of_a_question | comprehension | 116 |

## 4. Unit-conversion eligibility (plan 5.5, 5.7)

GSM8K allowlist `newman_experiment/data/unit_conversion_allowlist_gsm8k.json` (sha256 `15eea4c537da6498`): unique rows {'train': 845, 'test': 203}; extra lists none; conflicts 0.

Content check against the pinned parquet (unit words of each group, by index offset):

| split/group | n | correction | peak | hit rate | by offset |
| --- | --- | --- | --- | --- | --- |
| train/시간단위 | 662 | -2 | -2 | 1.00 | -4:0.39 -3:0.39 -2:1.00 -1:0.38 +0:0.41 +1:0.42 +2:0.39 |
| train/길이단위 | 45 | -2 | -2 | 1.00 | -4:0.13 -3:0.11 -2:1.00 -1:0.09 +0:0.09 +1:0.13 +2:0.02 |
| train/화폐단위 | 53 | -2 | -2 | 1.00 | -4:0.36 -3:0.40 -2:1.00 -1:0.40 +0:0.34 +1:0.23 +2:0.30 |
| train/거리단위 | 40 | +0 | +0 | 1.00 | -4:0.17 -3:0.15 -2:0.12 -1:0.15 +0:1.00 +1:0.07 +2:0.07 |
| train/무게/부피 | 68 | +0 | +0 | 1.00 | -4:0.10 -3:0.07 -2:0.10 -1:0.03 +0:1.00 +1:0.06 +2:0.06 |
| train/묶음단위 | 25 | +0 | +0 | 0.96 | -4:0.12 -3:0.08 -2:0.24 -1:0.04 +0:0.96 +1:0.08 +2:0.24 |
| test/시간단위 | 123 | -2 | -2 | 1.00 | -4:0.35 -3:0.42 -2:1.00 -1:0.43 +0:0.40 +1:0.48 +2:0.38 |
| test/길이단위 | 11 | -2 | -2 | 1.00 | -4:0.00 -3:0.09 -2:1.00 -1:0.09 +0:0.09 +1:0.18 +2:0.00 |
| test/화폐단위 | 6 | -2 | -2 | 1.00 | -4:0.17 -3:0.17 -2:1.00 -1:0.33 +0:0.50 +1:0.17 +2:0.50 |
| test/거리단위 | 12 | +0 | +0 | 1.00 | -4:0.00 -3:0.00 -2:0.00 -1:0.08 +0:1.00 +1:0.08 +2:0.08 |
| test/무게/부피 | 47 | +0 | +0 | 1.00 | -4:0.04 -3:0.19 -2:0.17 -1:0.04 +0:1.00 +1:0.06 +2:0.09 |
| test/묶음단위 | 20 | +0 | +0 | 0.80 | -4:0.15 -3:0.10 -2:0.10 -1:0.20 +0:0.80 +1:0.00 +2:0.15 |

SFT cases by eligibility (None = no confirmed allowlist: the unit-related types are never their negatives):

| dataset | benchmark | True | False | None |
| --- | --- | --- | --- | --- |
| eic | GSM8K | 137 | 506 | 13 |
| eic | MathQA | 0 | 0 | 690 |
| mathclean | - | 0 | 0 | 449 |
| mathedu | - | 0 | 0 | 715 |
| stepwise | - | 24 | 138 | 0 |

## 5. Global question groups and split (train:test = 80:20, halves 50:50)

| groups | split | half | count |
| --- | --- | --- | --- |
| gsm8k_only | test | - | 1613 |
| gsm8k_only | train | - | 6466 |
| sft | test | - | 474 |
| sft | train | A | 963 |
| sft | train | B | 961 |

SFT cases per region:

| dataset | benchmark | half_a | half_b | test |
| --- | --- | --- | --- | --- |
| eic | GSM8K | 259 | 264 | 133 |
| eic | MathQA | 288 | 271 | 131 |
| mathclean | - | 180 | 180 | 89 |
| mathedu | - | 289 | 282 | 144 |
| stepwise | - | 65 | 66 | 31 |

GSM8K rows by original split and global split: {('test', 'test'): 260, ('test', 'train'): 1059, ('train', 'test'): 1492, ('train', 'train'): 5981}.

Forced into train: 34 groups; into half A: 2.

## 6. SFT pairs and negatives (plan 5.4)

Negative type: uniform over the candidate scope `same_dataset` except the anchor's own type; unit-related types only on allowlisted questions, where they have priority unless the anchor's own type is unit-related.

Second negative per anchor (`::neg_cross`): uniform over the types of another source dataset at another Newman stage, with the same unit rules and priority; separate RNG, so the first negatives equal the one-negative version.

Draws with unit priority: half_a 27, half_b 25, test 10.

Second-negative draws with unit priority: half_a 26, half_b 19, test 12.

| region | anchors | paired | no candidate | same-stage neg | different-stage neg | same-dataset neg | other-dataset neg | pair rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| half_a | 1081 | 1081 | 0 | 146 | 2016 | 1081 | 1081 | 3243 |
| half_b | 1063 | 1063 | 0 | 158 | 1968 | 1063 | 1063 | 3189 |
| test | 528 | 528 | 0 | 55 | 1001 | 528 | 528 | 1584 |

Positives / negatives carrying the type, per region:

| type | half_a | half_b | test |
| --- | --- | --- | --- |
| eic.adding_irrelevant_information | 80 / 162 | 75 / 164 | 45 / 81 |
| eic.calculation_error | 86 / 133 | 87 / 124 | 42 / 76 |
| eic.confusing_formula_error | 70 / 114 | 83 / 113 | 36 / 61 |
| eic.operator_error | 82 / 113 | 76 / 117 | 38 / 58 |
| eic.referencing_context_value_error | 88 / 142 | 76 / 140 | 36 / 73 |
| eic.referencing_previous_step_value_error | 68 / 147 | 73 / 146 | 35 / 68 |
| eic.unit_conversion_error | 73 / 34 (unit removed 688) | 65 / 30 (unit removed 689) | 32 / 13 (unit removed 340) |
| mathclean.computing_error | 78 / 186 | 77 / 196 | 38 / 94 |
| mathclean.logic_error | 102 / 156 | 103 / 153 | 51 / 69 |
| mathedu.algebraic_error | 16 / 164 | 16 / 148 | 9 / 89 |
| mathedu.arithmetical_error | 28 / 181 | 27 / 174 | 14 / 75 |
| mathedu.comprehension_error | 66 / 183 | 64 / 196 | 32 / 83 |
| mathedu.measurement_error | 5 / 19 (unit removed 723) | 4 / 14 (unit removed 713) | 2 / 9 (unit removed 357) |
| mathedu.wrong_mathematical_operation_concept | 174 / 119 | 171 / 116 | 87 / 55 |
| stepwise.calculation_error_easily_solved_by_a_calculator | 19 / 149 | 19 / 145 | 8 / 72 |
| stepwise.misunderstanding_of_a_question | 46 / 160 | 47 / 150 | 23 / 80 |

## 7. Length

| half | tokenizer | regions | pairs | min | median | p99 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Qwen/Qwen2.5-Math-7B-Instruct | half_a, test | 4827 | 303 | 461 | 1712 | 2721 |
| B | deepseek-ai/DeepSeek-R1-0528-Qwen3-8B | half_b, test | 4773 | 336 | 488 | 1489 | 2641 |

Anchors dropped for length (> 4096): 0.

## 8. RL scenario sizes (reference; the decisions are in configs/data.yaml rl_data and data/prepared/rl/meta.json)

GSM8K source splits ['train'] (6 conditions per optimizer step at 48 completions):

| scenario | train_questions | train_conditions | test_questions | test_conditions | train_steps_per_epoch |
| --- | --- | --- | --- | --- | --- |
| balanced k=1 | 5981 | 5981 | 1492 | 1492 | 996 |
| balanced k=2 | 5981 | 11962 | 1492 | 2984 | 1993 |
| balanced k=4 | 5981 | 23924 | 1492 | 5968 | 3987 |
| all_types | 5981 | 85090 | 1492 | 21222 | 14181 |

GSM8K source splits ['train', 'test'] (6 conditions per optimizer step at 48 completions):

| scenario | train_questions | train_conditions | test_questions | test_conditions | train_steps_per_epoch |
| --- | --- | --- | --- | --- | --- |
| balanced k=1 | 7040 | 7040 | 1752 | 1752 | 1173 |
| balanced k=2 | 7040 | 14080 | 1752 | 3504 | 2346 |
| balanced k=4 | 7040 | 28160 | 1752 | 7008 | 4693 |
| all_types | 7040 | 100246 | 1752 | 24938 | 16707 |

## 9. Checks

| check | result | detail |
| --- | --- | --- |
| every question group has one split | pass |  |
| every SFT train group has one half | pass | 0 without |
| half A / half B / test share no question group | pass | 0 groups |
| positive target type = the anchor's own type | pass |  |
| negative type differs from the anchor type | pass |  |
| every pair's stage = mapping(its type) | pass |  |
| unit-related negatives only on allowlisted questions | pass |  |
| no excluded type in any pair | pass |  |
| every kept anchor has one positive and 2 negative(s) | pass |  |
| the first negative comes from the anchor's own dataset | pass |  |
| the second negative is another dataset and another Newman stage | pass |  |
| Q and S of a negative are the anchor's own | pass |  |
| forced-train groups (prompt dev, judge examples) not in test | pass | 0 |
| judge-example groups in half A | pass | 0 |
| no pair over 4096 tokens | pass | 0 |

