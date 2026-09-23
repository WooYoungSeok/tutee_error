# Data inspection report

Generated (UTC): 2026-09-21T09:16:35Z  
Seed: 42 · per-dataset target: 50 · dev per dataset: 10

## 1. Sources and provenance

| dataset | status | source | revision | files | bytes |
| --- | --- | --- | --- | --- | --- |
| mathedu | ok | NYCU-NLP-Lab/MathEDU | acb1873f1569 | 22 | 15175794 |
| stepwise | ok | eth-lre/verify-then-generate | 161019e6cc29 | 1 | 2641752 |
| mathclean | ok | MeiyiQiang/MathClean | 27e7028b3119 | 8 | 7413285 |
| eic | ok | LittleCirc1e/EIC | be8132a826dd | 34 | 4265978 |

Per-file URLs, byte sizes and SHA-256 digests: `data/raw/source_manifest.json`.

## 2. Normalized records, eligibility and exclusions

| dataset | records read | eligible | unique question groups | unique sample ids |
| --- | --- | --- | --- | --- |
| mathedu | 4048 | 890 | 888 | 888 |
| stepwise | 1002 | 915 | 583 | 766 |
| mathclean | 610 | 610 | 610 | 610 |
| eic | 1300 | 898 | 701 | 828 |

**mathedu exclusions**

| reason | count |
| --- | --- |
| missing_field:incorrect_solution | 82 |
| multiple_annotated_errors:2 | 23 |
| multiple_annotated_errors:3 | 3 |
| not_an_incorrect_answer:correct | 3050 |

**stepwise exclusions**

| reason | count |
| --- | --- |
| non_error_label | 87 |

**eic exclusions**

| reason | count |
| --- | --- |
| label_outside_canonical_set:calculation_error_fixed_addition | 1 |
| label_outside_canonical_set:referencing_value | 1 |
| non_error_type_directory:wrong_step_calculation_error | 400 |

## 3. Original error label frequencies (eligible pool)

**mathedu** (pool 890)

| original label | pool | planned | selected |
| --- | --- | --- | --- |
| Wrong mathematical operation/concept | 437 | 7 | 7 |
| Comprehension error | 169 | 7 | 7 |
| Unfinished answer | 116 | 6 | 6 |
| Arithmetical error | 73 | 6 | 6 |
| Algebraic error | 41 | 6 | 6 |
| Careless error | 28 | 6 | 6 |
| Lack of necessary mathematical concepts | 14 | 6 | 6 |
| Measurement error | 12 | 6 | 6 |


**stepwise** (pool 915)

| original label | pool | planned | selected |
| --- | --- | --- | --- |
| Misunderstanding of a question | 287 | 9 | 9 |
| Extra quantity or Missing quantity | 240 | 9 | 9 |
| Missing / Wrong factual knowledge | 140 | 8 | 8 |
| Calculation error easily solved by a calculator | 128 | 8 | 8 |
| Reached correct solution but proceeded further | 70 | 8 | 8 |
| Unit conversion error | 50 | 8 | 8 |


**mathclean** (pool 610)

| original label | pool | planned | selected |
| --- | --- | --- | --- |
| logic error | 314 | 17 | 17 |
| computing error | 232 | 17 | 17 |
| expression error | 64 | 16 | 16 |


**eic** (pool 898)

| original label | pool | planned | selected |
| --- | --- | --- | --- |
| calculation_error | 102 | 6 | 6 |
| adding_irrelevant_information | 100 | 6 | 6 |
| confusing_formula_error | 100 | 6 | 6 |
| counting_error | 100 | 6 | 6 |
| operator_error | 100 | 6 | 6 |
| unit_conversion_error | 100 | 5 | 5 |
| referencing_context_value_error | 99 | 5 | 5 |
| referencing_previous_step_value_error | 99 | 5 | 5 |
| missing_step | 98 | 5 | 5 |


## 4. Duplicates across datasets

| dataset pair | shared question groups |
| --- | --- |
| stepwise|eic | 52 |

Shared groups are sampled at most once: the dataset processed first (config order: mathedu, stepwise, mathclean, eic) keeps the case.

## 5. Fixed sample

| dataset | selected | dev | holdout | question groups |
| --- | --- | --- | --- | --- |
| mathedu | 50 | 10 | 40 | 50 |
| stepwise | 50 | 10 | 40 | 50 |
| mathclean | 50 | 10 | 40 | 50 |
| eic | 50 | 10 | 40 | 50 |
| total | 200 | 40 | 160 | 200 |

### Metadata distribution of the sample

**mathedu**

- mathedu_split_file — test: 8, train: 36, val: 6
- mathqa_category — gain: 7, general: 18, geometry: 2, other: 3, physics: 20
- student_id — 1: 7, 2: 7, 3: 10, 4: 9, 5: 10, 6: 7

**stepwise**

- error_description present — False: 20, True: 30

**mathclean**

- difficulty_file — challenging: 26, simple: 24
- extent — not obvious error: 27, obvious error: 23
- subset — check_type_answer: 50

**eic**

- source_benchmark — GSM8K: 50
- type_dir — adding_irrelevant_information: 6, calculation_error: 6, confusing_formula_error: 6, counting_error: 6, missing_step: 5, operator_error: 6, referencing_context_value_error: 5, referencing_previous_step_value_error: 5, unit_conversion_error: 5

## 6. Notes

- Sample ids are `dataset:sha256(question, solution, label)[:16]`; `source_id` points at the original file and record index.
- The sample manifest is fixed: it must not be rebuilt when the prompt changes.
- MathEDU is real student work; Stepwise, MathClean and EIC contain model-generated solutions.
