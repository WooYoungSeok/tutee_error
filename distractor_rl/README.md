# distractor_rl — Eedi GRPO with a verifiable distractor reward

Student(Q, misconception C) -> solution, as in `../rl`, with the main reward changed (user decisions 2026-10-02):
correct or unjudgeable -0.75; incorrect and equal to the condition's target distractor 1.0; other incorrect + reward
verifier 2/2 aligned 0.5; otherwise 0. Plus 0.5 x student-likeness inside G = {main > 0} and truncation -0.5.
Settings, smoke findings and results: `../rl/EXPERIMENTS.md` ("Distractor 보상 실험").

- `rl/` is not modified: `scripts/_patch.py` swaps in `src/distractor_rl/orchestrator.py` and runs `rl/scripts/train.py` / `evaluate.py`.
- Answer check = the Eedi judge text (gpt-5-nano, reasoning low); incorrect answers get a second call against the
  target distractors only (`prompts/distractor_match_*.txt`); a literal match with the correct answer / a target distractor overrides the judge.
- OpenAI `invalid_prompt` refusals: 3 tries, then null verdict / no match / tie, logged in `outputs/<run>/rollouts/flagged.jsonl`.

```bash
cd ../rl && source env.sh && cd ../distractor_rl
python -m pytest tests -q -p no:cacheprovider
tmux new -s distractor 'bash scripts/run_pipeline.sh'      # RUN=<name> continues a run; logs in logs/
```
