# Newman 단계 × 원본 오류 유형 조건부 오류 생성 (Student RL + verifier A/B SFT)

`Student(Q, N, E) → S`: 문제 Q, Newman 단계 N, 원본 데이터셋의 오류 유형 E를 받아 그 조건에 맞는 틀린 풀이 S를 쓴다.

- 이어받는 에이전트: **[`AGENTS.md`](AGENTS.md)** (작업 규칙, 현재 상태, 다음 단계)
- 결정 기록: [`docs/decisions.md`](docs/decisions.md) (계획서보다 우선) · 계획서 원문: [`docs/experiment_plan.md`](docs/experiment_plan.md)
- 설정·결과: [`../rl/EXPERIMENTS.md`](../rl/EXPERIMENTS.md) Newman 절 (run 기록에서 `scripts/record_experiment.py`로 옮긴다)

| 모델 | 학습 데이터 | 쓰임 |
| --- | --- | --- |
| verifier A (`configs/verifier_half_a.yaml`, Qwen2.5-Math-7B-Instruct) | SFT train half A | RL 보상 (n=2, T=0.6, 둘 다 aligned) |
| verifier B (`configs/verifier_half_b.yaml`, DeepSeek-R1-0528-Qwen3-8B) | SFT train half B | RL validation·test 채점 (보상에 쓰지 않음) |
| Student (`configs/{student_likeness,diversity}.yaml`, Qwen2.5-7B-Instruct) | GSM8K RL train 조건 | GRPO, 보상 = 오답 판정 × A 정렬 + 0.5 × 보조항 + 길이 벌점 |

기존 `../rl`(Eedi GRPO)과 `../verifier_sft`(descriptive verifier) 코드는 **수정하지 않는다**. 다음 모듈을 import해서 쓴다.
- `tutee_rl`: gpt-5-nano 채점·student-likeness judge 클라이언트와 재시도/중단 정책, 보상 산술
- `verifier_common`, `prepare_descriptive_pairs`: 토큰화·정확 일치 판정·지표, v2 품질 필터

## 현재 상태 (2026-10-01)

| 항목 | 상태 |
| --- | --- |
| 코드 | 완료. 단위 테스트 51개 (네트워크·GPU 없음) |
| 매핑 워크북 | 검증 완료 (sha256 `9324bac2…`, 이름·정의·D열 26행 모두 일치). git 제외, 재준비 때만 필요 |
| SFT 데이터 | 적격 사례 2,672 → half A 1,081 / half B 1,063 / test 528 앵커 (쌍 행 2,162 / 2,126 / 1,056). 형식·loss mask 점검 실패 0 |
| RL 데이터 | GSM8K train+test, 질문당 1조건(16개 유형 균형): train 6,336 / validation 704 / test 1,752 |
| smoke | 이전 서버(A100 × 2)에서 verifier SFT·평가, GRPO(mock)+재개, Student 평가 통과 |
| 승인 | backbone, taxonomy(이름·정의·NEA 개요·단계 정의), verifier·Student 프롬프트 완료(verifier SFT 시작 가능). 답 채점 프롬프트+GSM8K 답 형식 계약, 학생다움 judge 재사용은 RL 전 확인 대기 |
| 남은 `REQUIRED` | verifier A/B checkpoint (SFT 평가 후) |

## 업로드가 필요한 파일

| 파일 | 위치 | 비고 |
| --- | --- | --- |
| `.env` | 저장소 루트 `tutee_error/.env` | `OPENAI_API_KEY`, `HF_TOKEN`, `WANDB_API_KEY`, `WANDB_PROJECT`. **`KEY=value` (`=` 양옆 공백 없이)**: `../rl/env.sh`, `../verifier_sft/setup_server.sh`는 .env를 셸로 실행한다 |
| (재준비할 때만) 매핑 워크북 `Newman_relabeling_영석_마무리 (1).xlsx` | `newman_experiment/data/raw/` | 준비된 데이터와 `manifests/taxonomy_mapping.json`이 커밋되어 있어 평소에는 필요 없다. NFD 파일 이름도 인식 |
| (선택) SFT 단위 변환 허용 목록 | 예: `data/raw/*.jsonl` (`{"question": ...}`) | `configs/data.yaml` `unit_eligibility.extra_allowlists`에 경로·sha256 추가 |

GSM8K는 `scripts/fetch_sources.py`가 HF `openai/gsm8k` 고정 리비전(`740312a`)에서 받고 sha256을 확인한다.

## 설치 (서버, 최초 1회)

```bash
cd tutee_error && git checkout rl-grpo
(cd rl && bash setup_server.sh)             # ~/venv/rl    : vLLM 0.30, TRL 1.14, torch 2.13+cu129
(cd verifier_sft && bash setup_server.sh)   # ~/venv/tutee : torch 2.11+cu128, transformers 5.17, DeepSpeed 0.19.7
cd newman_experiment && bash setup_server.sh   # openpyxl 추가, 단위 테스트, GSM8K 다운로드
source env.sh          # 새 셸마다 (RL venv).  verifier SFT: source env.sh sft
```

## 실행 순서 (`newman_experiment/`에서)

```bash
# 0) 데이터 (이미 준비·커밋됨. 입력이나 규칙을 바꿀 때만 다시)
python scripts/prepare_data.py --stage sft      # 워크북 검증 → 품질 필터 → 전역 80:20 → half A/B → negative 1:1 → 길이
python scripts/prepare_data.py --stage rl       # GSM8K 조건: train/validation(90:10)/test
python scripts/check_formatting.py --config configs/verifier_half_a.yaml   # (B도)

# 1) 사용자 확인 뒤 승인 기록 (내용 해시에 묶임; 수정하면 다시 승인)
python scripts/approve.py --status
python scripts/approve.py taxonomy_definitions --note "..."

# 2) verifier SFT (GPU 1장, 한 번에 하나: 7-8B 한 run이 host RAM ~229 GiB)
#    한 번에: tmux new -s newman_sft 'bash scripts/run_sft_pipeline.sh'   (A 학습 → B 학습 + A 평가(GPU 1) → B 평가)
GPU=0 bash scripts/run_train_verifier.sh configs/verifier_half_a.yaml
GPU=0 bash scripts/run_train_verifier.sh configs/verifier_half_b.yaml
source env.sh sft
python scripts/eval_verifier.py --config configs/verifier_half_a.yaml --run_dir outputs/<verifier_half_a run> --include_base
python scripts/eval_verifier.py --config configs/verifier_half_b.yaml --run_dir outputs/<verifier_half_b run> --include_base
#    best(macro-F1 → neg. false acceptance; test loss는 보고만)의 경로를 configs/rl_common.yaml
#    verifier.checkpoint (A), evaluation.verifier.checkpoint (B)에 적는다
python scripts/upload_verifier_hf.py --run_dir outputs/<run>          # best → HF private repo (HF_TOKEN)
#    API 모델 verifier 비교 (같은 system/user 메시지, 같은 판정; RL venv: source env.sh)
python scripts/eval_verifier_api.py --model gpt-5.6-sol               # --model gpt-5.1
python scripts/compare_verifiers.py --entry A=outputs/<A run>/test_eval/epoch-K --entry B=... \
    --entry gpt-5.6-sol=outputs/verifier_api_gpt-5.6-sol_seed42_<stamp> --entry gpt-5.1=...   # reports/verifier_comparison_*.md
#    다른 test로 다시 평가할 때 기존 test_eval/을 지키려면 eval_verifier.py --only epoch-K --eval_dir <새 폴더>

# 데이터 v3 (원본 풀이당 positive 1 + 같은 데이터셋 negative 1 + 다른 데이터셋·다른 단계 negative 1)
python scripts/prepare_data.py --config configs/data_v3.yaml --stage sft      # -> data/prepared_v3/sft, manifests_v3/
CFG_A=configs/verifier_half_a_v3.yaml CFG_B=configs/verifier_half_b_v3.yaml PIPELINE_LOG=logs/sft_pipeline_v3.log \
    bash scripts/run_sft_pipeline.sh
#    2026-10-01 실행은 scripts/run_verifier_v2_v3_chain.sh (v2 끝 → v3 학습, HF 업로드, 서로의 test로 교차 평가)

# 3) 서빙된 verifier 확인 (보상 경로 그대로: greedy + n=2/T=0.6)
bash scripts/launch_eval_servers.sh configs/diversity.yaml
python scripts/check_verifier_server.py --config configs/diversity.yaml --role a    # --role b
bash scripts/stop_servers.sh

# 4) Student GRPO + 평가 (두 실험, 무인 실행, 중단 시 자동 재개; GPU 4장 기준)
tmux new -s newman 'bash scripts/run_rl_pipeline.sh student_likeness diversity'
#    학습 → validation에서 snapshot 선택(B 기준 평균 reward) → test에서 base + 모든 snapshot 보고
#    단계별: launch_servers.sh → run_train_student.sh → evaluate_student.py --split validation / --split test

# 5) API baseline (gpt-5.6-sol), 모델 간 학생다움 비교(같은 rollout 번호 k), 기록
python scripts/generate_api_baseline.py --config configs/student_likeness.yaml --model gpt-5.6-sol
python scripts/evaluate_student.py --config configs/student_likeness.yaml --out outputs/<run>/test_eval --api_dirs outputs/api_baselines/gpt-5.6-sol --stage score
python scripts/compare_student_likeness.py --config configs/student_likeness.yaml --x outputs/<run>/test_eval/<best> --y outputs/<run>/test_eval/base
python scripts/record_experiment.py outputs/<run>
```

Smoke (인프라 확인; run 이름 `smoke_`로 시작해야 하며 미승인 초안·mock 보상이 허용된다):

```bash
GPU=0 bash scripts/run_train_verifier.sh configs/smoke/verifier_small.yaml --run_name smoke_verifier --limit 64 --max_steps 4
python scripts/make_smoke_data.py && bash scripts/launch_servers.sh configs/smoke/rl_mock.yaml   # GPU 번호는 서버에 맞게
bash scripts/run_train_student.sh configs/smoke/rl_mock.yaml --run_name smoke_rl --max_steps 3
```

## 실행 차단 장치 (작업 규칙 1)

- **`REQUIRED`**: 결정이 없는 값이 있으면, 그 값을 읽는 단계가 시작을 거부한다. 지금 남은 것은 verifier A/B checkpoint뿐이다.
- **승인**: `configs/approvals.yaml`에 파일 sha256(또는 값)을 기록한다. 실제 run은 사용하는 파일이 승인된 내용과 같을 때만 시작한다.
- **데이터**: 워크북으로 검증된 데이터(`meta.json`의 `mapping_verified`)만 실제 학습에 쓰인다.
- **자원**: effective batch(SFT 32, RL 48)가 다르면 시작하지 않는다. 모든 checkpoint를 보관하므로 예상 저장량이 여유 공간을 넘어도 시작하지 않는다.

## 설계 요점

- **라벨**: 이름은 워크북 A열, 정의는 B열 원문을 쓴다(Stepwise 두 유형은 정의가 없어 그 줄을 뺀다). 단계는 D열이다. 데이터 라벨은 데이터셋 안의 승인된 alias로만 해석한다. N = mapping(E)는 `Taxonomy.condition()`만 만든다.
- **품질 필터**: v2 필터(status ok, 그림 없는 문제 제외, 중복 제거)에 더해, 같은 학생 풀이에 오류 라벨이 둘 이상이면 그 풀이를 제외한다. 이때 pool 밖 원자료의 라벨(Stepwise "None of the above" 등)도 센다.
- **전역 분할**: SFT 사례와 GSM8K 전체를 한 문제 키로 묶어 80:20으로 나눈다. SFT train은 A/B 50:50이다. RL은 train을 90:10으로 나눠 validation을 만드는데, SFT 풀이가 없는 GSM8K 전용 그룹에서만 뽑는다. 층마다 독립 난수를 쓴다. 같은 그룹은 같은 split이므로 RL validation/test 질문은 verifier 학습에 없고, SFT test 질문은 RL train에 없다.
- **negative**: 원본 풀이당 positive 1 + negative 1이다. `random.Random(42)`를 영역마다 새로 만들고, 같은 원본 데이터셋의 다른 채택 유형에서 균등하게 뽑는다(계획서 4.3; 전체 16개 유형에서 뽑는 방식은 verifier가 라벨 출처를 배워서 폐기). N' = mapping(E'). 단위 두 유형은 허용 목록 True인 질문에만 쓰고, 그런 질문에서는 데이터셋에 단위 유형이 있으면 그것을 우선한다(자기 라벨이 단위 유형인 풀이 제외).
- **단위 허용 목록**: llm_tutee_tutor `UNIT_CONV_RAW` 원문을 쓴다(AST 추출, 출처 해시). 보정 후 train 845 / test 203이며, 준비 때마다 고정 parquet 내용과 대조한다.
- **보상과 지표**: `main`은 정답·판정 불가 −0.75 / 오답 + A 2/2 aligned 1 / 그 외 0이다. 절단은 −0.5, 보조항은 × 0.5다. 학습 지표는 `verifier_a/*`, 평가 지표는 `b_*`로 이름을 구분한다. gpt-5-nano 두 역할은 요청에 `reasoning: {effort: low}`를 보낸다.
- **IS 보정**: TRL 1.14 키를 명시하고, 가중치가 0인 rollout 비율 `sampling/importance_sampling_zero_weight_fraction`을 추가로 기록한다.

## 파일

```
AGENTS.md, CLAUDE.md           에이전트 인수인계 (CLAUDE.md는 AGENTS.md를 불러옴)
docs/                          계획서 원문, 결정 기록
configs/                       taxonomy, data, verifier_{common,half_a,half_b}, rl_common, student_likeness, diversity,
                               approvals, accelerate_*, smoke/
prompts/                       verifier system/user, Student, GSM8K 답 형식 계약 (judge 프롬프트는 ../rl/prompts 재사용)
data/unit_conversion_allowlist_gsm8k.json, data/prepared/{sft,rl}/
manifests/                     taxonomy_mapping(워크북 검증), case_manifest, question_groups, sft_pair_manifest, unit_eligibility_gsm8k
reports/                       data_audit.md, format_check_verifier_half_{a,b}.md
src/newman/                    common, taxonomy, sources, unit_eligibility, splits, negatives, rl_conditions,
                               verifier_format, clients, orchestrator, metrics, approvals, preflight
scripts/                       fetch_sources, prepare_data, check_formatting, approve, train_verifier(+run_…sh), eval_verifier,
                               check_verifier_server, train_student(+run_…sh), evaluate_student, generate_api_baseline,
                               compare_student_likeness, record_experiment, make_smoke_data, server/launch/stop, run_rl_pipeline.sh
tests/                         단위 테스트
```

`data/raw/`, `data/smoke/`, `outputs/`, `logs/`는 git 제외.

## run 출력 (`outputs/<experiment>_seed42_<YYYYmmdd_HHMMSS>`, Asia/Seoul = W&B run 이름)

- **verifier**:
  - `run_meta.json`: 설정·데이터·프롬프트·taxonomy 해시, 승인 상태, 실제 optimizer 클래스·beta/eps, 저장 예상량, git, 버전
  - `epoch_checkpoints/epoch-K/`: 모두 보관
  - `test_eval/<epoch-K|base>/{predictions.jsonl, generation_meta.json, metrics.json}`, `test_eval/summary.json`(best)
- **Student**:
  - `run_meta.json`: 실제 API 요청 필드 포함
  - `rollouts/step_*.jsonl`, `groups_*.jsonl`
  - `epoch_checkpoints/epoch-{0.5,…}`, `checkpoint-N/`(재개용, 모두 보관, 실측 크기)
  - `eval_validation/`(best 선택), `test_eval/`(보고, paired bootstrap)

## 저장 공간 (모든 checkpoint 보관, 작업 규칙 5)

- verifier 한 run: snapshot 5개 × 15–16 GB.
- Student 한 run: snapshot 4개 × 15 GB + 재개 checkpoint 4개(0.5 epoch마다) × 약 114 GB ≈ 0.53 TB.
- SFT 두 run(약 0.16 TB)과 RL 두 run을 합쳐 약 1.3 TB로, 2 TiB 디스크에 들어간다. 공간이 모자라면 `train_student.py`가 시작하지 않는다.

## 테스트

```bash
source env.sh && python -m pytest tests -q -p no:cacheprovider
```
