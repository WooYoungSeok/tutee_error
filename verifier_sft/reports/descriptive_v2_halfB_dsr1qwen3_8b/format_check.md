# Format and loss-mask check

Tokenizer `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` · prompt sha256 system `8873b8bcb1a596d7` user `e1fb1b93fbe7bf8b` · examples checked: 4132 · failures: 0

Tokens that carry loss:

- `aligned`: ['aligned', '<｜end of sentence｜>']
- `not_aligned`: ['not', '_aligned', '<｜end of sentence｜>']

## Example (training text, negative pair)

`eic:0082d64e3149e5bb::neg` · donor `eic:319668986052435f` · 297 tokens, 3 with loss · loss tokens decode to `'not_aligned<｜end of sentence｜>'`

```text
<｜begin▁of▁sentence｜>You are a mathematical error verifier.
Given a mathematics question, an incorrect solution, and an error description,
determine whether the description accurately describes an error
actually present in the solution.

Respond with aligned if the description is supported by the solution
in the context of the question. Otherwise, respond with not_aligned.

The description may use different wording from the solution and does
not need to cover every error. However, all error claims in the
description must be supported. A shared mathematical topic or an error
that could occur in the question is not enough.

Output exactly one label: aligned or not_aligned.
Do not provide an explanation or any other text.<｜User｜>Question:
Sheila works 8 hours per day on Monday, Wednesday, and Friday, and 6 hours per day on Tuesday and Thursday. She does not work on Saturday and Sunday. She earns $396 per week. How much does she earn in dollars per hour?

Incorrect solution:
The total number of hours Sheila works in a week is 8 * 2 + 6 * 2 = 28 hours
She earns $396 per week
To find her hourly rate, divide her total earnings by the total number of hours worked: 396 / 28 = 14.14
#### 14.14

Error description:
Uses the original cost instead of calculating the fractional cost<｜Assistant｜>not_aligned<｜end▁of▁sentence｜>
```

