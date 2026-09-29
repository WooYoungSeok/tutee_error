# Eedi conditional error generation — GRPO (Student RL)

Student (Qwen2.5-7B-Instruct) receives a problem Q and a misconception description C and writes a full
solution with a final answer. Reward: final answer wrong **and** the reward verifier says the solution
shows C (two samples, both `aligned`), plus one auxiliary term per experiment (BLEU diversity **or**
pairwise student-likeness inside the accepted set G), minus a truncation penalty.
Design document: `RL error generation implementation plan.md` (2026-09-29).

## Status

| Item | State |
| --- | --- |
| Environment (`~/venv/rl`) | done — vLLM 0.30.0+cu129, TRL 1.14.0, torch 2.13.0+cu129, DeepSpeed 0.19.7 (`requirements-lock.txt`) |
| Models in `~/hf_cache` | policy `Qwen/Qwen2.5-7B-Instruct`; reward verifier `WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2-trval-halfA`; test verifier `WooYoungSeok/deepseek-r1-0528-qwen3-8b-descriptive-verifier-v2-trval-halfB` |
| Eedi inputs in `data/raw/` | **missing** — `train_model_inputs.jsonl` + (`train_privileged_annotations.jsonl` or `all_judgements.csv`) |
| Unit tests (`tests/`) | pass (no GPU, no network) |
| Reward verifier as served (`check_verifier_server.py`, v2 test, 688 rows) | greedy 0.9695 = SFT eval of the same checkpoint (epoch 4); reward setting (n=2, T=0.6): false rejection 2.6 % on positives, false acceptance 3.8 % on negatives, invalid 0 % |
| Design items awaiting sign-off | see "Open design decisions" below — real runs must wait for them |

## Setup (once per server)

```bash
cd tutee_error/rl
bash setup_server.sh        # venv with the cu129 stack (the driver is 535 / CUDA 12.2: CUDA 13 wheels cannot run)
source env.sh               # every new shell: venv, CUDA_HOME, HF_HOME=~/hf_cache, secrets from ../.env
```

`../.env` must hold `OPENAI_API_KEY` (gpt-5-nano answer check), `HF_TOKEN` (private verifiers),
`WANDB_API_KEY` / `WANDB_PROJECT` (optional; without a key `report_to` falls back to none).

## Run order (from `rl/`, after `source env.sh`)

```bash
# 0) data (copy the two Eedi files into data/raw/ first)
python scripts/prepare_eedi.py                 # -> data/prepared/{train,test,privileged,split_manifest}.jsonl, meta.json
python scripts/prepare_mathedu_examples.py     # -> data/mathedu_student_examples.json (already committed)

# 1) inference servers on GPU 3 (verifier :8001 first, then the policy rollout server :8000)
bash scripts/launch_servers.sh configs/diversity.yaml
python scripts/check_verifier_server.py        # served reward verifier vs its SFT test accuracy

# 2) training on GPUs 0,1,2
bash scripts/run_train.sh configs/diversity.yaml --run_name diversity_seed42
bash scripts/run_train.sh configs/student_likeness.yaml --run_name student_likeness_seed42   # after judge sign-off

# resume an aborted run (reward execution failures abort the batch by design)
bash scripts/run_train.sh configs/diversity.yaml --run_name diversity_seed42 --resume latest
bash scripts/stop_servers.sh
```

Smoke tests (synthetic data in `data/smoke/`, run names must start with `smoke_`):

```bash
python scripts/make_smoke_data.py
bash scripts/run_train.sh configs/smoke_mock.yaml --run_name smoke_mock --max_steps 3   # mock rewards, no API
```

## GPU layout (4 × A100 80GB PCIe, no NVLink, all pairs `SYS`)

| GPU | Role |
| --- | --- |
| 0, 1, 2 | policy training: DeepSpeed ZeRO-2, optimizer on CPU (`configs/ds_zero2_offload.json`); reference model on each GPU |
| 3 | `trl vllm-serve` policy rollout (0.50 of memory, weights pushed every step) + `vllm serve` reward verifier (0.35) |

gpt-5-nano and (optionally) the student-likeness judge are API calls. Reward scoring runs on rank 0 as
one async pipeline: answer check → verifier request as soon as a rollout is judged incorrect → group
auxiliary score as soon as its 8 rollouts are done.

## Outputs (`outputs/<run>/`)

- `run_meta.json` — config chain + hash, package versions, prompt hashes, data meta, reward settings
  (verifier sampling, stop ids, BLEU signature, judge decoding), TRL loss settings.
- `rollouts/step_XXXXXX.jsonl` — every rollout: solution, token count, EOS/truncation, answer-check
  record (raw response, extracted answer, verdict, reason, model, prompt version, response/request id,
  usage, latency, attempts), verifier raw outputs and labels, distractor match (diagnostic), main /
  aux / truncation / total reward.
- `rollouts/groups_XXXXXX.jsonl` — per group: K, G, BLEU matrix or every A/B placement with the judge response.
- `epoch_checkpoints/epoch-K/` — model at every epoch end (all kept; best epoch chosen on test).
- `checkpoint-N/` — rolling full checkpoint (optimizer state) for `--resume`, only the latest is kept.
- W&B / trainer logs: TRL metrics plus `answer/*`, `verifier/*`, `target/success_rate`, `groups/*`,
  `aux/*`, `truncation/*`, `distractor/*`, `diversity/*` or `student_likeness/*`, `timing/*`.

## Files

```
configs/common.yaml                  all shared settings (diversity.yaml / student_likeness.yaml only set the mode)
configs/ds_zero2_offload.json, ds_zero3.json, accelerate_*.yaml
prompts/                             Student, gpt-5-nano answer judge, student-likeness judge (verifier prompts: ../verifier_sft/prompts)
src/tutee_rl/data.py                 join + checks + train/test question-group split
src/tutee_rl/rewards.py              pure reward arithmetic (main, truncation, BLEU, pair schedule, Borda score)
src/tutee_rl/clients.py              gpt-5-nano answer check, verifier client, pairwise judge (retry/abort policy)
src/tutee_rl/orchestrator.py         TRL adapter: gather across ranks, score on rank 0, broadcast, logs, metrics
scripts/train.py, run_train.sh       GRPO training
scripts/launch_servers.sh, stop_servers.sh, server_settings.py, check_verifier_server.py
scripts/prepare_eedi.py, prepare_mathedu_examples.py, make_smoke_data.py
```
