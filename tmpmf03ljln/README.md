---
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: transformers
tags: [grpo, error-generation, eedi, misconception]
---
# Eedi Student with a distractor reward (student_likeness GRPO), epoch-2.0 (best)

Student(Q, misconception description C) -> a solution showing C, trained with GRPO from `Qwen/Qwen2.5-7B-Instruct`
on the Eedi train split (2,048 pairs; tutee_error `distractor_rl/`, first version).

- Run `distractor_student_likeness_seed42_20261003_011448`, 2 epochs / 682 steps; best snapshot chosen on test
  (mean test reward with verifier B), so the test score is optimistic.
- Reward: gpt-5-nano (reasoning low) Eedi answer judge; correct / unjudgeable -0.75; incorrect and equal to the
  condition's target distractor (literal match or a second gpt-5-nano check) +1; other incorrect + reward verifier
  (`WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2-trval-halfA`, n=2, T=0.6, both aligned) +0.5, else 0;
  + 0.5 x pairwise student-likeness inside G = {main > 0}; truncation -0.5.
- Input format: system = `rl/prompts/student.txt` with the misconception description; user = the problem (options hidden).
- Sampling used in training (generation_config.json): T 1.0, top_p 1.0, top_k off, repetition 1.0, 1,024 tokens.

Test (481 pairs x 8 rollouts). B = `WooYoungSeok/deepseek-r1-0528-qwen3-8b-descriptive-verifier-v2-trval-halfB`;
sol = gpt-5.6-sol with the same verifier messages; success = incorrect and the verifier says aligned twice.

| model | mean reward | correct rate | B success | gpt-5.6-sol success | distractor match (all / among incorrect) |
|---|---|---|---|---|---|
| base | -0.032 | 0.583 | 0.408 | 0.327 | 0.204 / 0.490 |
| epoch-2.0 | 0.646 | 0.193 | 0.800 | 0.651 | 0.384 / 0.477 |

Verifier B accepts 98–99% of incorrect answers; the gain comes mostly from fewer correct answers, while the
distractor match rate among incorrect answers did not rise. Details: `rl/EXPERIMENTS.md` D3, D4, D7.
