# RL 실험 기록 (학습·test 설정)

모든 값은 실제 run이 저장한 기록(`outputs/<run>/run_meta.json`, `test_eval/<model>/generation_meta.json`,
`metrics.json`)에서 옮겼다. 설정 원본은 `configs/common.yaml` + 실험별 yaml이다
(student_likeness run의 config sha256 `ba5dd6bd…`).

## 1. 공통 학습 설정 (두 실험 동일)

| 구분 | 항목 | 값 |
|---|---|---|
| 모델 | Student (policy) | `Qwen/Qwen2.5-7B-Instruct`, bf16, sdpa |
| 데이터 | Eedi KEEP 1,207문제 / 2,529쌍 | 문제 본문(NFKC·공백 정규화) 그룹 기준 8:2 split, `RandomState(42)` |
| | train / test | 2,048쌍·965문제 / 481쌍·242문제 (validation 없음) |
| | 프롬프트 길이 | 최대 433, 평균 157 토큰 (한도 1,024) |
| Student 입력 | system | `prompts/student.txt` v2 (sha256 `2a8b2067…`), `{error_description}` = misconception 설명 |
| | user | 문제 본문 |
| 샘플링 (rollout) | temperature / top_p / top_k / repetition penalty | **1.0 / 1.0 / 0(없음) / 1.0** |
| | 최대 생성 길이 | 1,024 토큰 |
| GRPO | 그룹 크기 G | 8 |
| | step당 | 48 풀이 = 6문제 (GPU 3장 × per_device 8 × grad_accum 2) |
| | epoch / 총 step | 2 epoch / 682 step (epoch당 341) |
| | lr / 스케줄 | 1e-6, warmup 10% 후 선형 감소 |
| | KL beta / clip ε | 0.04 / 0.2 |
| | loss / reward 정규화 | `dapo` / 그룹 단위(`scale_rewards=group`), num_iterations 1 |
| | vLLM IS 보정 | TRL 기본(`sequence_mask`, 켜짐), bias-corrected KL 켜짐 |
| | max grad norm | 1.0 |
| 저장 | 모델 스냅샷 | 0.5 epoch마다 `epoch_checkpoints/epoch-{0.5,1.0,1.5,2.0}` (step 170/341/512/682), 모두 보관 |
| | 재개용 전체 체크포인트 | 50 step마다, 최신 1개만 |
| 인프라 | 학습 | GPU 0–2, DeepSpeed ZeRO-2 + optimizer CPU offload |
| | 추론 | GPU 3: `trl vllm-serve` rollout(메모리 0.50) + reward verifier `vllm serve`(0.35) |
| 버전 | | torch 2.13.0+cu129, transformers 5.17.0, TRL 1.14.0, vLLM 0.30.0+cu129, DeepSpeed 0.19.7, openai 3.20.0, sacrebleu 2.6.0 |

## 2. Reward (학습)

rollout마다 `main + 0.5 × aux + truncation`, 가중치 `[1, 0.5, 1]`.

| 항목 | 규칙 |
|---|---|
| main | +1: 최종 답 오답 **그리고** reward verifier 2개 샘플 모두 `aligned` / 0: 오답이지만 not aligned / −0.75: 정답 또는 최종 답 추출 불가(null) |
| 최종 답 판정 | `gpt-5-nano`, Responses API, strict JSON schema, reasoning effort API 기본, max output 8,000, timeout 120 s, 최대 6회 시도. 입력: 문제, AnswerContract, 정답, 생성 풀이 (misconception·보기·verifier 결과는 주지 않음). 지시문 sha256 `b29a3e99…`(system) / `9b1c770a…`(user) |
| | 스키마 규칙: `extracted_answer`가 `"null"`/빈 문자열이면 위반. `"none"`/`"n/a"`는 verdict가 null일 때만 위반 (실제 답 "none" 허용) |
| reward verifier | `WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2-trval-halfA` (epoch 4). n=2, T 0.6, top_p 1, top_k 없음, repetition penalty 1.0, max 10 토큰, stop [151643, 151645], 정확히 `aligned`/`not_aligned`만 인정. 입력은 verifier SFT와 같은 chat template·지시문(`../verifier_sft/prompts`) |
| truncation | EOS 없이 1,024 토큰에서 잘리면 −0.5 |
| aux: student_likeness | 통과(G) 풀이가 2개 이상인 그룹에서 모든 쌍을 `gpt-5-nano` judge로 비교(A/B 위치 무작위, 무승부 허용), 정규화 승률(승 1, 무 0.5). judge에는 MathEDU 실제 학생 풀이 2개(id 13427, 8584)를 예시로 제공. max output 8,000. 지시문 sha256 `199506ca…` / `fb294500…` |
| aux: diversity | G 안에서 `1 − max_j sentence-BLEU(S_i, S_j)/100`. sacrebleu `nrefs:1|case:mixed|eff:yes|tok:13a|smooth:exp|version:2.6.0` |
| API 연결 | 채점·judge가 한 연결 풀 공유(크기 = 동시 요청 수 192 + 128, keep-alive 600 s) |

## 3. Test 평가 설정

| 항목 | 값 |
|---|---|
| 데이터 | test 481쌍 × 8 풀이 = 3,848 풀이 / 모델 |
| 생성 | vLLM offline, 학습과 같은 샘플링(T 1.0, top_p 1.0, top_k 0, rep 1.0, 1,024 토큰), 풀이마다 seed = sha256(42\|PairId\|k) → 모든 모델에 같은 seed |
| 채점 | 학습 reward와 동일(같은 gpt-5-nano 판정, judge, 가중치). **verifier만** 독립 모델 `WooYoungSeok/deepseek-r1-0528-qwen3-8b-descriptive-verifier-v2-trval-halfB`(epoch 5)로 교체, 샘플링 동일(n=2, T 0.6, stop [151645]) |
| 대상 | 학습 전 모델(`base`) + 스냅샷 4개 |
| best 선택 | test 평균 reward(`reward/total_mean`) 최고. test에서 골랐으므로 점수는 낙관적 |
| 함께 기록 | 성공률(오답 + half-B 2회 aligned), 정답 비율, 목표 오답 보기 일치율 등 (`test_eval/summary.json`) |

## 4. 실험별 결과

### student_likeness — `student_likeness_seed42_20260929_115310`
- W&B: `tutee_error_rl/runs/3379c05b`. 학습 2026-09-29 11:54 → 09-30 01:28 (step당 약 71 s).
- best: **epoch-2.0** → Hugging Face (private) `WooYoungSeok/qwen2.5-7b-instruct-student-likeness-error-generator-epoch2`
  (`generation_config.json`은 위 학습 샘플링으로 수정해 올림).

| 모델 | 평균 reward | 성공률 | 정답 비율 | 오답 중 half-B 통과 | 목표 오답 보기 일치 |
|---|---|---|---|---|---|
| base | 0.088 | 41.8% | 57.4% | 98.1% | 24.7% |
| epoch-0.5 | 0.710 | 72.7% | 26.4% | 98.7% | 24.0% |
| epoch-1.0 | 0.688 | 71.3% | 27.0% | 97.7% | 20.2% |
| epoch-1.5 | 0.740 | 74.0% | 24.6% | 98.1% | 21.2% |
| **epoch-2.0** | **0.760** | **75.0%** | **23.6%** | 98.2% | 21.2% |

### diversity — `diversity_seed42_20260930_025827`
- 설정은 위와 같고 aux만 BLEU diversity. W&B `tutee_error_rl/runs/ffc4cf70`. 학습 2026-09-30 03:00 → 11:34
  (682 step, step당 평균 41.6 s). 스냅샷 4개(`epoch-0.5`~`2.0`) 저장, `generation_config.json`은 학습 샘플링으로 수정.
- **test 평가(best 선택)는 사용자 요청으로 보류.** 마지막 모델 `epoch-2.0`을 Hugging Face (private)
  `WooYoungSeok/qwen2.5-7b-instruct-diversity-error-generator-epoch2`에 올림 (best가 아니라 마지막 스냅샷).
- 학습 중 지표 (train, 0.5 epoch 평균, verifier = half-A):

| step | 전체 reward | 성공률 | 정답 비율 | 통과 풀이 간 최대 BLEU | 중복 풀이 | KL |
|---|---|---|---|---|---|---|
| 0–169 | 0.654 | 68.2% | 29.7% | 0.431 | 5.6% | 0.074 |
| 170–340 | 0.887 | 78.1% | 18.3% | 0.372 | 2.0% | 0.100 |
| 341–511 | 0.905 | 78.6% | 17.5% | 0.358 | 0.9% | 0.109 |
| 512–681 | 0.940 | 80.3% | 15.7% | 0.362 | 3.7% | 0.105 |

- 평가 방법(보류 해제 시): `python scripts/evaluate.py --config configs/diversity.yaml --run outputs/diversity_seed42_20260930_025827 --include_base`
  (test verifier 서버 먼저: `bash scripts/launch_eval_server.sh configs/diversity.yaml`)

## 5. 결정 이력 (2026-09-29)

| 결정 | 이유 |
|---|---|
| reward verifier = half-A, test verifier = half-B | 학습 reward와 평가가 학습 데이터를 공유하지 않게 |
| Student 지시문 v2 (오류 언급·정답 제시 금지 3줄 추가) | v1에서 오답의 124/135가 오류를 해설하듯 씀(비교 실험에서 해설형 82% → 10%) |
| 샘플링 Qwen 기본값 → T 1.0 / top_p 1.0 | top-k/top-p 샘플링이 TRL의 풀이 단위 vLLM IS 비율을 약 0.1로 만들어 학습 신호가 약 1/10로 줄었음. llm_tutee_tutor와 같은 설정으로 복귀 |
| step당 192 → 48 풀이, 3 → 2 epoch, warmup 10% + 선형 감소 | llm_tutee_tutor처럼 작은 배치로 자주 업데이트(epoch당 85 → 341회) |
| 스냅샷 0.5 epoch마다 | epoch 2로 줄여도 best 후보를 4개 유지 |
| judge = gpt-5-nano, judge·채점 max output 8,000 | 2,000/4,000에서 추론만으로 응답이 잘려 재시도 발생 |
| OpenAI 연결 풀 재사용 | step마다 수백 개 새 연결 → 약 20분 후 연결 거부 누적으로 학습 중단 |
| 실험 순서 student_likeness → diversity, run 이름에 시작 시각 | 사용자 요청 |
| diversity: test 평가 보류, 마지막 스냅샷(epoch-2.0) 업로드 (2026-09-30) | 사용자 요청. 파이프라인은 평가 직전에 중단 |

## 6. 중단된 run (`outputs/_aborted/`)

| 폴더 | 중단 이유 |
|---|---|
| `diversity_seed42_student_prompt_v1` | Student 지시문 v1의 해설형 오답 (step 4) |
| `student_likeness_seed42_oom_start` | 비교 스크립트가 남긴 vLLM 프로세스로 GPU 0 메모리 부족 (시작 직후) |
| `student_likeness_seed42_api_connection_errors` | OpenAI 연결 오류 누적으로 3회 중단 (step 48) |
| `student_likeness_seed42_qwen_sampling_accum8` | Qwen 기본 샘플링 + step당 192 풀이: 학습 신호 부족 (step 43) |
| `student_likeness_seed42_20260929_104900_stopped_for_tmux` | tmux로 재시작 (step 22) |
| `student_likeness_seed42_20260929_111558_none_answer_rule` | 실제 답 "none"을 스키마 위반으로 거부한 버그 (step 23) |

---

# Newman 단계 × 원본 오류 유형 실험 (`newman_experiment/`)

계획서 원문 `newman_experiment/docs/experiment_plan.md`, 사용자 결정 `newman_experiment/docs/decisions.md`(계획서보다 우선),
인수인계 `newman_experiment/AGENTS.md`. **계획** = 실행 전 config 값, **실행 확인** = run이 남긴 기록(`run_meta.json`,
`generation_meta.json`, `metrics.json`, `summary.json`, `prepared/*/meta.json`)에서 옮긴 값. 실행 확인 표는
`python scripts/record_experiment.py outputs/<run>`으로 만든다. 시각은 Asia/Seoul.

## N1. 계획 — verifier A/B SFT (`configs/verifier_common.yaml`, `verifier_half_{a,b}.yaml`)

| 항목 | 계획 값 |
|---|---|
| 과제 | (Q, 틀린 풀이 S, 목표 N, 목표 E) → `aligned` / `not_aligned`, 정확 일치(그 외 invalid) |
| backbone (승인) | A `Qwen/Qwen2.5-Math-7B-Instruct`, B `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`, 각자 공개 backbone에서 시작 |
| 데이터 | A = train half A, B = train half B, 평가 = 공통 SFT test (validation 없음) |
| 학습 | full SFT, lr 1e-5, 최대 5 epoch, wd 0.01, warmup 10%, linear, batch 8 × accum 4 × GPU 1 = 32(다르면 시작 거부), bf16, grad ckpt, max len 4,096(자르지 않음), ZeRO-2 + CPU optimizer offload, seed 42 |
| 저장 | 매 epoch 모델 snapshot, 모두 보관. 재개용 optimizer checkpoint는 저장하지 않음(설정으로 켤 수 있음) |
| 평가·선택 | SFT test greedy(최대 10 토큰, rep 1.0), test loss(보고만). 선택: macro-F1 최대 → negative false acceptance 최소 → 같으면 앞 epoch. test에서 고르므로 낙관적 |

## N2. 계획 — Student GRPO (`configs/rl_common.yaml` + `student_likeness.yaml` / `diversity.yaml`)

| 항목 | 계획 값 |
|---|---|
| policy | `Qwen/Qwen2.5-7B-Instruct`, bf16, sdpa |
| 데이터 | GSM8K train+test, 질문당 1조건(16개 유형 균형). 전역 train을 RL train/validation 90:10, 전역 test = RL test |
| 샘플링 | G 8, T 1.0, top_p 1.0, top_k 0(끔; vLLM 0.30에서도 0 = 끔), rep 1.0, 최대 1,024 토큰 |
| GRPO | lr 1e-6, 2 epoch, warmup 10% + linear, 8 × GPU 3 × accum 2 = 48 풀이 = 6 조건/step, beta 0.04, eps 0.2, `dapo`, scale group, num_iterations 1, max grad norm 1.0, mask_truncated false |
| vLLM IS 보정 | correction true, `sequence_mask`, clip_max 3.0, clip_min null, bias-corrected KL true, 가중치 0 비율 지표 추가 |
| 보상 | main −0.75 / 1 / 0, truncation −0.5, aux 0.5 × (diversity 또는 student_likeness) |
| gpt-5-nano | 채점·judge 모두 reasoning effort low, max output 8,000, timeout 120 s, 6회, 동시성 192 / 128 |
| verifier A 호출 | n 2, T 0.6, top_p 1.0, top_k 끔, rep 1.0, max 10 토큰, 둘 다 aligned |
| 저장 | 0.5 epoch마다 snapshot과 재개 checkpoint, 모두 보관(run당 재개 4개 × 약 114 GB, 디스크 2 TiB 기준) |
| 선택·평가 | RL validation에서 verifier B 기준 평균 training reward 최고 snapshot. test는 base + 모든 snapshot 보고, 질문 그룹 paired bootstrap 1000 |
| API baseline | `gpt-5.6-sol`, reasoning 미전송(기본), max output 8,000, 조건당 8회 |
| 학생다움 직접 비교 | 같은 조건·같은 rollout 번호 k의 두 출력이 모두 B 통과일 때 gpt-5-nano(low) judge |

## N3. 실행 확인 — 데이터 준비 (검증된 워크북, 2026-10-01 00:50)

`prepare_data.py --stage sft` / `--stage rl`, `data/prepared/{sft,rl}/meta.json`, `reports/data_audit.md`. 다시 실행해도 산출물이 바이트 단위로 같음을 확인했다.

| 항목 | 값 |
|---|---|
| 매핑 워크북 | sha256 `9324bac2…`, 26행의 이름(A열)·정의(B열)·D열이 taxonomy.yaml과 모두 일치 (mapping_verified true) |
| 적격 SFT 사례 | 2,672 = EIC 1,346 / MathEDU 715 / MathClean 449 / Stepwise 162 |
| 다중 라벨 풀이 제외 | 풀이 EIC 2 / Stepwise 173 (그중 pool 밖 원자료 라벨로만 드러난 Stepwise 28), 레코드 EIC 4 / Stepwise 356 |
| SFT 영역: 앵커 / 쌍 행 / 문제 그룹 | half A 1,081 / 2,162 / 963 · half B 1,063 / 2,126 / 961 · test 528 / 1,056 / 474 |
| negative (2026-10-01 13:10 재생성, 현재) | 같은 데이터셋의 다른 유형에서 균등 추출(계획서 4.3) + 허용 목록 문제에서는 단위 유형 우선(자기 라벨이 단위 유형이면 제외). 우선 배정 27 / 25 / 10건. same-stage 146 / 158 / 55 (half A / half B / test), 후보 없음 0 |
| 단위 유형 negative | EIC Unit Conversion Error 27 / 25 / 10 (positive 73 / 65 / 32). MathEDU Measurement error 0 (positive 5 / 4 / 2): MathQA 질문에는 허용 목록이 없음 |
| (폐기된 구성) | 같은 날 16개 유형 전체에서 뽑았던 구성은 N8의 superseded run 결과로 폐기 |
| 길이 (2026-10-01, NEA 개요를 넣은 프롬프트) | verifier 입력: Qwen2.5-Math 최대 2,721, DeepSeek-R1-Qwen3 최대 2,652 토큰, 4,096 초과 0. Student 프롬프트(Qwen2.5-7B-Instruct): 최대 562, 평균 379 토큰, 1,024 초과 0 |
| 형식·loss mask | 3,218 / 3,182 쌍, 실패 0 |
| RL 조건 | train 6,336 / validation 704 / test 1,752 (질문당 1). 유형별 train 371–400. 단계: Comprehension 800, Process Skills 2,396, Reading 800, Transformation 2,340. 허용 목록 질문 train 763 / validation 80 / test 205 |
| RL 누출 점검 | validation 질문은 verifier 학습 데이터에 없음, test 질문은 A/B 학습 절반에 없음, 세 split 문제 그룹 공유 0 |

## N4. 실행 확인 — smoke (2026-09-30, 이전 서버 A100 80GB × 2, 드라이버 535)

| run | 기록 |
|---|---|
| `smoke_verifier_sft` | `Qwen/Qwen2.5-0.5B-Instruct`, 64쌍, 4 step, DeepSpeed on, effective batch 32. 실제 optimizer DeepSpeedZeroOptimizer > `DeepSpeedCPUAdam`, betas (0.9, 0.999), eps 1e-8, wd 0.01. epoch snapshot 2개(각 1.27 GB). `eval_verifier.py` 정상 |
| `smoke_rl_mock` | `Qwen/Qwen2.5-0.5B-Instruct`, mock 보상, 학습 GPU 0 + rollout GPU 1, 8 풀이/step, 3 step + `--resume latest` 1 step. snapshot 0.5/1.5/2.0, 재개 checkpoint 2·3·4 모두 보관(각 8.19 GB), IS 가중치 0 비율 기록. `evaluate_student.py` 정상, warmup 첫 step의 epoch-0.5는 base와 지표 동일(rollout seed 공유 확인) |
| 버전 | SFT torch 2.11.0+cu128 · transformers 5.17.0 · DeepSpeed 0.19.7 / RL torch 2.13.0+cu129 · TRL 1.14.0 · vLLM 0.30.0+cu129 |

이 smoke는 미검증 매핑의 초기 데이터로 돌렸다(인프라 확인 목적). 실제 7B/8B 학습과 유료 API 호출은 아직 없다.

## N5. 결정 이력

전체 표는 `newman_experiment/docs/decisions.md`. 2026-09-30 사용자 결정 요약:

- **매핑·정의:** 워크북 D열 매핑. 이름·정의는 A·B열이고, Stepwise 두 유형은 정의 줄을 생략한다.
- **verifier:** A/B backbone은 verifier_sft와 같다. 같은 학생 풀이에 라벨이 둘 이상이면 제외한다.
- **RL 데이터·선택:** 전역 train을 RL train/validation 90:10으로 나누고, 질문당 1조건을 유형 균형으로 배정한다. RL은 validation의 B 기준 평균 reward로 선택하고, SFT는 macro-F1 → negative false acceptance → test loss 순서로 선택한다.
- **baseline·비교:** RL Student와 비교할 API baseline은 gpt-5.6-sol(reasoning 기본, 8,000 토큰), 학생다움 비교는 같은 rollout 번호로 짝짓는다(judge는 gpt-5-nano low).
- **실행 계획:** 서버를 옮겨 SFT·RL을 이어서 진행한다.
- **2026-10-01:** 두 프롬프트의 단계 부분에 Newman's Error Analysis 개요를 넣고("네 단계 중 하나" 문장은 뺌) 단계 정의를 White(2009) 기반으로 다시 씀, Student 지시 문장 수정(승인 대기). negative는 16개 유형 전체에서 균등 추출(llm_tutee_tutor finetuning 방식)하되 허용 목록 문제에서는 단위 유형 우선, SFT 선택에서 test loss 제외, 디스크 2 TiB에 맞춰 RL 재개 checkpoint는 0.5 epoch마다 모두 보관.

## N6. 열린 결정

답 채점 프롬프트 재사용과 GSM8K 답 형식 계약, 학생다움 judge 재사용 승인(RL 전), C 생성 이력 없는 원본 포함 여부. taxonomy·verifier·Student 프롬프트는 2026-10-01 승인. 자세한 것은 `newman_experiment/docs/decisions.md`.

## N8. 실행 확인 — verifier SFT 1차 (superseded: negative를 16개 유형 전체에서 뽑은 데이터)

이 절의 두 run은 끝까지 학습·평가했지만, 아래 지름길 문제로 사용자 결정(2026-10-01)에 따라 쓰지 않는다. 모두 `outputs/_superseded/`에 보관.
B `verifier_half_b_seed42_20261001_070425`(W&B `5dd66872`, 07:06–08:57, 335 step): epoch-5 accuracy 0.9167, macro-F1 0.9166, negative false acceptance 0.1004, positive recall 0.9337, invalid 0. 같은 데이터셋 negative 53 / 168 수락, 다른 데이터셋 0 / 360.

### A 1차

`scripts/run_sft_pipeline.sh`(A 학습 → B 학습과 A 평가 동시 → B 평가)를 tmux `newman_sft`에서 실행.

| run | 기록 (`run_meta.json`) |
|---|---|
| `verifier_half_a_seed42_20261001_051819` | 시작 2026-10-01T05:20:00+09:00, W&B `tutee_error_newman_verifier/runs/baee62a2`, backbone `Qwen/Qwen2.5-Math-7B-Instruct`, 2162 쌍 행 / 1081 앵커(mapping verified True), lr 1e-05, 5 epoch, batch 8×4×1 = 32, 총 340 step, DeepSpeed True, optimizer DeepSpeedCPUAdam (betas [0.9, 0.999], eps 1e-08, wd 0.01), 사전 점검 경고 0, git `048c179`. 진행 중 (첫 로그 step 10 loss 4.412, step당 약 20 s) |

A 학습 종료 2026-10-01 07:04 (340 step, 1시간 42분). A 평가 `test_eval/summary.json` (SFT test 1,056행, 선택 규칙 macro-F1 → negative false acceptance, test에서 골라 낙관적):

| checkpoint | accuracy | macro-F1 | neg. recall | neg. false acceptance | pos. recall | invalid | pair acc. | test loss |
|---|---|---|---|---|---|---|---|---|
| base | 0.0000 | 0.0000 | 0.0000 | 0.0038 | 0.0000 | 0.9981 | 0.0000 | 5.5965 |
| epoch-1 | 0.6203 | 0.6147 | 0.7405 | 0.2595 | 0.5000 | 0.0000 | 0.3807 | 0.2290 |
| epoch-2 | 0.8258 | 0.8257 | 0.8125 | 0.1875 | 0.8390 | 0.0000 | 0.6742 | 0.1095 |
| epoch-3 | 0.8731 | 0.8721 | 0.7841 | 0.2159 | 0.9621 | 0.0000 | 0.7519 | 0.0846 |
| epoch-4 | 0.9025 | 0.9022 | 0.8504 | 0.1496 | 0.9545 | 0.0000 | 0.8068 | 0.0716 |
| **epoch-5 (best)** | 0.9138 | 0.9136 | 0.8598 | 0.1402 | 0.9678 | 0.0000 | 0.8277 | 0.0644 |

- epoch-5 95% CI(질문 그룹 bootstrap): accuracy [0.899, 0.929], macro-F1 [0.899, 0.928].
- **잘못 수락한 negative 74건이 모두 같은 데이터셋 negative**: 같은 데이터셋 74 / 168 (44%), 다른 데이터셋 0 / 360. 풀이의 출처와 라벨의 출처가 다른지를 단서로 쓰는 것으로 보인다(16개 유형 전체에서 negative를 뽑은 결과). 많이 틀린 쌍: MathEDU Wrong operation/concept ← Comprehension error 9, MathClean logic ↔ computing 11, Stepwise misunderstanding ← calculation 5.
- 목표 유형별로 가장 약한 것: MathEDU Comprehension error 0.823, EIC referencing context value 0.833, MathEDU Arithmetical 0.836.
- epoch 1→5 동안 계속 좋아졌고 5 epoch(계획 최대)에서 끝났다.

## N7. 중단·폐기된 run

| run | 이유 |
|---|---|
| `_superseded/verifier_half_a_seed42_20261001_051819`, `_superseded/verifier_half_b_seed42_20261001_070425` | 학습·평가는 끝났으나 negative를 16개 유형 전체에서 뽑아 verifier가 라벨의 출처 데이터셋을 단서로 씀(다른 데이터셋 negative 0/360 수락, 같은 데이터셋 32–44% 수락). 같은 데이터셋 negative로 되돌려 다시 학습(사용자 결정 2026-10-01) |

## N9. 실행 확인 — verifier SFT 2차 (같은 데이터셋 negative, 진행 중)

`scripts/run_sft_pipeline.sh`, tmux `newman_sft`. A 13:12–14:58, B 14:58–16:52, 평가 종료 17:11. 둘 다 best epoch-5.

#### verifier_half_a_seed42_20261001_131155 (실행 확인)

| 항목 | 값 |
|---|---|
| run / W&B | `verifier_half_a_seed42_20261001_131155` / tutee_error_newman_verifier |
| 역할 / half | reward / A |
| backbone | `Qwen/Qwen2.5-Math-7B-Instruct` |
| 데이터 | `newman_experiment/data/prepared/sft/half_a.jsonl` sha256 `6844546702c8`, 2162 rows / 1081 anchors, mapping verified True |
| 학습 | 5 epoch, lr 1e-05, wd 0.01, warmup 0.1, linear, batch 8x4x1 = 32, max grad norm 1.0, bf16 True, max len 4096 |
| optimizer (실제) | accelerate.utils.deepspeed.DeepSpeedOptimizerWrapper > deepspeed.runtime.zero.stage_1_and_2.DeepSpeedZeroOptimizer > deepspeed.ops.adam.cpu_adam.DeepSpeedCPUAdam {'lr': 0.0, 'betas': [0.9, 0.999], 'eps': 1e-08, 'weight_decay': 0.01} |
| 저장 | snapshots epoch-1 (15.24 GB), epoch-2 (15.24 GB), epoch-3 (15.24 GB), epoch-4 (15.24 GB), epoch-5 (15.24 GB); resume checkpoints none |
| 프롬프트 / taxonomy | system `a2513fd9a228` user `e8d93eafa952` / `9b7cc7964664` |
| 승인 | taxonomy_definitions: approved, verifier_prompt: approved, verifier_backbones: approved |
| 버전 / git | torch 2.11.0+cu128, transformers 5.17.0, deepspeed 0.19.7 / `7c7c02879b73` dirty True |
| 시간 | 2026-10-01T13:12:19+09:00 → 2026-10-01T14:57:56+09:00 |

SFT test (`newman_experiment/data/prepared/sft/test.jsonl` 1056 rows, sha256 `3c95e572aa6e`), selection rule ['macro_f1:max', 'negative_false_acceptance:min'], best **epoch-5** — chosen on the test split (user rule 5): the chosen checkpoint's test score is optimistic

| checkpoint | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | test_loss |
|---|---|---|---|---|---|---|---|
| base | 0.0000 | 0.0000 | 0.0000 | 0.0019 | 0.0000 | 0.9991 | 5.6107 |
| epoch-1 | 0.5701 | 0.5248 | 0.8788 | 0.1212 | 0.2614 | 0.0000 | 0.2064 |
| epoch-2 | 0.6127 | 0.5972 | 0.4167 | 0.5833 | 0.8087 | 0.0000 | 0.1841 |
| epoch-3 | 0.6686 | 0.6465 | 0.4186 | 0.5814 | 0.9186 | 0.0000 | 0.1730 |
| epoch-4 | 0.7017 | 0.6972 | 0.8239 | 0.1761 | 0.5795 | 0.0000 | 0.1558 |
| epoch-5 | 0.7528 | 0.7528 | 0.7367 | 0.2633 | 0.7689 | 0.0000 | 0.1352 |

#### verifier_half_b_seed42_20261001_145835 (실행 확인)

| 항목 | 값 |
|---|---|
| run / W&B | `verifier_half_b_seed42_20261001_145835` / tutee_error_newman_verifier |
| 역할 / half | test / B |
| backbone | `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` |
| 데이터 | `newman_experiment/data/prepared/sft/half_b.jsonl` sha256 `f203c910aa41`, 2126 rows / 1063 anchors, mapping verified True |
| 학습 | 5 epoch, lr 1e-05, wd 0.01, warmup 0.1, linear, batch 8x4x1 = 32, max grad norm 1.0, bf16 True, max len 4096 |
| optimizer (실제) | accelerate.utils.deepspeed.DeepSpeedOptimizerWrapper > deepspeed.runtime.zero.stage_1_and_2.DeepSpeedZeroOptimizer > deepspeed.ops.adam.cpu_adam.DeepSpeedCPUAdam {'lr': 0.0, 'betas': [0.9, 0.999], 'eps': 1e-08, 'weight_decay': 0.01} |
| 저장 | snapshots epoch-1 (16.39 GB), epoch-2 (16.39 GB), epoch-3 (16.39 GB), epoch-4 (16.39 GB), epoch-5 (16.39 GB); resume checkpoints none |
| 프롬프트 / taxonomy | system `a2513fd9a228` user `e8d93eafa952` / `9b7cc7964664` |
| 승인 | taxonomy_definitions: approved, verifier_prompt: approved, verifier_backbones: approved |
| 버전 / git | torch 2.11.0+cu128, transformers 5.17.0, deepspeed 0.19.7 / `7c7c02879b73` dirty True |
| 시간 | 2026-10-01T14:59:02+09:00 → 2026-10-01T16:51:25+09:00 |

SFT test (`newman_experiment/data/prepared/sft/test.jsonl` 1056 rows, sha256 `3c95e572aa6e`), selection rule ['macro_f1:max', 'negative_false_acceptance:min'], best **epoch-5** — chosen on the test split (user rule 5): the chosen checkpoint's test score is optimistic

| checkpoint | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | test_loss |
|---|---|---|---|---|---|---|---|
| base | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 20.4009 |
| epoch-1 | 0.5473 | 0.4554 | 0.1364 | 0.8636 | 0.9583 | 0.0000 | 0.3046 |
| epoch-2 | 0.6648 | 0.6629 | 0.7386 | 0.2614 | 0.5909 | 0.0000 | 0.2349 |
| epoch-3 | 0.7633 | 0.7633 | 0.7595 | 0.2405 | 0.7670 | 0.0000 | 0.1900 |
| epoch-4 | 0.7727 | 0.7726 | 0.7973 | 0.2027 | 0.7481 | 0.0000 | 0.1969 |
| epoch-5 | 0.7812 | 0.7811 | 0.8049 | 0.1951 | 0.7576 | 0.0000 | 0.3058 |

v2 test(같은 데이터셋 negative) 비교 (`newman_experiment/reports/verifier_comparison_v2_test_20261001.md`):

| verifier | accuracy [95% CI] | macro-F1 | neg. false acceptance | pos. recall | pair acc. | gpt-5.6-sol 대비 accuracy |
|---|---|---|---|---|---|---|
| A 2차 epoch-5 | 0.7528 [0.718, 0.782] | 0.7528 | 0.2633 | 0.7689 | 0.6420 | −0.075 [−0.109, −0.040] |
| B 2차 epoch-5 | 0.7812 [0.750, 0.810] | 0.7811 | 0.1951 | 0.7576 | 0.6705 | −0.046 [−0.078, −0.015] |
| A 1차 (폐기) | 0.7055 | 0.6837 | 0.5568 | 0.9678 | 0.4242 | −0.122 |
| B 1차 (폐기) | 0.7443 | 0.7346 | 0.4470 | 0.9356 | 0.5133 | −0.083 |
| gpt-5.6-sol | 0.8277 | 0.8276 | 0.1951 | 0.8504 | 0.7254 | – |
| gpt-5.1 | 0.6998 | 0.6962 | 0.4091 | 0.8087 | 0.5000 | −0.128 |

- 같은 데이터셋 negative 수락률이 1차의 0.557 / 0.447에서 0.263 / 0.195로 내려감. B 2차의 수락률은 gpt-5.6-sol과 같음(0.195), 대신 positive recall이 0.093 낮음.
- 학습 곡선이 불안정함(A: neg. false acceptance 0.12 → 0.58 → 0.58 → 0.18 → 0.26). epoch-5까지 accuracy가 계속 올라 5 epoch에서 수렴하지 않았을 수 있음.
- 가장 약한 곳: MathClean(0.58–0.60), Comprehension 단계(0.60–0.61).

2차 best 교차 평가 (`scripts/run_verifier_v2_v3_chain.sh`, 17:12–17:25, `<run>/test_eval_{v3_test,alltype_test}/epoch-5`), HF private 업로드 완료(`WooYoungSeok/newman-verifier_half_{a,b}_seed42_…-epoch-5`, missing 0):

| test | verifier | accuracy | neg. false acceptance | 같은 데이터셋 neg. 수락 | 다른 데이터셋 neg. 수락 | pos. recall | 원본 풀이 단위 acc. |
|---|---|---|---|---|---|---|---|
| v3 (1,584행) | A 2차 | 0.7090 | 0.3201 | 0.269 | 0.371 | 0.7670 | 0.447 |
| v3 | B 2차 | 0.7620 | 0.2348 | 0.191 | 0.278 | 0.7557 | 0.513 |
| v3 | gpt-5.6-sol | 0.8258 | 0.1856 | 0.203 | 0.169 | 0.8485 | 0.608 |
| v3 | gpt-5.1 | 0.6237 | 0.4593 | 0.428 | 0.491 | 0.7898 | 0.258 |
| 1차 (all-type, 1,056행) | A 2차 | 0.7206 | 0.3220 | 0.238 | 0.361 | 0.7633 | 0.525 |
| 1차 | B 2차 | 0.7367 | 0.2879 | 0.137 | 0.358 | 0.7614 | 0.551 |

- 2차 verifier는 다른 데이터셋·다른 단계 negative를 28–37% 수락(gpt-5.6-sol 17%)한다. 같은 데이터셋 negative만으로 학습해 이 유형의 negative를 본 적이 없음. v3 학습이 겨냥하는 부분.

## N10. 실행 확인 — API 모델 verifier와 비교 (SFT test 1,056행, 같은 데이터셋 negative, data sha256 `3c95e572…`)

사용자 지시(2026-10-01). API 모델에도 학습한 verifier와 **같은 system/user 메시지**를 같은 역할로 보냄(행마다 메시지 해시 대조). 같은 엄격 판정을 적용했고, reasoning은 보내지 않았으며 max_output_tokens는 8000, 행당 1회 호출. 1차(폐기) best는 이 test로 다시 평가함(`<run>/test_eval_same_dataset_negatives/epoch-5`, 원래 `test_eval/`은 보존). 표 전체: `newman_experiment/reports/verifier_comparison_superseded_vs_api_20261001.md`.

| verifier | run | accuracy [95% CI] | macro-F1 | neg. false acceptance | pos. recall | pair acc. | invalid | 사용량 (입력 / 출력 토큰) |
|---|---|---|---|---|---|---|---|---|
| A 1차 epoch-5 (폐기) | `_superseded/verifier_half_a_seed42_20261001_051819` | 0.7055 [0.682, 0.728] | 0.6837 | 0.5568 | 0.9678 | 0.4242 | 0 | – |
| B 1차 epoch-5 (폐기) | `_superseded/verifier_half_b_seed42_20261001_070425` | 0.7443 [0.719, 0.769] | 0.7346 | 0.4470 | 0.9356 | 0.5133 | 0 | – |
| gpt-5.6-sol | `verifier_api_gpt-5.6-sol_seed42_20261001_132300` | 0.8277 [0.801, 0.852] | 0.8276 | 0.1951 | 0.8504 | 0.7254 | 0 | 542,737 / 104,174 |
| gpt-5.1 | `verifier_api_gpt-5.1_seed42_20261001_132300` | 0.6998 [0.671, 0.729] | 0.6962 | 0.4091 | 0.8087 | 0.5000 | 0 | 542,737 / 12,442 |

- 잘린 응답 0, 느슨한 판정을 써도 invalid 0.
- 1차 verifier는 같은 데이터셋 negative를 거르지 못함(다른 단계 negative 수락 A 0.586, B 0.471). 데이터셋 지름길이라는 판단과 맞음.
- gpt-5.6-sol 기준 짝지은 차이(question-group bootstrap): accuracy A −0.122 [−0.151, −0.094], B −0.083 [−0.111, −0.056], gpt-5.1 −0.128 [−0.159, −0.099].
- 2차(재학습) A/B best는 평가가 끝나면 이 표에 추가한다.

### N10-2. 1차 학습 때의 test set(negative를 16개 유형 전체에서 무작위, sha256 `af37b797…`)으로 비교

1차 평가의 `predictions.jsonl`에서 예측 필드를 빼 복원했고 sha256이 1차 평가 기록과 일치함(`newman_experiment/data/prepared/sft_all_type_negatives_test/`). negative 528개 중 다른 데이터셋 360개, 같은 데이터셋 168개. 1차 A/B는 원래 `test_eval/epoch-5` 결과를 씀. 표 전체: `newman_experiment/reports/verifier_comparison_alltype_test_superseded_vs_api_20261001.md`.

| verifier | run | accuracy [95% CI] | macro-F1 | neg. false acceptance | 다른 데이터셋 neg. 수락 | 같은 데이터셋 neg. 수락 | pos. recall |
|---|---|---|---|---|---|---|---|
| A 1차 epoch-5 (폐기) | `_superseded/verifier_half_a_seed42_20261001_051819` | 0.9138 [0.899, 0.929] | 0.9136 | 0.1402 | 0 / 360 | 74 / 168 | 0.9678 |
| B 1차 epoch-5 (폐기) | `_superseded/verifier_half_b_seed42_20261001_070425` | 0.9167 [0.901, 0.934] | 0.9166 | 0.1004 | 0 / 360 | 53 / 168 | 0.9337 |
| gpt-5.6-sol | `verifier_api_gpt-5.6-sol_alltype_test_seed42_20261001_134120` | 0.8040 [0.779, 0.828] | 0.8035 | 0.2443 | 108 / 360 | 21 / 168 | 0.8523 |
| gpt-5.1 | `verifier_api_gpt-5.1_alltype_test_seed42_20261001_134120` | 0.7093 [0.682, 0.737] | 0.7050 | 0.4110 | 158 / 360 | 59 / 168 | 0.8295 |

- 이 test에서는 1차 A/B가 gpt-5.6-sol보다 accuracy가 높음(+0.110, +0.113). 그러나 다른 데이터셋 negative는 출처만 보고도 거를 수 있어 1차 verifier가 0/360을 수락한 반면, 같은 데이터셋 negative는 32–44%를 수락함.
- gpt-5.6-sol이 수락한 다른 데이터셋 negative 108개는 같은 단계가 62/99, 다른 단계가 46/261. 뜻이 거의 같은 유형 쌍이 많음: EIC operator → MathClean logic 5/5, EIC confusing formula → MathEDU wrong operation/concept 5/5, EIC referencing previous step value → MathEDU arithmetical 5/5, EIC calculation → MathEDU arithmetical 3/3. 무작위 전체 유형 negative에는 실제로는 맞는 라벨인 경우가 섞여 있어, 이 test의 1차 verifier 점수는 부풀려진 값으로 봐야 함.

- HF private 업로드(1차, 참고용): `WooYoungSeok/newman-verifier_half_a_seed42_20261001_051819-epoch-5`, `…half_b_seed42_20261001_070425-epoch-5`.

## N11. 계획 → 진행 중 — 데이터 v3 verifier (사용자 결정 2026-10-01)

- **데이터 (실행 확인, `data/prepared_v3/sft/meta.json`, 검사 모두 통과)**
  - 원본 풀이당 3행이다: positive, 같은 데이터셋 negative(`::neg`, v2와 바이트 단위로 같음), 다른 데이터셋·다른 단계 negative(`::neg_cross`).
  - 원본 풀이 수: half A 1,081 / half B 1,063 / test 528. 행 수: 3,243 / 3,189 / 1,584.
  - 두 번째 negative의 단위 우선 배정: 26 / 19 / 12건. MathEDU Measurement error가 negative로 들어간 수: 19 / 14 / 9.
  - 형식 검사 실패 0.
- **학습 (계획)**: `configs/verifier_half_{a,b}_v3.yaml`. v2와 같은 하이퍼파라미터(lr 1e-5, 5 epoch, batch 32), positive:negative 1:2를 가중치 없이 학습, 선택은 macro-F1 → negative false acceptance(v3 test 기준). `scripts/run_verifier_v2_v3_chain.sh`가 v2 종료 뒤 자동 시작.
- **평가 지표 수정**: `verifier_common.compute_metrics`는 negative가 둘이면 마지막 것만 쳐서 pair accuracy를 계산한다. `newman.metrics.basic_metrics`가 이를 원본 풀이의 모든 행이 맞은 비율로 바로잡는다. negative가 1개인 데이터에서는 기존 값·CI와 같음을 저장된 예측으로 확인했다.
- **API (실행 확인, v3 test 1,584행)**: 2차(v2) best와 v3 best는 결과가 나오면 이 표에 추가한다.

| verifier | run | accuracy | macro-F1 | neg. false acceptance | invalid |
|---|---|---|---|---|---|
| gpt-5.6-sol | `verifier_api_gpt-5.6-sol_v3_test_seed42_20261001_142734` | 0.8258 | 0.8131 | 0.1856 | 0 |
| gpt-5.1 | `verifier_api_gpt-5.1_v3_test_seed42_20261001_142734` | 0.6237 | 0.6201 | 0.4593 | 0 |

- **1차 checkpoint 삭제**: 사용자 지시로 `_superseded/verifier_half_{a,b}_*`의 epoch_checkpoints(70 + 76 GiB)를 삭제했다. best(epoch-5)는 HF private에 있고, 기록은 `<run>/checkpoints_deleted.json`.

### N11-1. 실행 확인 — A 3차 (`verifier_half_a_v3_seed42_20261001_171232`, 17:12–19:47, 평가 20:10)

#### verifier_half_a_v3_seed42_20261001_171232 (실행 확인)

| 항목 | 값 |
|---|---|
| run / W&B | `verifier_half_a_v3_seed42_20261001_171232` / tutee_error_newman_verifier |
| 역할 / half | reward / A |
| backbone | `Qwen/Qwen2.5-Math-7B-Instruct` |
| 데이터 | `newman_experiment/data/prepared_v3/sft/half_a.jsonl` sha256 `e20634c56316`, 3243 rows / 1081 anchors, mapping verified True |
| 학습 | 5 epoch, lr 1e-05, wd 0.01, warmup 0.1, linear, batch 8x4x1 = 32, max grad norm 1.0, bf16 True, max len 4096 |
| optimizer (실제) | accelerate.utils.deepspeed.DeepSpeedOptimizerWrapper > deepspeed.runtime.zero.stage_1_and_2.DeepSpeedZeroOptimizer > deepspeed.ops.adam.cpu_adam.DeepSpeedCPUAdam {'lr': 0.0, 'betas': [0.9, 0.999], 'eps': 1e-08, 'weight_decay': 0.01} |
| 저장 | snapshots epoch-1 (15.24 GB), epoch-2 (15.24 GB), epoch-3 (15.24 GB), epoch-4 (15.24 GB), epoch-5 (15.24 GB); resume checkpoints none |
| 프롬프트 / taxonomy | system `a2513fd9a228` user `e8d93eafa952` / `9b7cc7964664` |
| 승인 | taxonomy_definitions: approved, verifier_prompt: approved, verifier_backbones: approved |
| 버전 / git | torch 2.11.0+cu128, transformers 5.17.0, deepspeed 0.19.7 / `7c7c02879b73` dirty True |
| 시간 | 2026-10-01T17:13:00+09:00 → 2026-10-01T19:46:30+09:00 |

SFT test (`newman_experiment/data/prepared_v3/sft/test.jsonl` 1584 rows, sha256 `0aac89ffa7e3`), selection rule ['macro_f1:max', 'negative_false_acceptance:min'], best **epoch-5** — chosen on the test split (user rule 5): the chosen checkpoint's test score is optimistic

| checkpoint | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | test_loss |
|---|---|---|---|---|---|---|---|
| base | 0.0000 | 0.0000 | 0.0000 | 0.0028 | 0.0000 | 0.9981 | 5.3690 |
| epoch-1 | 0.7064 | 0.5343 | 0.9858 | 0.0142 | 0.1477 | 0.0000 | 0.1508 |
| epoch-2 | 0.7891 | 0.7365 | 0.9271 | 0.0729 | 0.5133 | 0.0000 | 0.1062 |
| epoch-3 | 0.8390 | 0.8136 | 0.9062 | 0.0938 | 0.7045 | 0.0000 | 0.0885 |
| epoch-4 | 0.8668 | 0.8467 | 0.9214 | 0.0786 | 0.7576 | 0.0000 | 0.0734 |
| epoch-5 | 0.8662 | 0.8508 | 0.8902 | 0.1098 | 0.8182 | 0.0000 | 0.0834 |

best epoch-5 (macro-F1 0.8508 > epoch-4 0.8467). 다른 test에서의 결과 (`test_eval_{v2_test,alltype_test}/epoch-5`):

| test | verifier | accuracy [95% CI] | macro-F1 | neg. false acceptance | 같은 데이터셋 neg. 수락 | 다른 데이터셋 neg. 수락 | pos. recall |
|---|---|---|---|---|---|---|---|
| v3 | A 3차 | 0.8662 [0.846, 0.885] | 0.8508 | 0.1098 | 0.220 | 0.000 | 0.8182 |
| v3 | gpt-5.6-sol | 0.8258 | 0.8131 | 0.1856 | 0.203 | 0.169 | 0.8485 |
| v2 | A 3차 | 0.8011 [0.772, 0.830] | 0.8011 | 0.2159 | 0.216 | – | 0.8182 |
| v2 | A 2차 | 0.7528 | 0.7528 | 0.2633 | 0.263 | – | 0.7689 |
| v2 | gpt-5.6-sol | 0.8277 | 0.8276 | 0.1951 | 0.195 | – | 0.8504 |
| 1차 (all-type) | A 3차 | 0.8816 [0.860, 0.903] | 0.8812 | 0.0549 | 0.161 | 0.006 | 0.8182 |
| 1차 (all-type) | gpt-5.6-sol | 0.8040 | 0.8035 | 0.2443 | 0.125 | 0.300 | 0.8523 |

- v3 test에서 gpt-5.6-sol 대비 accuracy +0.040 [+0.018, +0.062], 틀린 negative 수락률은 −0.076.
- v2 test(같은 데이터셋 negative만)에서는 A 2차보다 +0.048 높지만 gpt-5.6-sol보다 −0.027 낮다.
- 다른 데이터셋 negative는 단계가 같아도 거의 다 거부한다(1차 test 0.006, gpt-5.6-sol 0.300). 뜻이 같은 다른 데이터셋 유형도 거부하므로 출처 단서를 쓰고 있을 가능성이 있다.


### N11-2. 실행 확인 — B 3차 (`verifier_half_b_v3_seed42_20261001_194709`, 19:47–22:33, 평가 22:46)

원래 서버의 run 폴더 대신 HF private repo `WooYoungSeok/newman-verifier_half_b_v3_seed42_20261001_194709-epoch-5`(snapshot `ddae4e08`)의 `newman_meta/`(run_meta.json, test_eval_summary.json)에서 옮겼다. 다른 test(v2, all-type) 교차 평가와 유형별 결과는 이 서버에 없다.


| 항목 | 값 |
|---|---|
| run / W&B | `verifier_half_b_v3_seed42_20261001_194709` / tutee_error_newman_verifier |
| 역할 / half | test / B |
| backbone | `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` |
| 데이터 | `newman_experiment/data/prepared_v3/sft/half_b.jsonl` sha256 `d803ed248315`, 3189 rows / 1063 anchors, mapping verified True |
| 학습 | 5 epoch, lr 1e-05, wd 0.01, warmup 0.1, linear, batch 8x4x1 = 32, max grad norm 1.0, bf16 True, max len 4096 |
| optimizer (실제) | accelerate.utils.deepspeed.DeepSpeedOptimizerWrapper > deepspeed.runtime.zero.stage_1_and_2.DeepSpeedZeroOptimizer > deepspeed.ops.adam.cpu_adam.DeepSpeedCPUAdam {'lr': 0.0, 'betas': [0.9, 0.999], 'eps': 1e-08, 'weight_decay': 0.01} |
| 저장 | snapshots epoch-1 (16.39 GB), epoch-2 (16.39 GB), epoch-3 (16.39 GB), epoch-4 (16.39 GB), epoch-5 (16.39 GB); resume checkpoints none |
| 프롬프트 / taxonomy | system `a2513fd9a228` user `e8d93eafa952` / `9b7cc7964664` |
| 승인 | taxonomy_definitions: approved, verifier_prompt: approved, verifier_backbones: approved |
| 버전 / git | torch 2.11.0+cu128, transformers 5.17.0, deepspeed 0.19.7 / `7c7c02879b73` dirty True |
| 시간 | 2026-10-01T19:47:47+09:00 → 2026-10-01T22:33:55+09:00 |

SFT test (`newman_experiment/data/prepared_v3/sft/test.jsonl` 1584 rows, sha256 `0aac89ffa7e3`), selection rule ['macro_f1:max', 'negative_false_acceptance:min'], best **epoch-5** — chosen on the test split (user rule 5): the chosen checkpoint's test score is optimistic

| checkpoint | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | test_loss |
|---|---|---|---|---|---|---|---|
| base | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 18.9044 |
| epoch-1 | 0.7102 | 0.5830 | 0.9470 | 0.0530 | 0.2367 | 0.0000 | 0.2479 |
| epoch-2 | 0.7424 | 0.7307 | 0.7131 | 0.2869 | 0.8011 | 0.0000 | 0.1713 |
| epoch-3 | 0.8049 | 0.7933 | 0.7812 | 0.2188 | 0.8523 | 0.0000 | 0.1396 |
| epoch-4 | 0.8535 | 0.8338 | 0.8987 | 0.1013 | 0.7633 | 0.0000 | 0.1450 |
| epoch-5 | 0.8580 | 0.8423 | 0.8797 | 0.1203 | 0.8144 | 0.0000 | 0.1948 |


## N12. 계획 — Student GRPO 시작 (2026-10-02, A100 80GB × 4, 드라이버 580)

| 항목 | 계획 값 |
|---|---|
| 보상 verifier A | `WooYoungSeok/newman-verifier_half_a_v3_seed42_20261001_171232-epoch-5` (v3 A best, SFT test macro-F1 0.8508) — 사용자 결정 2026-10-02 |
| 평가 verifier B | `WooYoungSeok/newman-verifier_half_b_v3_seed42_20261001_194709-epoch-5` (v3 B best, SFT test macro-F1 0.8423) — 사용자 결정 2026-10-02 |
| GPU 배치 | 학습 GPU 0–2 (8 × 3 × 2 = 48 풀이 = 6 조건/step), GPU 3에 rollout(0.50) + verifier A(0.35). 계획 배치 그대로 |
| step 수 (추정) | train 6,336 조건 / 6 = 1,056 step/epoch × **1 epoch** = 1,056 step/run (사용자 결정 2026-10-02, 처음 계획 2 epoch) |
| 저장 | snapshot + 재개 checkpoint **0.25 epoch마다**, 모두 보관 (run당 4 × 15 GB + 4 × 약 122 GB) |
| 평가 학생다움 judge | validation에서만 호출(student_likeness snapshot 선택), test는 호출 안 함(사람이 평가, aux = 0) |
| checkpoint 선택 | RL validation 704 조건 × 8 rollout에서 verifier B 기준 `reward_total_mean`(= main + 0.5 × aux + truncation의 rollout 평균) 최고 0.5 epoch snapshot |
| API baseline | gpt-5.6-sol, **조건당 1회**(사용자 결정 2026-10-02), 비교 지표 B joint success(오답 + B 2/2 aligned). 학습과 동시에 생성 |
| 남은 차단 | 승인 `answer_judge_prompt`, `student_likeness_prompt` (사용자와 재논의 중) |

### N12-1. 실행 확인 — smoke (`smoke_newman_diversity_seed42_20261002_112231`, 실제 보상 경로, 3 step)

| 항목 | 값 |
|---|---|
| 구성 | `configs/diversity.yaml` 그대로(7B policy, verifier A v3 epoch-5, gpt-5-nano low), `--max_steps 3 --report_to none`, snapshot·재개 저장은 끝 1회로 override |
| GPU | 학습 0–2(각 38–46 GiB), GPU 3 rollout + A 76 GiB. 48 풀이 = 6 조건/step |
| step 시간 | 55 / 40 / 50 s (`step_time` 37.2 / 39.0 / 51.8 s) |
| 답 채점 | correct 0.67–0.85, null 0, retry 0, 지연 2.8–3.8 s |
| verifier A | 오답 수락률 0 / 0.125 / 0.214, invalid 0 |
| 저장 실측 | snapshot 15.24 GB(16 s), 재개 checkpoint **121.86 GB**(설정 추정 114 GB) |
| API baseline | `outputs/api_baselines/gpt-5.6-sol`: 1,752 조건 × 1, truncated 0, 입력 635,968 / 출력 390,230 토큰, 11:22–11:24 |

### N12-2. 중단 run — `_aborted/newman_student_likeness_seed42_20261002_121157`

| 항목 | 값 |
|---|---|
| 기간 | 2026-10-02 12:13 → 15:23 (step 약 234 / 1,056, 첫 재개 checkpoint step 264 전이라 checkpoint 없음) |
| 이유 | gpt-5-nano 답 채점 요청 하나가 OpenAI에서 `invalid_prompt`(정책 위반 의심)로 거부됨. 재사용한 `tutee_rl` client가 모든 400을 치명 오류로 처리해 학습 전체가 멈춤. 거부된 풀이 원문은 그 step의 로그가 쓰이기 전이라 남지 않음 |
| 그때까지의 학습 지표 | 정답률 0.65–0.85 → 약 0.18, `groups/K_mean` 0.22 → 0.93, step 41–50 s |
| 조치 | 사용자 결정(2026-10-02): 거부되면 3회 재시도 후 판정 불가(−0.75), judge 쌍은 무승부, `rollouts/flagged.jsonl`에 기록. 같은 설정으로 새 이름의 run을 처음부터 다시 시작 |

### N12-3. 실행 확인 — API baseline 잠정 평가 (verifier **A** 사용, B 평가 전)

학습 중이라 B를 올릴 GPU가 없어, 학습용으로 떠 있는 verifier A 서버로 먼저 채점했다(`outputs/api_baselines_prelim_verifierA/test_eval`, `--override evaluation.verifier.*=A`). **A는 보상 verifier라 최종 평가값이 아니다**(파일 안 지표 이름은 `b_*`지만 실제 판정은 A). 오답률은 gpt-5-nano(low) 판정으로 최종값과 같다. RL test 1,752 조건 × 1, 질문 그룹 bootstrap 1000.

| 모델 | 생성 (입력 / 출력 토큰) | 오답률 [95% CI] | A 수락률 (오답 중) | **A 기준 success** (오답 + A 2/2) [95% CI] | 단계별 success (Comp. / Proc. / Read. / Transf.) |
|---|---|---|---|---|---|
| gpt-5.6-sol | 635,968 / 390,230 | 0.932 [0.920, 0.943] | 0.169 | 0.158 [0.141, 0.175] | 0.167 / 0.084 / 0.595 / 0.079 |
| gpt-5.1 | 635,968 / 321,748 (16:07–16:08) | 0.833 [0.816, 0.851] | 0.164 | 0.136 [0.120, 0.152] | 0.299 / 0.087 / 0.225 / 0.101 |

null 0 / 0.001, truncation 0, flagged 0. B 기준 최종값은 RL 학습이 끝나 GPU가 비면 같은 생성물로 다시 채점한다.

### N12-4. 실행 확인 — API baseline을 gpt-5.6-sol verifier로 채점 (사용자 요청 2026-10-02)

`scripts/score_generations_api_verifier.py`. N12-3과 같은 생성물·같은 gpt-5-nano 답 판정을 그대로 쓰고, 오답만 gpt-5.6-sol에 **학습한 verifier와 같은 system/user 메시지**로 보냄(`configs/verifier_common.yaml` api_verifier: reasoning 미전송, max_output_tokens 8000, 엄격 판정). 오답당 **2회 호출, 둘 다 aligned면 통과**(A/B 규칙과 같음). 결과 `outputs/api_baselines_verifier_gpt-5.6-sol/api_<model>/metrics.json`, 질문 그룹 bootstrap 1000.

| 생성 모델 | 오답률 | 오답 중 통과율 (sol / A) | **success: sol verifier** [95% CI] | success: A (N12-3) | 1회 호출 success (sol) | 단계별 success, sol (Comp. / Proc. / Read. / Transf.) | 사용량 (입력 / 출력) |
|---|---|---|---|---|---|---|---|
| gpt-5.6-sol | 0.932 | 0.965 / 0.169 | **0.899** [0.886, 0.912] | 0.158 | 0.904 | 0.864 / 0.923 / 0.950 / 0.868 | 1,398,574 / 134,238 |
| gpt-5.1 | 0.833 | 0.814 / 0.164 | **0.678** [0.659, 0.700] | 0.136 | 0.691 | 0.701 / 0.677 / 0.761 / 0.641 | 1,505,318 / 169,217 |

- invalid 0, flagged 0, 2회 판정 불일치 1.2% / 3.1%.
- A와 sol의 판정 (오답만, A 통과 / sol 통과): gpt-5.6-sol 생성물 A1/sol1 273, A0/sol1 1,302, A1/sol0 3, A0/sol0 54. gpt-5.1 생성물 222 / 965 / 17 / 255. A가 통과시킨 것은 거의 다 sol도 통과시키고, sol은 A가 거부한 것의 대부분을 통과시킴.
- A0/sol1 무작위 예시 2개(측정 오류 "30분 = 0.3시간", 계산 오류 "2500 × 1/10 = 200")는 눈으로 보기에 조건에 맞음. LaTeX 형식 여부로는 A 수락률 차이가 거의 없음(gpt-5.1 LaTeX 0.129 / plain 0.175).
- 해석 주의: sol은 자기 생성물을 0.965 통과시켜 gpt-5.1 생성물(0.814)보다 높음(자기 선호 가능성). 어느 verifier가 맞는지는 사람 검수 전에는 판단할 수 없음.

### N12-5. 진단 — verifier A가 데이터셋 문체를 단서로 씀 (2026-10-02, `newman_student_likeness_seed42_20261002_154536` step 약 580 시점)

- 학습 보상 정체: `reward/total_mean`은 step 150까지 −0.55 → 0으로 오른 뒤(대부분 정답률 0.77 → 0.1 감소) 0.0–0.13 사이에서 천천히 오름. A 수락률(오답 중) 0.11 → 약 0.15, `groups/K0_rate` 약 0.65.
- 유형별 rollout당 성공(A 기준, 최근 150 step): EIC unit conversion / calculation / confusing formula / operator / previous step 모두 0.000–0.004로 **처음부터 0**, MathEDU 다섯 유형 0.009–0.137, Stepwise·MathClean·EIC adding irrelevant 0.26–0.43.
- API baseline 오답(N12-3/4)에서도 같음: A 수락률 EIC operator / calculation / unit conversion / formula **0.000**(gpt-5.6-sol verifier 0.64–0.98).
- **확인 실험**: 같은 API 풀이 끝에 GSM8K/EIC 형식 줄 `#### <추출된 답>`만 붙여 A에 다시 보냄(오답만, 2회 모두 aligned):

| 목표 유형 | n | A 원래 | A + `####` |
|---|---|---|---|
| eic.calculation_error | 203 | 0.000 | 0.872 |
| eic.operator_error | 207 | 0.000 | 0.947 |
| eic.unit_conversion_error | 168 | 0.000 | 0.369 |
| eic.confusing_formula_error | 196 | 0.000 | 0.112 |
| mathedu.arithmetical_error | 203 | 0.025 | 0.000 |
| mathedu.wrong_mathematical_operation_concept | 181 | 0.006 | 0.000 |

- 해석: A 3차(v3)는 풀이의 문체가 목표 유형의 원본 데이터셋 문체와 맞는지를 크게 본다. v3 데이터의 "다른 데이터셋·다른 단계 negative"가 문체 불일치 → not_aligned를 가르친 것으로 보임(N11-1에서 다른 데이터셋 negative를 거의 다 거부한 것과 같은 현상). Student 출력에는 `####`가 0회(14,400 rollout)라 EIC 문체 유형은 보상을 거의 받지 못함. B 3차도 같은 데이터로 학습해 같은 문제가 있을 가능성이 높음(미확인, GPU가 비면 같은 실험).

### N12-6. 중단 — `newman_student_likeness_seed42_20261002_154536` (2026-10-02, 사용자 지시)

step 610 / 1,056에서 사용자 지시로 학습을 멈춤(N12-5의 verifier A 문체 단서 진단 뒤, Eedi distractor 보상 실험으로 전환). 남은 것: snapshot `epoch-0.25`, `epoch-0.50`, 재개 checkpoint `checkpoint-264`, `checkpoint-528`(모두 보관), rollouts step 0–609. 평가와 diversity run은 실행하지 않음.

---

# Distractor 보상 실험 (`distractor_rl/`, Eedi GRPO 변형, 2026-10-02 사용자 결정)

`rl/` 코드는 고치지 않고 `distractor_rl/scripts/_patch.py`가 Eedi `RewardOrchestrator` 자리에 `DistractorRewardOrchestrator`를 넣어 `rl/scripts/train.py`, `evaluate.py`를 그대로 실행한다. 설정은 `rl/configs/student_likeness.yaml`을 상속(`distractor_rl/configs/student_likeness.yaml`).

## D1. 계획

| 항목 | 값 |
|---|---|
| main reward | 정답 −0.75, 최종 답 판정 불가(null) −0.75, **오답이면서 조건의 target distractor와 같음 1.0**(verifier 불필요), 그 밖의 오답 + reward verifier 2/2 aligned **0.5**, 그 밖 0 |
| 보조항 | 0.5 × student-likeness, G = main > 0 (distractor 일치 + verifier 통과) |
| 답 채점 | Eedi 지시문 그대로(`rl/prompts/answer_judge_*.txt`), gpt-5-nano **reasoning low** |
| distractor 판정 | 오답일 때만 두 번째 gpt-5-nano 호출(low), target distractor(조건 misconception의 보기)만 제시: `distractor_rl/prompts/distractor_match_*.txt` (사용자 승인, sha256 `7d4ea6ee…` / `aeb97193…`) |
| 결정적 보정 | `_norm_answer` 기준으로 정답 문자열과 같으면 정답, target distractor와 같으면 일치(채점기보다 우선) |
| OpenAI 거부 | `invalid_prompt`는 3회 재시도 후 답 채점 → null(−0.75), distractor 판정 → 불일치, judge 쌍 → 무승부, `rollouts/flagged.jsonl` |
| 그 밖 | Eedi run과 같음: Qwen2.5-7B-Instruct, Eedi train 2,048 / test 481쌍, Student 지시문(보기 숨김), T 1.0, 2 epoch 682 step, 48 풀이/step, reward verifier half-A, test verifier half-B, best = test 평균 reward. snapshot 0.5 epoch, 재개 checkpoint 171 step마다 모두 보관 |
| target distractor 수 | 모든 쌍에 1개 이상 (train 1개 1,858 / 2개 164 / 3개 26) |

## D2. 설계 변경 이력 (smoke로 확인)

| smoke | 내용 |
|---|---|
| `smoke_distractor_seed42_20261003_003118` (한 번의 호출, 3 step) | 채점기에 target 보기를 함께 주자 정답 `150 m`을 "option C(1.5 m)와 다르다"며 오답 + 일치로 판정(정답에 +1). "정답 + 일치" 모순이 재시도를 부름(최대 5/6회) |
| `smoke_distractor_seed42_20261003_004733` (한 번의 호출 + 보정, 2 step) | 정답 문자열과 같은 답을 오답으로 판정 6/96, 이유는 모두 "target 보기와 맞지 않음". 한 번의 호출 방식 폐기 → 두 번 호출(A안, 사용자 승인) |
| `smoke_distractor_seed42_20261003_010822` (두 번 호출, 2 step) | 96 rollout: 정답 53, distractor 25(문자열 보정 20 + 채점기 5, 5건 모두 맞음), verifier 통과 17, 거부 1. 정답을 오답으로 판정 0, 재시도 0, 거부 0 |

## D3. 실행 확인 — `distractor_student_likeness_seed42_20261003_011448`

tmux `distractor`, `distractor_rl/scripts/run_pipeline.sh`(학습 → 자동 재개 → test 평가). W&B `tutee_error_distractor_rl/de0597b6`. 682 step, 첫 step 56 s(정답률 0.65, 오답 중 distractor 일치 0.71, 거부 0). 학습 2026-10-03 01:15 → 평가 종료 11:51, OpenAI 거부 0.

test (481쌍 × 8, verifier B, `test_eval/summary.json`, best = test 평균 reward → **epoch-2.0**, test에서 골라 낙관적):

| 모델 | 평균 reward | 정답률 | distractor 일치 (전체) | **distractor 일치 (오답 중)** | 그 밖 오답 + B 통과 | 오답 중 B 통과 | 성공(main > 0) |
|---|---|---|---|---|---|---|---|
| base | −0.032 | 0.583 | 0.204 | 0.490 | 0.205 | 0.978 | 0.409 |
| epoch-0.5 | 0.528 | 0.262 | 0.355 | 0.481 | 0.376 | 0.989 | 0.731 |
| epoch-1.0 | 0.604 | 0.214 | 0.359 | 0.458 | 0.422 | 0.992 | 0.781 |
| epoch-1.5 | 0.597 | 0.219 | 0.366 | 0.470 | 0.406 | 0.988 | 0.773 |
| **epoch-2.0** | 0.646 | 0.193 | 0.384 | 0.477 | 0.416 | 0.993 | 0.801 |

- 학습 reward는 step 75 무렵 약 0.6에 이른 뒤 0.55–0.67에서 정체. 오른 몫은 정답률 감소(0.58 → 0.19)에서 옴.
- **오답 중 distractor 일치율은 base 0.490 → 0.46–0.48로 늘지 않음**(학습 중에도 0.50 → 약 0.44). 전체 일치율이 0.20 → 0.38로 오른 것은 오답이 늘었기 때문. Eedi run(목표 보기 일치 24.7% → 21.2%)과 같은 양상.
- verifier B가 오답의 98–99%를 통과시켜, distractor가 아닌 오답도 거의 다 0.5를 받음. distractor 일치의 추가 보상은 +0.5뿐.

### D4. 분석 — 조건별 target distractor 일치 (test 481조건 × 8, 사용자 요청 2026-10-03)

| 모델 | 일치 / 전체 | 일치 / 오답 | 한 번도 못 맞힌 조건 (0/8) | 1회 이상 | 4회 이상 | 8/8 | 8개 모두 정답인 조건 |
|---|---|---|---|---|---|---|---|
| base | 0.204 | 0.490 | 280 | 201 | 96 | 29 | 139 |
| epoch-0.5 | 0.355 | 0.481 | 167 | 314 | 186 | 44 | 21 |
| epoch-1.0 | 0.359 | 0.458 | 145 | 336 | 187 | 44 | 8 |
| epoch-1.5 | 0.366 | 0.470 | 158 | 323 | 186 | 45 | 10 |
| epoch-2.0 | 0.384 | 0.477 | 149 | 332 | 198 | 49 | 7 |

- 조건당 일치 수(0–8) 분포: base 280/44/38/23/16/19/18/14/29, epoch-2.0 149/53/44/37/35/33/37/44/49.
- base → epoch-2.0 조건별: 0 → 1회 이상 144, 1회 이상 → 0 13, 둘 다 0 136. 늘어난 조건 253, 줄어든 조건 56, 같음 172.
- epoch-2.0에서 못 맞힌 149조건의 rollout: 그 밖 오답 + verifier 통과 792, 정답 390, 거부 7, null 3. 이 조건들에서 오답은 거의 다 같은 0.5를 받아 distractor 쪽 신호가 없음.
- 그림이 있는 문제(`![` 포함, 158조건)는 못 맞힌 비율 0.34, 오답 중 일치 0.431. 그림 없는 문제(323조건)는 0.29, 0.499. target 보기가 "None of these" 같은 문장인 10조건은 7개를 못 맞힘.

## D5. 계획 → 진행 중 — verifiable distractor 보상, verifier 없음 (사용자 결정 2026-10-03, `distractor_rl/configs/verifiable.yaml`)

| 항목 | 값 |
|---|---|
| main reward | **target distractor 일치 +1, 그 밖의 모든 응답(정답·다른 오답·추출 불가) −0.75**, truncation −0.5 |
| verifier | 사용하지 않음(서버도 띄우지 않음). 평가 단계에서 `rl/scripts/evaluate.py`가 서버 상태를 검사해서 B 서버를 띄우기만 하고 채점에는 쓰지 않음 |
| 보조항 | G = distractor 일치 풀이, \|G\| ≥ 2일 때 0.5 × student-likeness(gpt-5-nano low) + 0.25 × BLEU diversity |
| gpt-5-nano | ① 최종 답 **추출만**(정오답 판정 없음, `prompts/answer_extract_*.txt`, 사용자 승인) ② 추출된 답이 있으면 distractor 판정(승인된 지시문). 모두 reasoning low |
| 결정적 보정 | 정답 문자열과 같으면 판정 호출 없이 불일치, target distractor 문자열과 같으면 일치 |
| 속도 | 10초 안에 응답이 없으면 같은 요청을 한 번 더 보내 먼저 온 응답을 씀(`openai_client.hedge_after_s`, smoke에서 58.5초짜리 한 건이 step 전체를 붙잡은 것을 보고 넣음). rollout 서버 GPU 메모리 0.50 → 0.85 |
| OpenAI 거부 | 3회 재시도 후 추출 불가 / 불일치 / 무승부, `rollouts/flagged.jsonl` |
| 학습 | 그룹 8(16을 검토했다가 8 유지), step당 48 = 조건 6개, 2 epoch 682 step, 그 밖 Eedi run과 같음. snapshot 0.5 epoch, 재개 checkpoint 171 step, 모두 보관 |
| smoke | `smoke_verifiable_seed42_20261003_123006`(그룹 16, 2 step: 채점 66.8초 중 judge 대기 대부분), `smoke_verifiable_seed42_20261003_125025`(그룹 8 + 중복 전송, 3 step: step 38–41초, 채점 7–19초). 두 smoke 모두 가중치는 사용자 지시로 삭제 |
| run | `distractor_verifiable_seed42_20261003_130011`, W&B `tutee_error_distractor_rl/873ace3e`, 13:00 시작, step 41–42초(예상 약 8.7시간) |

### D6. checkpoint 정리 (사용자 지시 2026-10-03)

수렴하지 않은 run은 best 하나만 남김: `distractor_student_likeness_seed42_20261003_011448` → epoch-2.0(test best)만, `newman_student_likeness_seed42_20261002_154536` → 평가하지 않아 best가 없으므로 가장 많이 학습된 epoch-0.50만. 재개 checkpoint와 나머지 snapshot, smoke 가중치는 삭제(각 폴더 `checkpoints_deleted.json`). rollout·평가 기록은 보관.

### D7. 실행 확인 — distractor 1차 test를 gpt-5.6-sol verifier로 채점 (사용자 요청 2026-10-03)

`distractor_rl/scripts/score_api_verifier.py`, 결과 `<run>/test_eval_api_verifier_gpt-5.6-sol/{base,epoch-2.0}/metrics.json`. test rollout의 gpt-5-nano 오답 판정을 그대로 쓰고, 오답만 gpt-5.6-sol에 Eedi verifier(half-A/B)와 같은 system/user 메시지(`verifier_sft/prompts/system.txt`, `user.txt`: 질문·풀이·misconception 설명)로 보냄. 오답당 2회, 둘 다 aligned면 통과. reasoning 미전송, max_output_tokens 8000, invalid 0. 질문 그룹 bootstrap 1000.

| 모델 | 오답률 | 오답 중 sol 통과 [95% CI] | **sol success** (오답 + sol 2/2) [95% CI] | 1회 호출 success | 오답 중 B 통과 | B success | 오답 중 sol 통과: distractor 일치 / 불일치 | sol·B 불일치 (오답 중) | 사용량 (입력 / 출력) |
|---|---|---|---|---|---|---|---|---|---|
| base | 0.417 | 0.783 [0.739, 0.824] | **0.327** [0.287, 0.368] | 0.332 | 0.978 | 0.408 | 0.966 / 0.608 | 0.199 | 1,037,164 / 135,080 |
| epoch-2.0 | 0.806 | 0.808 [0.782, 0.834] | **0.651** [0.618, 0.683] | 0.665 | 0.993 | 0.800 | 0.960 / 0.669 | 0.189 | 2,369,792 / 279,746 |

- gpt-5.6-sol은 B보다 엄격함(오답 중 통과 0.78–0.81 vs 0.98–0.99). distractor와 일치한 오답은 96–97% 통과, 일치하지 않는 오답은 61–67%만 통과.
- sol 기준으로도 success는 base 0.327 → epoch-2.0 0.651로 두 배. 오답 중 통과율은 0.783 → 0.808로 거의 같아, 늘어난 몫은 대부분 오답이 늘어난 데서 옴.
