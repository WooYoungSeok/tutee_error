# 엄격한 verifier — 같은 문제 대조 사례 (strict_contrast_v1)

목표: `{Q, S, C}`에서 **C가 S에 실제로 있는 오류를 묘사하는지**를 판정하도록, 같은 문제 안에서 풀이와 설명을 교차한
사례를 gpt-5.6-sol로 `aligned / not_aligned / unclear` 검수해 기존 verifier를 이어서 학습한다. Verifier 출력 형식
(`aligned` / `not_aligned`)과 SFT 방식은 그대로다. `unclear`는 학습에서 제외하는 검수용 상태다.

배경: v2의 `make_pairs()`는 negative를 "다른 원본 라벨 **이고** 다른 문제 그룹"에서만 뽑아, 같은 문제의 다른 오류 설명은
학습·평가 어디에도 없었다.

## 연구자 결정 (2026-09-29)

| 항목 | 결정 |
| --- | --- |
| 검수 지시문 | `prompts/audit_system.txt`, `audit_user.txt` — 20행 파일럿(`outputs/strict_contrast_v1/audit/pilot/pilot_review.md`)을 보고 확정 |
| 검수 모델 | gpt-5.6-sol, reasoning effort 모델 기본값, structured output. 검수 모델에는 Q·S·C만 준다(설명 출처·원본 라벨 비공개) |
| 검수 범위 | 후보 1,807행 전부 (원래 행 포함 — 검수 모델 대조군) |
| 사람 확인 | 없음. 파일럿으로 지시문을 확정한 뒤 sol 판정을 라벨로 그대로 쓴다 |
| 학습 방식 | 기존 verifier에서 **이어서 학습**. negative는 검수된 같은 문제 `not_aligned` 행만(다른 문제 negative 없음), positive도 검수된 행만(풀이가 2개 이상인 문제의 원래 행 + 교차 `aligned` 행) |
| 학습 설정 | 학습률 5e-6, 3 epoch, 매 epoch 저장, validation 없음. 나머지는 v2 절반 A와 같음 |
| 대상 | halfA (`WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2-trval-halfA`, 절반 A 행) · 전체 v2 (`WooYoungSeok/qwen2.5-math-7b-descriptive-verifier-v2`, 절반 A+B 행) |

## 파이프라인

| 단계 | 파일 | 결과 |
| --- | --- | --- |
| 1. 후보 | `build_contrast_candidates.py`, `config/strict_contrast_v1.json` | `data/strict_contrast_v1/candidates_v2_same_question.jsonl` — 1,807행, 308개 문제 그룹 (EIC 1,696 · Stepwise 72 · MathEdu 39). 원본 라벨이 같아도 포함 |
| 2. 검수 | `audit_contrast.py` | `outputs/strict_contrast_v1/audit/audits.jsonl`, `audit_summary.md` (API 원문은 git 제외) |
| 3. 학습·평가 파일 | `build_contrast_sft.py` | `data/strict_contrast_v1_{halfA,full}_cont/` — `train`, `contrast_test`, `test`(v2), `test_augmented` |
| 4. 학습·평가 | `run_strict_contrast_v1.sh <config>` | `outputs/`, `reports/strict_contrast_v1_{halfA,full}_cont/`, wandb `tutee_error_verifier` |

같은 문제 그룹은 한 split·한 절반에만 있으므로 교차 행이 A/B 독립성과 test 분리를 깨지 않는다(점검 통과).

## 검수 결과 (1,807행)

| 행 종류 | 행 수 | aligned | not_aligned | unclear |
| --- | --- | --- | --- | --- |
| 원래 행 (풀이 + 자기 설명) | 725 | 717 (99%) | 8 (1%) | 0 |
| 교차 행, 원본 라벨 같음 | 332 | 286 (86%) | 46 (14%) | 0 |
| 교차 행, 원본 라벨 다름 | 750 | 112 (15%) | 637 (85%) | 1 |

교차 행을 원본 라벨로 자동 판정했다면 약 15%가 틀린 라벨이 된다. 한 행에서 sol이 NUL 문자를 반복하다 잘려
(`max_output_tokens`) 재호출로 해결했다.

## 학습·평가 데이터

| 파일 | 행 | 구성 |
| --- | --- | --- |
| halfA `train` | 691 (127 문제) | aligned 416 · not_aligned 275, 2×2 대조 묶음 117 |
| 전체 `train` | 1,604 (276 문제) | aligned 976 · not_aligned 628, 2×2 묶음 264 |
| `contrast_test` | 202 (32 문제) | test split 검수 행: aligned 139 · not_aligned 63 |
| `test_augmented` | 750 | v2 test 688행 그대로 + test split 같은 문제 `not_aligned` 교차 행 62 (23 문제). `row_source`로 종류 구분 |

v2 test의 한 positive(`eic:99e611036a83e97e`)는 sol이 `not_aligned`로 판정했지만 v2 행은 바꾸지 않았다.

## 결과 — `test_augmented` (750행)

| 모델 | 정확도 [95% 구간] | 같은 문제 negative 수용 (/62) | 다른 문제 negative 수용 (/344) | positive 거부 (/344) | 오답 |
| --- | --- | --- | --- | --- | --- |
| 학습 전 halfA | 0.907 [0.878, 0.936] | 79.0% (49) | 3.8% (13) | 2.3% (8) | 70 |
| halfA epoch 1 | 0.541 | 0% (0) | 0% (0) | 100% (344) | 344 |
| halfA epoch 2 | 0.840 | 17.7% (11) | 0.6% (2) | 31.1% (107) | 120 |
| halfA epoch 3 | 0.909 [0.888, 0.930] | 29.0% (18) | 2.0% (7) | 12.5% (43) | 68 |
| 학습 전 전체 v2 | 0.913 [0.885, 0.941] | 75.8% (47) | 3.2% (11) | 2.0% (7) | 65 |
| 전체 v2 epoch 1 | 0.915 [0.892, 0.936] | 33.9% (21) | 0.3% (1) | 12.2% (42) | 64 |
| 전체 v2 epoch 2 | 0.911 [0.890, 0.931] | 27.4% (17) | 1.5% (5) | 13.1% (45) | 67 |
| 전체 v2 epoch 3 | 0.915 [0.894, 0.935] | 27.4% (17) | 1.7% (6) | 11.9% (41) | 64 |
| gpt-5.6-sol | 0.961 [0.948, 0.974] | 8.1% (5)* | 5.8% (20) | 1.2% (4) | 29 |

\* 같은 문제 negative 62행의 정답은 sol 검수 판정이므로 sol에게 유리하다. sol이 받아들인 5행 중 4행은 원본 라벨이 같은
세부 오류 구분 행이다. 구간은 문제 그룹 bootstrap. epoch를 test로 고르면 그 점수는 낙관적이다. 평가는 greedy다
(RL 보상은 샘플 2개 모두 aligned).

- 기존 방식 데이터로만 학습한 verifier는 같은 문제의 다른 설명을 76~79% 받아들인다. 학습 데이터를 두 배로 늘린 전체 v2도 같다.
- 이어서 학습하면 그 수용이 약 1/3로 줄지만(49→18, 47→17), v2 positive 거부가 2% → 12% 수준으로 늘어 전체 정확도는 거의 같다.
  늘어난 거부는 대조 학습 데이터에 거의 없는 MathClean·MathEdu·Stepwise에 몰린다(전체 v2 epoch 3: EIC 3.5%, MathClean 21.7%,
  MathEdu 19.8%, Stepwise 19.5%). 대조 사례를 691 → 1,604행으로 늘려도 이 부작용은 줄지 않았다.
- halfA는 epoch 1에서 전부 `not_aligned`로 무너졌다가 회복했고, 전체 v2는 무너지지 않았다.
- 보고서: `reports/strict_contrast_v1_*_cont/verifier_results{,_contrast_test,_test_augmented}.md`,
  `subset_same_question_negatives.md` (62행만), `eval_gpt-5.6-sol_test_augmented.md`.

## 다음 후보 (미결정)

- 기존 데이터(특히 MathClean·MathEdu·Stepwise의 positive와 다른 문제 negative)를 섞어 positive 거부 부작용을 줄인다.
- Eedi 형제 misconception 보충 (아래, 원본 파일을 받으면 생성 방식 승인 요청).
- 같은 문제 negative 평가 라벨을 sol과 독립적으로 확정(사람 또는 다른 모델).

### Eedi 형제 misconception 보충 — 초안, 연구자 검수 전

필요 입력: `rl/data/raw/train_model_inputs.jsonl` + (`train_privileged_annotations.jsonl` 또는 `all_judgements.csv`).

| 항목 | 초안 |
| --- | --- |
| 형제 misconception | 같은 `QuestionId`의 다른 `MisconceptionId` 행의 설명. misconception이 2개 이상인 문제만 사용 |
| 풀이 생성 모델 | RL 학습 전 Student `Qwen/Qwen2.5-7B-Instruct` (대안: RL 학습된 checkpoint) |
| Student 지시문 | RL과 같은 `rl/prompts/student.txt` (v2) |
| 샘플링 | RL과 같은 Qwen generation_config (T 0.7, top_p 0.8, top_k 20, repetition penalty 1.05), max 1024 토큰, (문제, 목표 misconception)당 2개 |
| 최종 답 추출·정오답 판정 | RL 보상과 같은 gpt-5-nano + `rl/prompts/answer_judge_*`. `incorrect`만 남기고 `correct`·`null`·잘린 생성은 버린다 |
| 후보 행 | 남은 풀이 S × {목표 설명 C_a, 모든 형제 C_b}. C_a도 검수한다 |
| split | RL과 같은 문제 그룹 split. RL-train 그룹은 문제 그룹 단위로 A/B에 먼저 배정, RL-test 그룹은 verifier 학습에 쓰지 않고 대조 평가에만 쓴다 |
