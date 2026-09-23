# Run summary — v4__gpt-5.6-luna__full

- model: `gpt-5.6-luna`
- prompt: `prompts/error_description_v4.txt` version v4 sha256 `28ef5467bbbac5ce`
- split: full · cases: 3986
- finished (UTC): 2026-09-23T12:03:57Z

## Processing status (request level)

| processing_status | count |
| --- | --- |
| ok | 3986 |

## Model status by dataset (data level)

| dataset | cases | ok | ambiguous | label_conflict | (none) |
| --- | --- | --- | --- | --- | --- |
| eic | 1722 | 1684 | 0 | 38 | 0 |
| mathclean | 610 | 473 | 5 | 132 | 0 |
| mathedu | 888 | 866 | 1 | 21 | 0 |
| stepwise | 766 | 689 | 0 | 77 | 0 |

## Description length (words)

| dataset | n with description | min | median | max | outside 5-15 |
| --- | --- | --- | --- | --- | --- |
| eic | 1695 | 3 | 9 | 15 | 9 |
| mathclean | 475 | 4 | 9 | 16 | 3 |
| mathedu | 867 | 3 | 10 | 18 | 14 |
| stepwise | 724 | 2 | 10 | 16 | 5 |

## Repeated descriptions

119 description(s) appear more than once (363 cases). Reuse across questions is expected, not an automatic failure.

| description (normalized) | count |
| --- | --- |
| uses the perimeter formula instead of the area formula | 12 |
| uses an incorrect minutesperhour conversion | 11 |
| uses an incorrect minutestohours conversion factor | 9 |
| adds an unsupported extra quantity to the calculation | 8 |
| uses addition instead of multiplication to calculate rectangular area | 7 |
| uses an incorrect conversion factor when converting hours to minutes | 7 |
| uses an incorrect conversion factor when converting minutes to hours | 7 |
| uses an incorrect hourstominutes conversion factor | 7 |
| makes an arithmetic subtraction error | 6 |
| uses an incorrect conversion factor between hours and minutes | 6 |
| adds an unstated quantity to the total | 5 |
| adds an unsupported quantity to the total | 5 |
| introduces an unsupported extra quantity into the calculation | 5 |
| makes an arithmetic error when dividing distance by relative speed | 5 |
| makes an arithmetic error when subtracting quantities | 5 |
| uses an incorrect conversion factor between feet and inches | 5 |
| uses an incorrect number of minutes per hour | 5 |
| adds an irrelevant quantity to the requested total | 4 |
| adds an unprovided quantity to the total | 4 |
| adds an unsupported extra quantity to the total | 4 |
| calculates profit percentage using selling price instead of cost price | 4 |
| computes the final division incorrectly | 4 |
| makes an arithmetic error when isolating the variable | 4 |
| uses an incorrect conversion between hours and minutes | 4 |
| uses an incorrect number of minutes per hour in unit conversion | 4 |

## Automated review flags

| flag | cases |
| --- | --- |
| null description | 225 |
| outside 5-15 words | 31 |
| contains a digit | 44 |
| shares an uncommon token with the question | 1230 |
| evidence_quote not found verbatim | 346 |

These flags mark rows worth a look. They are not correctness judgements, and no stored response was edited to satisfy them.

## Tokens and errors

- token usage totals: {'input_tokens': 3196477, 'output_tokens': 772126, 'total_tokens': 3968603}
- failed requests: 0 (non-ok processing statuses)
- cost: not computed here. Multiply the token totals by the price you confirmed for this model; reasoning tokens, if any, are billed as output tokens.

## Review criteria (fill in the review columns)

1. error preserved — does C point at the error in R and A?
2. context removed — would C still apply with different story, values and step order?
3. not over-general — is C more than a statement that fits almost any wrong answer?

Also note unsupported claims about missing knowledge, and disagreements with the source annotations.
