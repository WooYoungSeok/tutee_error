# Newman 실험 결정 기록

[`experiment_plan.md`](experiment_plan.md)(계획서 원문)보다 이 문서가 우선한다. 사용자 결정은 날짜와 함께 추가만 하고 지우지 않는다.
구현 기본값은 사용자 확인 전까지 "구현 기본값"으로 둔다. 설정·결과 수치는 `../../rl/EXPERIMENTS.md`(Newman 절)에 기록한다.

## 사용자 결정

| 날짜 | 항목 | 결정 | 반영 위치 |
|---|---|---|---|
| 2026-09-30 | 작업 규칙 1–5 | 계획서 "작업 규칙" 절 그대로 (단, 아래 RL validation 결정이 규칙 5를 RL에 한해 바꿈) | `AGENTS.md` |
| 2026-09-30 | Newman 매핑 | 워크북 `Newman 재분류` D열(영석 분류): 채택 16 / 제외 10, 원본 유형 보존 | `configs/taxonomy.yaml` |
| 2026-09-30 | 오류 유형 이름·정의 | 워크북 A열(라벨명)·B열(라벨 설명) 그대로. Stepwise 두 유형은 정의가 없어 **정의 줄을 생략**(라벨명만) | `configs/taxonomy.yaml`, `verifier_format.render_condition` |
| 2026-09-30 | verifier 역할 | A = train half A → RL 보상, B = train half B → test 평가, 각자 공개 backbone에서 별도 SFT | `configs/verifier_half_{a,b}.yaml` |
| 2026-09-30 | A/B backbone | `verifier_sft`와 같게: A `Qwen/Qwen2.5-Math-7B-Instruct`, B `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` (승인 기록됨) | `configs/approvals.yaml` |
| 2026-09-30 | negative | 같은 Q/S에 다른 채택 유형 E', N' = mapping(E'), 원본당 positive 1 + negative 1, `random.Random(42)` | `src/newman/negatives.py` |
| 2026-10-01 | negative 후보 | **16개 채택 유형 전체에서 자기 유형만 빼고 균등 추출(데이터셋 무관)**. llm_tutee_tutor `finetuning/train_new_label*.py`, `reward_model/train_04*.py`와 같은 방식이며, 계획서 4.3의 "같은 데이터셋" 규칙을 대체. 단위 두 유형 제한은 유지 | `configs/data.yaml` negatives, `negatives.py` |
| 2026-09-30 | 단위 유형 제한 | Measurement error, Unit Conversion Error는 단위 변환 허용 목록 True인 질문에만 (SFT negative, RL 조건) | `src/newman/unit_eligibility.py` |
| 2026-09-30 | 단위 허용 목록 | llm_tutee_tutor GSM8K `UNIT_CONV_RAW` 재사용 | `data/unit_conversion_allowlist_gsm8k.json` |
| 2026-09-30 | 다중 라벨 풀이 | 같은 학생 풀이에 오류 라벨이 둘 이상이면 그 풀이의 사례 전부 제외. pool 밖 원자료 라벨(Stepwise "None of the above" 등)도 센다 | `src/newman/sources.py`, `configs/data.yaml` filters |
| 2026-09-30 | gpt-5-nano | 답 채점·학생다움 judge 모두 reasoning effort low | `configs/rl_common.yaml` |
| 2026-09-30 | SFT 분할 | 전역 문제 그룹 train:test 8:2, SFT validation 없음, 모든 checkpoint 보관, SFT test에서 best | `configs/data.yaml`, `configs/verifier_common.yaml` |
| 2026-09-30 | SFT checkpoint 선택 | macro-F1 최대 → negative false acceptance 최소 → test loss 최소 (계획서 제안) | `configs/verifier_common.yaml` evaluation.selection_rule |
| 2026-10-01 | 데이터 v3 (negative 2개) | 2차(v2) 학습·평가 뒤 이어서 v3로도 A/B를 학습한다. 원본 풀이당 positive 1 + negative 2: ① 같은 데이터셋의 다른 유형(같은 단계 허용, v2와 같은 추출) ② **다른 데이터셋이면서 Newman 단계도 다른 유형**. 두 negative 모두 단위 유형 우선(허용 목록 문제). positive:negative = 1:2를 가중치 없이 그대로 학습, 하이퍼파라미터·선택 규칙은 v2와 같음 | `configs/data_v3.yaml`, `configs/verifier_half_{a,b}_v3.yaml`, `data/prepared_v3/` |
| 2026-10-01 | 1차 checkpoint 삭제 | 1차(폐기) A/B의 epoch snapshot 1–5를 로컬에서 삭제(디스크 확보). best(epoch-5)는 HF private에 있음. 평가 결과·메타데이터는 보관, 기록 `<run>/checkpoints_deleted.json` | 사용자 지시 |
| 2026-10-01 | verifier HF 업로드 | 학습을 마친 verifier의 best checkpoint는 Hugging Face **private** repo `WooYoungSeok/newman-<run>-<checkpoint>`에 올린다(`scripts/upload_verifier_hf.py`, 기록 `<run>/hf_upload_<checkpoint>.json`). 폐기된 1차 A/B도 참고용으로 올림 | 사용자 지시 |
| 2026-10-01 | API verifier 비교 | gpt-5.6-sol, gpt-5.1을 zero-shot verifier로 SFT test 쌍(1,056행)에서 평가해 A/B best와 비교. **지시문은 학습한 verifier와 동일**: 같은 `build_messages`의 system/user 메시지를 같은 역할로 그대로 보냄(`instructions` 필드나 추가 문구 없음, 행마다 메시지 해시 대조). 같은 엄격 판정. reasoning 미전송, max_output_tokens 8000(Student API baseline 결정과 같음), 행당 1회 | `configs/verifier_common.yaml` api_verifier, `scripts/eval_verifier_api.py`, `scripts/compare_verifiers.py` |
| 2026-10-01 | negative 후보 되돌림 | **같은 원본 데이터셋 안의 다른 유형으로 되돌림(계획서 4.3)**. 전체 16개 유형에서 뽑았더니 A/B 모두 다른 데이터셋 negative는 0/360만 수락했지만 같은 데이터셋 negative는 32–44% 수락해, 오류가 아니라 라벨의 출처를 배웠다. 그때의 A/B run은 `outputs/_superseded/`에 보관 | `configs/data.yaml` negatives.candidates: same_dataset |
| 2026-10-01 | 단위 유형 negative 우선 | 단위 변환 허용 목록 문제(GSM8K와 연결된 EIC-GSM8K·Stepwise 질문)에서는 negative를 **단위 두 유형(Unit Conversion Error, Measurement error) 중에서만** 균등 추출. 자기 라벨이 단위 유형인 풀이는 제외(다른 단위 유형은 뜻이 거의 같아 거짓 negative가 되므로 균등 추출 유지) | `configs/data.yaml` negatives.unit_priority, `negatives.unit_priority` |
| 2026-10-01 | 단계 설명(프롬프트) | Student·verifier 프롬프트의 단계 부분에 Newman's Error Analysis 개요(Newman 1977, 1983; White 2009 p. 251: 순서대로 넘어야 하는 hurdle, 처음 무너진 단계에 오류를 둠)를 넣고("네 단계 중 하나"라는 문장은 baseline도 같은 프롬프트를 쓰므로 넣지 않음), 4개 단계 정의를 Newman의 hurdle·인터뷰 질문 기반으로 다시 씀(초안, 승인 대기) | `configs/taxonomy.yaml` framework·stages, `prompts/verifier_user.txt`, `prompts/student.txt` |
| 2026-10-01 | Student 지시 문장 | "주된 오류가 지정된 단계에서 일어나고 지정된 유형에 맞는 틀린 풀이" → "At the specified problem-solving stage, write an incorrect solution that matches the specified error type." | `prompts/student.txt` |
| 2026-10-01 | 승인 | NEA 개요·단계 정의·워크북 이름/정의(taxonomy), verifier 프롬프트, Student 프롬프트를 "이대로 확정" → `approve.py`로 해시 기록 | `configs/approvals.yaml` |
| 2026-10-01 | SFT checkpoint 선택 수정 | **test loss 제외**: macro-F1 최대 → negative false acceptance 최소, 그래도 같으면 앞 epoch. test loss는 보고만 | 같은 위치 |
| 2026-09-30 | RL 분할 | 전역 train을 RL train/validation **90:10**, 전역 test = RL test. GSM8K 원본 train+test를 모두 풀로 사용 | `configs/data.yaml` rl_data |
| 2026-09-30 | RL 조건 | 질문당 1조건, 16개 유형 균형(단계 비율은 Reading·Comprehension 각 약 13%, 나머지 각 약 37%) | `configs/data.yaml` rl_data |
| 2026-09-30 | RL checkpoint 선택 | RL validation에서 **verifier B 기준 평균 training reward**(`reward_total_mean`)가 최고인 0.5 epoch snapshot | `configs/rl_common.yaml` evaluation |
| 2026-09-30 | API baseline | RL Student와 성능을 비교할 모델 = `gpt-5.6-sol`, reasoning effort 미전송(모델 기본), max_output_tokens 8000, 조건당 8회 (학생다움 judge는 계속 gpt-5-nano low) | `configs/rl_common.yaml` api_baselines |
| 2026-09-30 | 학생다움 직접 비교 | 같은 조건·같은 rollout 번호 k(같은 seed)의 두 출력이 모두 B 통과일 때만 비교 | `configs/rl_common.yaml` likeness_comparison |
| 2026-09-30 | 브랜치 | SFT/RL 모두 `rl-grpo` 한 브랜치 (이름은 이전 프로젝트에서 이어받음, 기술적 필수는 아님) | `AGENTS.md` git 절 |
| 2026-09-30 | 서버 | 이 서버(A100 × 2)에서는 실행하지 않고 서버를 옮겨 SFT·RL을 이어서 진행 | `AGENTS.md` |
| 2026-10-01 | 재개 checkpoint | 새 서버 디스크 2 TiB. RL 재개 checkpoint는 **0.5 epoch마다(snapshot과 같은 시점) 모두 보관**, run당 4개 × 약 114 GB. 전체 예상 약 1.3 TB | `configs/rl_common.yaml` training.resume_save_every_epochs |

## 구현 기본값 (결과 의미 불변, 사용자 확인 대기)

| 항목 | 기본값 | 이유 |
|---|---|---|
| RL validation 추출 범위 | SFT 풀이가 없는 GSM8K 전용 train 그룹에서만 뽑음(전체 RL train의 10%) | verifier A/B가 학습한 질문이 validation에 들어가지 않게 |
| C 프롬프트 개발 문제 그룹 | train 고정 (v2 관행) | 설명 프롬프트를 만들며 본 문제를 test에서 제외 |
| judge 예시 문제(MathEDU 13427, 8584) | train half A 고정 (계획서 8.4 제안) | test에 들어가지 않게 |
| 층별 독립 난수 | 분할·절반·validation을 층마다 따로 seed | 한 층의 변화가 다른 층의 배정을 바꾸지 않게 |
| verifier SFT 재개 checkpoint | 저장하지 않음(epoch snapshot만), 설정으로 켤 수 있음 | v2 train+validation 절반 관행, 저장 공간 |
| verifier 호출 반복 벌점, TRL IS 키 | rep 1.0 명시, IS 설정 명시 + 가중치 0 비율 지표 추가 | 계획서 "명시" 요구 |

## 열린 결정

| 항목 | 상태 |
|---|---|
| 승인: 답 채점 프롬프트 재사용(`../rl/prompts/answer_judge_*.txt`) + GSM8K 답 형식 계약(`prompts/gsm8k_answer_contract.txt`), 학생다움 judge 재사용(`../rl/prompts/student_likeness_*.txt` + MathEDU 예시 2개). **RL 전에 필요**, verifier SFT에는 불필요 | `python scripts/approve.py --status` |
| C 생성 이력이 없는 원본 포함 여부 | 기존 ok-only 유지 중 |
| 다른 GPU 수 | effective batch(SFT 32, RL 48)를 유지할 per-device/accumulation 조합은 사용자와 확정 |
