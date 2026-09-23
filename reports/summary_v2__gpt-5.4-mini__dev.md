# Run summary — v2__gpt-5.4-mini__dev

- model: `gpt-5.4-mini`
- prompt: `prompts/error_description_v2.txt` version v2 sha256 `15f304a7be10cace`
- split: dev · cases: 40
- finished (UTC): 2026-09-23T06:41:39Z

## Processing status (request level)

| processing_status | count |
| --- | --- |
| json_parse_error | 2 |
| ok | 38 |

## Model status by dataset (data level)

| dataset | cases | ok | ambiguous | label_conflict | (none) |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 10 | 0 | 0 | 0 |
| mathclean | 10 | 8 | 0 | 0 | 2 |
| mathedu | 10 | 9 | 0 | 1 | 0 |
| stepwise | 10 | 10 | 0 | 0 | 0 |

## Description length (words)

| dataset | n with description | min | median | max | outside 5-15 |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 5 | 9 | 14 | 0 |
| mathclean | 8 | 5 | 11 | 18 | 1 |
| mathedu | 9 | 5 | 9 | 12 | 0 |
| stepwise | 10 | 8 | 13 | 18 | 2 |

## Repeated descriptions

1 description(s) appear more than once (2 cases). Reuse across questions is expected, not an automatic failure.

| description (normalized) | count |
| --- | --- |
| makes an arithmetic multiplication error | 2 |

## Automated review flags

| flag | cases |
| --- | --- |
| null description | 3 |
| outside 5-15 words | 3 |
| contains a digit | 1 |
| shares an uncommon token with the question | 16 |
| evidence_quote not found verbatim | 3 |

These flags mark rows worth a look. They are not correctness judgements, and no stored response was edited to satisfy them.

## Tokens and errors

- token usage totals: {'input_tokens': 72908, 'output_tokens': 2146, 'total_tokens': 75054}
- failed requests: 2 (non-ok processing statuses)
- cost: not computed here. Multiply the token totals by the price you confirmed for this model; reasoning tokens, if any, are billed as output tokens.

## Review criteria (fill in the review columns)

1. error preserved — does C point at the error in R and A?
2. context removed — would C still apply with different story, values and step order?
3. not over-general — is C more than a statement that fits almost any wrong answer?

Also note unsupported claims about missing knowledge, and disagreements with the source annotations.
