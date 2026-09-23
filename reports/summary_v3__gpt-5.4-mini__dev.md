# Run summary — v3__gpt-5.4-mini__dev

- model: `gpt-5.4-mini`
- prompt: `prompts/error_description_v3.txt` version v3 sha256 `86e57f4075105fa3`
- split: dev · cases: 40
- finished (UTC): 2026-09-23T07:19:02Z

## Processing status (request level)

| processing_status | count |
| --- | --- |
| ok | 40 |

## Model status by dataset (data level)

| dataset | cases | ok | ambiguous | label_conflict | (none) |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 10 | 0 | 0 | 0 |
| mathclean | 10 | 9 | 0 | 1 | 0 |
| mathedu | 10 | 10 | 0 | 0 | 0 |
| stepwise | 10 | 10 | 0 | 0 | 0 |

## Description length (words)

| dataset | n with description | min | median | max | outside 5-15 |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 5 | 9 | 10 | 0 |
| mathclean | 10 | 5 | 9 | 16 | 1 |
| mathedu | 10 | 5 | 9 | 11 | 0 |
| stepwise | 10 | 5 | 10 | 13 | 0 |

## Repeated descriptions

1 description(s) appear more than once (3 cases). Reuse across questions is expected, not an automatic failure.

| description (normalized) | count |
| --- | --- |
| makes an arithmetic multiplication error | 3 |

## Automated review flags

| flag | cases |
| --- | --- |
| null description | 0 |
| outside 5-15 words | 1 |
| contains a digit | 0 |
| shares an uncommon token with the question | 12 |
| evidence_quote not found verbatim | 3 |

These flags mark rows worth a look. They are not correctness judgements, and no stored response was edited to satisfy them.

## Tokens and errors

- token usage totals: {'input_tokens': 40708, 'output_tokens': 2024, 'total_tokens': 42732}
- failed requests: 0 (non-ok processing statuses)
- cost: not computed here. Multiply the token totals by the price you confirmed for this model; reasoning tokens, if any, are billed as output tokens.

## Review criteria (fill in the review columns)

1. error preserved — does C point at the error in R and A?
2. context removed — would C still apply with different story, values and step order?
3. not over-general — is C more than a statement that fits almost any wrong answer?

Also note unsupported claims about missing knowledge, and disagreements with the source annotations.
