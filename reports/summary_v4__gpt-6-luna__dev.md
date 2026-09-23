# Run summary — v4__gpt-6-luna__dev

- model: `gpt-6-luna`
- prompt: `prompts/error_description_v4.txt` version v4 sha256 `28ef5467bbbac5ce`
- split: dev · cases: 40
- finished (UTC): 2026-09-23T10:09:04Z

## Processing status (request level)

| processing_status | count |
| --- | --- |
| json_parse_error | 1 |
| ok | 39 |

## Model status by dataset (data level)

| dataset | cases | ok | ambiguous | label_conflict | (none) |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 10 | 0 | 0 | 0 |
| mathclean | 10 | 6 | 0 | 3 | 1 |
| mathedu | 10 | 10 | 0 | 0 | 0 |
| stepwise | 10 | 8 | 0 | 2 | 0 |

## Description length (words)

| dataset | n with description | min | median | max | outside 5-15 |
| --- | --- | --- | --- | --- | --- |
| eic | 10 | 4 | 8 | 10 | 2 |
| mathclean | 6 | 6 | 9 | 10 | 0 |
| mathedu | 10 | 6 | 9 | 11 | 0 |
| stepwise | 10 | 7 | 9 | 12 | 0 |

## Repeated descriptions

Every description is distinct.

## Automated review flags

| flag | cases |
| --- | --- |
| null description | 4 |
| outside 5-15 words | 2 |
| contains a digit | 0 |
| shares an uncommon token with the question | 10 |
| evidence_quote not found verbatim | 4 |

These flags mark rows worth a look. They are not correctness judgements, and no stored response was edited to satisfy them.

## Tokens and errors

- token usage totals: {'input_tokens': 33388, 'output_tokens': 10278, 'total_tokens': 43666}
- failed requests: 1 (non-ok processing statuses)
- cost: not computed here. Multiply the token totals by the price you confirmed for this model; reasoning tokens, if any, are billed as output tokens.

## Review criteria (fill in the review columns)

1. error preserved — does C point at the error in R and A?
2. context removed — would C still apply with different story, values and step order?
3. not over-general — is C more than a statement that fits almost any wrong answer?

Also note unsupported claims about missing knowledge, and disagreements with the source annotations.
