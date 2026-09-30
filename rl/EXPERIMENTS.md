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
- 설정은 위와 같고 aux만 BLEU diversity. 2026-09-30 03:00 학습 시작. 결과는 평가 후 추가.

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

## 6. 중단된 run (`outputs/_aborted/`)

| 폴더 | 중단 이유 |
|---|---|
| `diversity_seed42_student_prompt_v1` | Student 지시문 v1의 해설형 오답 (step 4) |
| `student_likeness_seed42_oom_start` | 비교 스크립트가 남긴 vLLM 프로세스로 GPU 0 메모리 부족 (시작 직후) |
| `student_likeness_seed42_api_connection_errors` | OpenAI 연결 오류 누적으로 3회 중단 (step 48) |
| `student_likeness_seed42_qwen_sampling_accum8` | Qwen 기본 샘플링 + step당 192 풀이: 학습 신호 부족 (step 43) |
| `student_likeness_seed42_20260929_104900_stopped_for_tmux` | tmux로 재시작 (step 22) |
| `student_likeness_seed42_20260929_111558_none_answer_rule` | 실제 답 "none"을 스키마 위반으로 거부한 버그 (step 23) |
