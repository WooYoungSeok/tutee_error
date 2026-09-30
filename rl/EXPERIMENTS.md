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
| negative (2026-10-01 재생성) | 16개 유형 중 자기 유형 제외 균등 추출 + 허용 목록 문제에서는 단위 유형 우선(자기 라벨이 단위 유형이면 제외). 우선 배정 39 / 31 / 16건. same-stage 270 / 269 / 126, other-dataset 763 / 754 / 360 (half A / half B / test), 후보 없음 0. 단위 외 유형은 half A에서 유형당 62–88건 |
| 단위 유형 negative | EIC Unit Conversion Error 20 / 14 / 8 (positive 73 / 65 / 32), MathEDU Measurement error 21 / 17 / 8 (positive 5 / 4 / 2). negative 없는 유형 0 |
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

## N7. 중단된 run

없음.
