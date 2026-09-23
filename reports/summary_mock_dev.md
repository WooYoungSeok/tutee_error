# Run summary — mock_dev

- model: `mock-model`  (MOCK RUN)
- prompt: `prompts/error_description_v1.txt` version v1 sha256 `1b3c182347176be6`
- split: dev · cases: 30
- finished (UTC): 2026-09-21T05:31:46Z

## Processing status (request level)

| processing_status | count |
| --- | --- |
| ok | 30 |

## Model status by dataset (data level)

| dataset | cases | ok | ambiguous | label_conflict | (none) |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 10 | 0 | 0 | 0 |
| mathclean | 10 | 10 | 0 | 0 | 0 |
| stepwise | 10 | 10 | 0 | 0 | 0 |

## Description length (words)

| dataset | n with description | min | median | max | outside 5-15 |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 6 | 6 | 6 | 0 |
| mathclean | 10 | 6 | 6 | 6 | 0 |
| stepwise | 10 | 6 | 6 | 6 | 0 |

## Repeated descriptions

1 description(s) appear more than once (30 cases). Reuse across questions is expected, not an automatic failure.

| description (normalized) | count |
| --- | --- |
| mock description of the exemplified error | 30 |

## Automated review flags

| flag | cases |
| --- | --- |
| null description | 0 |
| outside 5-15 words | 0 |
| contains a digit | 0 |
| shares an uncommon token with the question | 0 |
| evidence_quote not found verbatim | 30 |

These flags mark rows worth a look. They are not correctness judgements, and no stored response was edited to satisfy them.

## Tokens and errors

- token usage totals: {'input_tokens': 21046, 'output_tokens': 1200, 'total_tokens': 22246}
- failed requests: 0 (non-ok processing statuses)
- cost: not computed here. Multiply the token totals by the price you confirmed for this model; reasoning tokens, if any, are billed as output tokens.

## Review criteria (fill in the review columns)

1. error preserved — does C point at the error in R and A?
2. context removed — would C still apply with different story, values and step order?
3. not over-general — is C more than a statement that fits almost any wrong answer?

Also note unsupported claims about missing knowledge, and disagreements with the source annotations.
