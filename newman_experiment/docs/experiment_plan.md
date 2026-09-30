<!--
원문 보존본: 사용자가 2026-09-30 대화에 첨부한 `newman_error_generator_experiment_plan.md`를 그대로 옮겼다.
이후 사용자 결정이 이 문서와 다르면 docs/decisions.md가 우선한다
(예: RL은 train을 train/validation 90:10으로 나누고 validation에서 checkpoint를 고른다).
-->

# Newman 단계와 원본 오류 유형을 조건으로 사용하는 수학 오류 생성기 실험 코드 계획서

작성일: 2026-09-30  
상태: 구현 전 계획서, 2026-09-30 추가 지시 반영본. ‘확인’은 원자료/코드에서 확인한 내용, ‘확정’은 사용자 지시, ‘제안’은 승인 전 설계 선택을 뜻한다.

이번 갱신에서 확정한 사항: 최신 파일의 **영석 분류**로 재매핑, **half-A 보상 RM / half-B 평가 verifier 별도 SFT**, **다른 원본 오류 유형을 붙이는 binary negative**, **단위 관련 두 유형의 문제별 배정 제한**, **GSM8K의 기존 단위 변환 허용 목록 재사용**, **gpt-5-nano reasoning effort=low**. 이전 초안의 목표 조건을 숨기는 다중 분류 RM과 OTHER_ERROR 추가안은 채택하지 않는다.

## 작업 규칙 — 사용자 확정 사항

이 절은 2026-09-30 사용자가 전달한 작업 방식이며, 아래의 미확정 설계 제안보다 우선한다. 다음 Claude 세션도 이 규칙을 그대로 적용한다.

1. **연구 설계는 먼저 사용자와 확정한다.** API를 통한 최종 답 추출, Student/answer judge/student-likeness judge 지시문, RM 목표와 출력 계약, reward와 loss 수식, 계획서에서 열어 둔 sampling과 batch 설정을 임의로 결정하지 않는다. 기존 대화에서 이미 확정된 항목은 그 결정을 유지하고 변경안만 논의한다. 환경 설정, 실행 스크립트, mock test, 결과 의미를 바꾸지 않는 속도 개선은 별도 확인 없이 진행할 수 있다. 속도 개선이 sampling 분포나 effective batch를 바꾸면 연구 설계 변경으로 다룬다.
2. **설정과 결과를 `rl/EXPERIMENTS.md`에 기록한다.** 학습 또는 test 설정이 바뀔 때마다 실행된 run의 `run_meta.json`, `generation_meta.json`, `metrics.json`에서 값을 읽어 기록한다. 기억이나 config 파일의 의도만으로 실제 적용값을 적지 않는다. 결과, 결정 이력, 중단 run 및 중단 이유도 남긴다. 실행 전 값은 ‘계획’, 실행 후 값은 ‘실행 확인’으로 구분한다. 신규 RM 학습도 동일한 metadata 파일명을 출력하도록 설계한다.
3. **출력 폴더와 W&B run 이름을 일치시킨다.** 기본 형식은 `<experiment>_seed42_<YYYYmmdd_HHMMSS>`다. 시각은 Asia/Seoul 기준으로 생성하고 metadata에 timezone을 명시하는 안이다. 동일 실행의 재개는 기존 run 이름을 사용하며, 별도 설정의 새 실험은 새 timestamp를 사용한다.
4. **Git 갱신은 전체 명령 블록으로 전달한다.** `add → status 확인 → commit → push → GitHub의 새 PR 생성 → merge`를 생략 없이 제시한다. merge 뒤에도 `rl-grpo` 브랜치에 머물며 `git fetch origin && git merge origin/main`으로 동기화한다. 브랜치를 바꾸거나 자동 삭제하지 않는다. 실제 변경 파일, PR 설명, 검증 결과가 준비된 뒤 작업 범위에 맞는 명령을 제공한다. 이번 요청에서는 계획서만 작성하며 commit/push/PR/merge를 실행하지 않는다.
5. **train:test=8:2이며 validation은 두지 않는다.** 생성한 모든 checkpoint를 보관하고 test에서 best를 선택한다. test를 모델 선택에 사용한 결과가 낙관적이라는 점을 받아들이며 보고서에 명시한다. 별도의 validation split을 임의로 추가하지 않는다. 여기서 ‘모든 checkpoint’에는 저장한 모델 snapshot과 재개용 checkpoint를 포함하며 자동 rotation/삭제를 사용하지 않는 것으로 반영했다.

Git 전달 형식 예시는 다음과 같다. 아래는 구현 후 변경 파일과 PR 본문을 확인한 상태에서 사용하는 명령 틀이며 지금 실행할 명령이 아니다. `git branch --show-current` 결과가 `rl-grpo`가 아니면 임의로 checkout하지 않고 현재 상태를 확인한다. `/tmp/newman_pr_body.md`는 실제 변경 목적과 수행한 검증 결과를 미리 작성한 파일이어야 한다.

```bash
git branch --show-current
git add newman_experiment/ rl/EXPERIMENTS.md
git status --short
git diff --cached --stat
git diff --cached
git commit -m "Add Newman-conditioned math error generation experiment"
git push origin rl-grpo
gh pr create --base main --head rl-grpo --title "Add Newman-conditioned math error generation experiment" --body-file /tmp/newman_pr_body.md
gh pr view --json number,url
gh pr merge --merge
git fetch origin && git merge origin/main
git status --short
```

각 단계의 실패를 확인하고 다음 단계로 넘어간다. 기존 PR을 재활용하는 대신 이번 변경을 위한 새 PR을 만든다. `status`와 staged diff에서 무관한 파일이나 비밀정보가 없는지 확인한 뒤 commit한다.

## 1. 실험 목표와 범위

Student에 수학 문제 Q, Newman 단계 N, 원본 데이터셋의 오류 유형 E를 제공하고, 해당 조건에 맞는 틀린 풀이 S를 생성하도록 RL로 학습한다.

입출력은 `Student(Q, N, E) → S`이다. N은 오류가 발생하는 문제 해결 단계, E는 오류의 대략적인 형태를 지정한다. 예를 들어 `Process Skills + Calculation Error`는 식의 피연산자와 연산자는 맞지만 계산 결과를 틀리는 풀이를 요구한다. 개별 문제의 오답 경로를 설명한 descriptive error는 조건에 넣지 않는다.

RM은 MathEDU, Stepwise/StepVerify, MathClean, EIC의 원본 풀이와 승인된 Newman 재매핑으로 학습한다. MathQA는 MathEDU 등의 문제 원문을 복원하기 위한 출처이며 다섯 번째 오류 데이터셋으로 세지 않는다. EIC의 GSM8K/MathQA 하위 출처는 별도 메타데이터로 유지한다.

이번 계획에서 SFT는 **RM의 full-parameter SFT**를 뜻한다. Student는 우선 Instruct 모델에서 RL을 시작한다. Student에 별도 SFT를 추가하는 것은 이 계획의 기본 실험에 포함하지 않는다.

연구 가설은 ‘학습한 Student가 문제별로 상세히 지정되지 않은 단계/유형 조건을 더 정확하게 구현한다’이다. 기존 Eedi 실험의 성공률이나 과거 논문의 서로 다른 조건 체계에서 측정한 점수와 직접 비교해 우월성을 주장하지 않는다. Base, RL, API baseline을 모두 같은 Q/N/E와 같은 평가 기준으로 다시 평가한다.

## 2. 확인한 자료와 적용 범위

### 2.1 하이퍼파라미터 기준

- 저장소: https://github.com/WooYoungSeok/tutee_error
- 확인한 main 커밋: `a95df533902332310d3d629ed7ace423980cdf0d`
- 커밋 시각: 2026-09-30 06:49:31 UTC
- 확인 파일: `verifier_sft/config/descriptive_verifier_v2.json`, `verifier_sft/train_descriptive_verifier.py`, `verifier_sft/ds_config.json`, `verifier_sft/README.md`, `rl/configs/common.yaml`, `rl/configs/accelerate_zero2_offload.yaml`, `rl/scripts/train.py`, `rl/EXPERIMENTS.md`, 각 환경의 `requirements-lock.txt`.

학습률, 배치, epoch, rollout 샘플링, KL, clipping, 정밀도, 메모리 설정과 저장 주기는 이 커밋의 최종 설정을 출발점으로 사용한다. 데이터 구성, RM 학습 목표, negative 규칙, 평가셋, checkpoint 선택 방식은 새 실험에 맞춰 설계한다. 과거 중단 run의 temperature 0.7, accumulation 8, 3 epoch를 최종 설정으로 가져오지 않는다.

`rl/EXPERIMENTS.md`의 샘플링 보정 관련 설명은 저장소의 당시 진단이다. ‘T=1이면 모든 보정 문제가 사라진다’, ‘평균 비율 0.1이면 gradient가 정확히 1/10이 된다’는 일반 법칙으로 사용하지 않는다. 새 run에서 실제 비율, mask 비율, gradient와 KL을 기록한다.

### 2.2 Newman 매핑 기준 — 사용자 확정

최신 업로드 파일 **Newman_relabeling_영석_마무리 (1)(1).xlsx**의 `Newman 재분류` 시트, **D열 ‘영석 분류’**를 적용한다. C열 ‘혁규 분류’와 별도 `분류 근거` 시트에 남아 있는 이전 분류로 D열을 덮어쓰지 않는다.

- 파일 SHA-256: `9324bac2d5112d3bbc4e6fc27a1b7d3a128bcc017c6586389d1d345c28b3da7b`.
- 표는 원본 오류 유형 26개의 **유형별 매핑표**이며 개별 풀이를 재검수한 annotation은 아니다.
- D열이 Reading / Comprehension / Transformation / Process Skills이면 해당 단계에 매핑한다.
- `Transformation(9)`는 `Transformation`으로 읽고 괄호의 메모는 별도 보존한다.
- `제외(85)`, `제외 - 100*2`처럼 ‘제외’로 시작하는 값은 모두 제외한다. 숫자는 표에 적힌 메모이며 신규 데이터의 검증된 사례 수로 사용하지 않는다.
- 최신 표의 제외 10개를 이전 초안처럼 ‘판단보류’로 표기하지 않는다.

### 2.3 Negative와 GSM8K 필터의 참고 저장소

- 저장소: https://github.com/WooYoungSeok/llm_tutee_tutor
- 확인한 main 커밋: `972f0c3866a48520c87c254f45dcd9c875da8797`.
- `finetuning/train_new_label_0622.py`의 `build_samples`는 동일 Q/S에 정답 category를 붙인 positive 1개와, 다른 category 하나를 무작위 선택한 negative 1개를 만든다. 출력은 `aligned` 또는 `not_aligned`다.
- `finetuning/train_new_label.py`, `finetuning/reward_model/train_0428.py`, `train_0431.py`에서도 같은 기본 구성을 확인했다.
- **현재 확인한 SFT 코드에서는 단위 변환 negative를 특정 질문에 제한하는 별도 목록/조건을 찾지 못했다.** 따라서 기존 코드에 그 제한이 이미 있다고 서술하지 않는다. 이번 구현에서는 사용자 지시대로 제한을 명시적으로 추가한다.
- **RL용 허용 목록은 확인했다.** `RL_new_cluster_2prm_0623/data/fix_labels.py`의 `UNIT_CONV_RAW`와 보정 함수를 재사용한다. 자세한 적용은 5.7절을 따른다.

옛 저장소의 5개 대분류, 90:10 split, 8 epoch, checkpoint 자동 삭제 등은 복사하지 않는다. 새 taxonomy와 사용자 확정 작업 규칙을 우선하고, 학습 하이퍼파라미터는 `tutee_error`의 최종 설정을 참고한다.

## 3. 사용할 라벨 체계

확인한 표에는 원본 오류 유형 26개가 있다. D열 기준으로 16개를 채택하고 ‘제외’로 표시된 10개는 사용하지 않는다. 채택 유형의 Newman 단계 분포는 Reading 2개, Comprehension 2개, Transformation 6개, Process Skills 6개다. **Encoding에 해당하는 채택 유형은 없다.** 숫자는 풀이 수가 아니라 오류 유형의 수다.

### 3.1 채택 유형 16개

아래 데이터셋 구분은 각 원본 taxonomy에 따른 것이다. 구현 시 원본 파일의 label manifest와 대조한다. 원문 표기와 안정적인 내부 ID를 함께 보존한다.

| 데이터셋 | 원본 오류 유형 | Newman 단계 |
|---|---|---|
| MathEDU | Wrong Mathematical Operation/Concept | Transformation |
| MathEDU | Comprehension error | Comprehension |
| MathEDU | Arithmetical error | Process Skills |
| MathEDU | Algebraic error | Process Skills |
| MathEDU | Measurement error | Transformation |
| MathClean | Logic error | Transformation |
| MathClean | Computing error | Process Skills |
| EIC | Calculation Error | Process Skills |
| EIC | referencing context value error | Reading |
| EIC | referencing previous step value error | Process Skills |
| EIC | Unit Conversion Error | Transformation |
| EIC | Operator Error | Transformation |
| EIC | confusing formula error | Transformation |
| EIC | adding irrelevant information | Reading |
| Stepwise | Calculation error easily solved by a calculator | Process Skills |
| Stepwise | Misunderstanding of a question | Comprehension |

### 3.2 제외 유형 10개

| 데이터셋 | 제외 유형 |
|---|---|
| MathEDU | Unfinished answer; Lack of Necessary Mathematical Concepts; Careless Error |
| MathClean | Expression error |
| EIC | Counting Error; Missing Step |
| Stepwise | Extra quantity or Missing quantity; Missing / Wrong factual knowledge; Reached correct solution but proceeded further; Unit conversion error |

제외 유형의 사례는 이번 SFT 풀에서 제외하고, 해당 유형명은 positive/negative 및 Student 목표 조건의 후보 목록에 모두 넣지 않는다. 제외 유형을 다른 모든 유형에 대한 negative로 전환하지 않는다.

### 3.3 라벨을 해석하는 규칙

1. 라벨 ID는 `(source_dataset, source_label)`로 구분한다. EIC의 `Unit Conversion Error`와 Stepwise의 `Unit conversion error`는 대소문자를 지워 하나로 합치면 안 된다. 전자는 채택, 후자는 제외다.
2. 표기 정규화는 데이터셋 내부에서 승인된 alias에만 적용한다. 원문 라벨은 별도 필드에 보존한다.
3. 자료의 Newman 매핑을 구현자가 임의로 변경하지 않는다. 이미 확인된 원본 라벨 충돌은 제외 사유로 기록한다. 매핑 단계에서 새 API 의미 검수를 자동 추가하지 않는다.
4. `adding irrelevant information → Reading`, 단위 관련 유형의 `Transformation` 배정은 이 연구의 운영상 매핑이다. 모든 NEA 연구에서 동일한 배정을 사용한다고 서술하지 않는다.
5. 일반적인 NEA는 Reading, Comprehension, Transformation, Process Skills, Encoding의 5단계를 사용하고 학생 면담을 포함한다. 여기서는 서면 풀이와 원본 라벨에서 관찰 가능한 오류를 매핑한다. 실제 학생의 잠재 인지 원인을 입증했다고 해석하지 않는다.[N1]
6. **현재 N은 E의 결정적 함수다.** `N = mapping(E)`이므로 입력 필드는 두 개여도 독립적인 제어 축 두 개가 아니다. 두 필드를 모두 쓰는 것은 단계와 유형을 명시하는 지시 방식이다. 추가적인 Newman 조건의 효과를 주장하려면 같은 Q/E에서 N 제공 여부를 바꾸는 별도 비교가 필요하다.

## 4. 모델 구성과 역할

### 4.1 Student

`Student(Q, N, E) → S`. 문제와 Newman 단계, 원본 오류 유형의 이름/공통 정의를 받아 틀린 풀이를 생성한다. 원본 오답 풀이, 오류 위치, 정답 풀이, 교사 첨삭, 문제별 descriptive error는 제공하지 않는다.

### 4.2 동일한 판정 과제를 학습하는 모델 두 개

`Verifier(Q, Incorrect solution S, target N, target E) → aligned / not_aligned`.

| 역할 | SFT 데이터 | 사용 시점 | Student gradient에 영향 |
|---|---|---|---|
| Reward model A | train half-A | RL 중 오답의 조건 적합성 판정 | 보상을 통해 영향 |
| Test verifier B | train half-B | Student checkpoint와 baseline의 test 평가 | RL 보상에는 사용하지 않음 |

두 모델은 **새 taxonomy로 각각 SFT**한다. A를 먼저 학습한 뒤 그 가중치에서 B를 이어 학습하면 A 데이터가 B에 전해지므로 그렇게 하지 않는다. 각 모델은 지정한 공개 backbone에서 별도로 시작한다. 기존 descriptive verifier checkpoint를 그대로 새 taxonomy의 평가자로 쓰지 않는다.

A와 B는 Q/S에 실제로 나타난 오류가 제시한 N/E에 맞는지 판단한다. 정답인지의 판정은 gpt-5-nano가 맡는다. 모델 출력에 unknown을 추가하지 않고 `aligned` / `not_aligned`만 학습한다. 형식 오류는 외부 parser에서 invalid로 기록한다.

**모델 두 개와 호출 두 번은 다르다.** RL에서는 A 하나를 temperature 0.6으로 2회 호출하고 둘 다 aligned일 때 통과한다. test에서는 B 하나로 같은 규칙을 적용한다. A와 B가 함께 동의해야 학습 보상을 주는 구조가 아니다.

### 4.3 원본 유형을 유지하는 이유와 negative 후보 범위

Newman 단계는 영석 분류로 추가하고 원본 오류 유형은 그대로 유지한다. 예를 들어 EIC의 계산 오류와 이전 단계 값 참조 오류는 모두 Process Skills지만 서로 다른 원본 유형이다. 같은 단계 안에서 잘못된 원본 유형을 붙인 negative도 만들어져야 한다.

서로 다른 데이터셋의 산술 오류 라벨은 의미가 겹친다. 따라서 기존 사용자 합의에 맞춰 negative는 **같은 원본 데이터셋의 채택 유형 중 다른 유형**에서 고른다. EIC_GSM8K와 EIC_MathQA는 EIC taxonomy를 공유하고 benchmark 출처는 보존한다. Newman 단계가 다르다는 조건을 강제하지 않는다.

원본 라벨이 다르다고 실제 의미가 반드시 배타적인 것은 아니다. 사용자의 기존 지시에 따라 negative별 API false-negative 검수는 추가하지 않는다. 이 한계와 유형별 false acceptance를 결과에 함께 기록한다.

## 5. 데이터 준비, 재라벨링, negative와 split

### 5.1 재라벨링을 실제 레코드에 반영하는 방법

재라벨링은 새 풀이를 생성하거나 기존 라벨을 삭제하는 작업이 아니다. **원본 레코드의 오류 유형을 영석 분류표에 연결해 Newman 필드를 추가**한다.

1. 원본 Q/S/오류 유형/ID/교사 주석을 보존한다.
2. `(source_dataset, source_error_label)`로 승인된 alias를 해석한다. 대소문자만으로 다른 데이터셋의 라벨을 합치지 않는다.
3. D열의 ‘제외’ 여부를 먼저 검사한다.
4. 포함 유형이면 `newman_stage`를 추가하고 표의 파일 해시, 시트, 행, 원래 D열 문자열을 보존한다.
5. positive에서는 이 원본 E와 대응하는 N을 사용한다. negative에서는 E를 E'로 바꾼 뒤 **N도 mapping(E')로 함께 갱신**한다.
6. Student의 조건과 두 verifier의 조건 정의가 동일한 taxonomy 파일을 읽도록 한다.

예: `EIC / Unit Conversion Error`는 `Transformation`을 추가해 유지한다. `Stepwise / Unit conversion error`는 최신 표에서 제외됐으므로 이름이 비슷해도 넣지 않는다.

구조 예시이며 실제 레코드는 아니다:

```json
{
  "sample_id": "stable-source-record-id",
  "source_dataset": "eic",
  "source_benchmark": "gsm8k",
  "source_question_id": "original-id",
  "question_group_id": "stable-group-id",
  "question": "...",
  "reference_answer": "...",
  "incorrect_solution": "...",
  "source_error_label_raw": "Calculation Error",
  "source_error_id": "eic.calculation_error",
  "newman_stage": "process_skills",
  "mapping_basis": "label_level_mapping",
  "mapping_version": "youngseok_20260930_v2",
  "mapping_cell_raw": "Process Skills",
  "mapping_file_sha256": "9324bac2d5112d3bbc4e6fc27a1b7d3a128bcc017c6586389d1d345c28b3da7b",
  "description_generation_status": "ok",
  "unit_conversion_eligible": null,
  "unit_eligibility_source": null,
  "split": "train",
  "verifier_half": "A"
}
```

이전에 만든 descriptive error C와 evidence는 추적/검수용으로 보존할 수 있지만 Student와 verifier의 조건에는 사용하지 않는다. `unit_conversion_eligible=null`은 ‘불가능이 입증됨’이 아니라 확인된 허용 목록이 없다는 뜻이다.

### 5.2 원본 정리와 기존 품질 필터

- 네 원본을 adapter로 통일한다. MathQA는 MathEDU 등의 질문 복원에 사용하며 원본 인덱스 순서를 대조한다.
- 중복 Q/S, 빈 풀이, 필수 그림/보기 누락, 이미 확인된 정답 사례/라벨 충돌을 보고한다.
- v2에서 제외했던 **동일 풀이에 여러 종류의 오류 라벨이 붙은 사례**를 다시 자동 편입하지 않는다. 같은 Q라도 S가 다르면 구분한다.
- 기존에 descriptive error를 생성한 풀에서는 사용자가 정한 `status=ok` 필터를 유지한다. 이번 N/E 매핑과 별개의 품질 필터다. C 생성 이력이 없는 원본까지 풀을 확대할지는 데이터 규모 보고 후 확인한다.
- 여기서 재라벨링된 16개 유형의 수와 최종 사례 수를 혼동하지 않는다. 표의 괄호 숫자로 학습 행 수를 계산하지 않는다.
- 입력 길이는 실제 tokenizer로 확인한다. 오류를 판정할 부분이나 assistant 정답을 잘라낸 채 학습하지 않는다.

### 5.3 질문 단위 80:20, 학습 부분은 half-A/half-B

아래 구체화는 사용자의 **8:2 / validation 없음 / 두 학습 half**를 함께 만족하는 구성이다.

| 전체 적격 원본 기준 | 목적 |
|---|---|
| 약 40% | RM A용 SFT train half-A |
| 약 40% | 평가 verifier B용 SFT train half-B |
| 약 20% | 두 모델의 SFT test, checkpoint 선택/보고 |

1. 전역 문제 그룹으로 train:test=80:20을 먼저 만든다.
2. train 80%를 다시 문제 그룹 단위 50:50으로 나눠 A/B에 배정한다.
3. seed는 42. 출처/유형 분포를 가능한 한 유지하되 그룹을 깨서 정확한 행 비율을 맞추지 않는다.
4. **positive/negative를 만들기 전에** split과 half를 확정한다. 같은 원본 S에서 만든 두 행은 같은 곳에 둔다.
5. 다른 원본에 실린 동일 GSM8K/MathQA 문제도 같은 그룹이다. A/B/test 간 Q, S, 파생 행의 중복을 확인한다.
6. A/B는 별도로 모든 checkpoint를 저장하고 SFT test에서 각각 best를 선택한다. B를 A와 가장 많이 동의하는 모델로 선택하지 않는다.

원본 문제 ID와 Unicode/공백 정규화를 사용한다. 수학적 의미를 바꾸는 기호 제거는 하지 않는다. 같은 test로 A/B를 선택하므로 **학습 데이터가 분리된 평가 모델**이라는 의미이며 완전히 독립적인 평가나 공유 편향의 제거를 보장하지 않는다. test 선택의 낙관성도 명시한다.

RL용 GSM8K와 SFT 원본에 겹치는 질문은 전역 그룹 manifest로 연결한다. **RL test 질문이 A/B SFT train에 들어가거나, SFT test 질문이 RL train에 들어가지 않게 한다.** 이 제약으로 80:20과 층화가 정확히 맞지 않는 경우 오차를 보고하고 임의로 누출을 허용하지 않는다.

### 5.4 Negative 생성 알고리즘

참고 코드의 **원본 풀이당 positive 1개 + negative 1개**, `random.Random(42)` 원칙을 따른다. 정렬된 원본 ID/후보 목록에서 한 번 생성해 manifest에 고정하며 epoch마다 다시 뽑지 않는다.

원본 레코드가 `(Q,S,E)`이고 `N=mapping(E)`이면:

- positive: `(Q,S,N,E) → aligned`.
- 후보: 같은 원본 데이터셋의 채택 E' 중 `E' != E`.
- 후보가 두 단위 관련 유형이면 5.5절의 Q 허용 조건을 만족할 때만 남긴다.
- 후보 중 한 개를 균등 무작위 선택한다.
- negative: `(Q,S,mapping(E'),E') → not_aligned`.

Q/S를 다른 풀이로 교체하지 않는다. 지금은 문제별 C를 옮기는 작업이 아니라 taxonomy 라벨을 바꾸므로, donor로 쓸 다른 질문의 사례를 고를 필요가 없다. 어느 split/half에서도 다른 split의 풀이를 가져오지 않는다.

N만 틀리게 붙이거나 N/E를 모순되게 조합하지 않는다. 모델이 매핑표만 보고 답을 맞히는 쉬운 negative가 생기기 때문이다. **같은 N 안의 다른 E도 후보에 포함**하고, 실제로 만들어진 same-stage/different-stage negative 수를 각각 보고한다.

후보가 0개면 유형 제한을 풀지 말고 `no_negative_candidate`로 기록한다. 1:1을 유지하는 기본안에서는 해당 원본의 positive도 paired SFT에서 제외한다. split/half별 각 유형의 positive와 negative 수를 audit하고, 한 유형에 negative가 전혀 없으면 라벨 이름만으로 답을 맞힐 위험을 보고한 뒤 데이터 구성을 확정한다.

negative를 새 LLM으로 의미 검수하거나 그럴듯한 새로운 풀이를 합성하는 과정은 이번 기본 계획에 추가하지 않는다.

### 5.5 SFT의 단위 오류 negative 제한 — 사용자 확정

대상은 다음 **원소스 라벨 두 개**다.

- `mathedu.measurement_error` — Measurement error.
- `eic.unit_conversion_error` — Unit Conversion Error.

이 E'를 negative로 붙이려면 **현재 Q가 확인된 단위 변환 허용 목록에 있어야 한다.** 단위라는 단어가 있다는 이유만으로 허용하지 않는다. 다른 Transformation 유형 전체를 같은 방식으로 제한하지도 않는다.

`allow_unit_negative(Q) = (unit_conversion_eligible is True)`

예를 들어 단위 변환 가능한 문제의 계산 실수 풀이에 Unit Conversion Error를 negative로 붙이는 것은 허용한다. 허용 목록 밖의 단순 합계 문제에는 이 라벨을 붙이지 않고 다른 후보에서 고른다. 이 제약은 해당 negative의 실제 의미상 비정렬 여부를 보장하는 검수와는 다르다.

**허용 목록 확보 상태와 처리**

| 출처 | 확인된 자료 | 적용 |
|---|---|---|
| GSM8K와 정확히 연결되는 SFT 질문 | 5.7절의 기존 수작업 허용 목록 | 원본 split/행/Q를 대조한 뒤 사용 |
| MathQA/MathEDU 또는 연결되지 않는 질문 | 현재 main에서 별도 SFT 허용 목록 미확인 | True로 추측하지 않음. 해당 단위 라벨을 negative 후보에서 제외 |
| 사용자가 별도로 선정해 둔 SFT 질문 목록 | 아직 파일 경로 미확인 | 발견 시 출처/해시/Q ID를 기록하고 병합 |

GSM8K의 정수 인덱스를 MathQA나 SFT 파일의 행 번호로 사용하면 안 된다. 특히 MathEDU의 Measurement error negative가 0건이 되는지 확인해야 한다. 목록이 없어 균형 있는 학습 구성이 불가능하면 해당 부분을 데이터 준비의 미완료 항목으로 보고한다. 완성된 제한 목록이 있는 것처럼 본 SFT를 시작하지 않는다.

### 5.6 RL 문제와 조건 구성

RL 문제 풀은 사용자가 지시한 **GSM8K**를 기준으로 준비한다. 이전 초안의 ‘네 오류 원본의 train Q로만 시작’ 제안은 기본안에서 뺀다. 기존 train:test=8:2, validation 없음 규칙을 유지한다. GSM8K 원래 train만 사용할지 원래 train+test를 풀로 사용할지는 실행 전 범위 확인 항목이며, 옛 저장소의 split을 자동 승계하지 않는다.

각 RL 행은 `(Q, reference_answer, N, E, condition_id)`다. 조건 배정에서도 E를 먼저 정하고 N=mapping(E)를 붙인다. 원본 오류 라벨의 설명은 고정 taxonomy 정의를 사용한다.

단위 변환 불가/미확인 질문은 **두 단위 오류 조건의 후보에서만 제외**한다. 다른 오류 조건의 학습 질문까지 통째로 삭제하지 않는다. 같은 Q에 여러 조건을 배정하더라도 모든 조건은 같은 split이다.

질문당 조건 수, 원본 유형별 균형 배정 여부, 최종 규모는 데이터 audit 후 사용자와 확정한다. 기존 코드의 5개 cluster별 할당 수를 16개 원본 유형에 그대로 복사하지 않는다. 이번 두 보조 보상 실험은 확정된 동일 조건 manifest를 공유한다.

### 5.7 GSM8K 단위 변환 허용 목록 재사용

확인 파일: `RL_new_cluster_2prm_0623/data/fix_labels.py`. `UNIT_CONV_RAW`는 시간, 길이, 화폐, 거리, 무게/부피, 묶음 단위의 수작업 인덱스를 담는다.

코드의 보정값을 적용하고 중복 제거한 결과:

| GSM8K 원본 split | 허용 고유 인덱스 수 |
|---|---:|
| train | 845 |
| test | 203 |

이는 **코드 상수에서 계산한 허용 인덱스 수**다. 새 학습 풀과 연결/중복 제거한 뒤 사용할 수 있는 실제 문제 수와는 다르다. 원본 parquet와의 전체 내용 대조는 구현 시 수행해야 한다.

재사용 절차:

1. `idx = raw_idx + correction`을 적용한다. 시간/길이/화폐 그룹은 -2, 거리/무게·부피/묶음 그룹은 0이다.
2. 원본 split 이름과 0-based 행을 함께 키로 사용하고 그 행의 질문/정답을 읽는다.
3. 참고 코드의 `build_parquet_index_map`처럼 정규화한 Q와 정답을 대조한다. JSON은 섞여 있으므로 현재 JSON 행 번호로 바로 적용하지 않는다.
4. 질문 해시에 `unit_conversion_eligible=True`와 목록 provenance를 저장한다. 매칭이 0건 또는 여러 건이면 자동 추측하지 않는다.
5. 신규 80:20 split으로 재분할해도 `original_split`과 `original_row_index`는 보존한다.
6. RL train/test와 SFT negative 생성이 동일 eligibility manifest를 조회한다. 두 단위 라벨이 True인 Q 밖에 배정된 건수가 0인지 assert한다.

`build_train_subset.py`는 **기존 Llama base가 정답을 맞힌 문제만 선택하는 별도 필터**다. 단위 변환 허용 목록과 다르므로, 이번에 그 6,783문제 subset까지 사용하기로 결정한 것으로 간주하지 않는다. old `train_subset_indices.json`이나 `train_subset_full_log.json`을 단위 변환 필터로 대신 쓰지 않는다.

## 6. RM SFT

### 6.1 학습 입력과 타깃 — 프롬프트 초안

A/B에 동일한 판정 계약을 사용한다. 문제, Incorrect solution, target Newman 단계/정의, target 원본 오류 유형/정의를 입력한다. 원본 정답 라벨 메타데이터와 negative 생성 여부는 입력하지 않는다.

```text
You evaluate whether an incorrect mathematical solution matches a specified error.
Use the question and the mathematical reasoning shown in the solution.
Judge whether the observed error matches both the specified problem-solving stage
and the specified error type. An incorrect final answer alone is not sufficient.
An error label mentioned in the solution is not evidence that the error was made.
Respond with exactly one of: aligned, not_aligned.
```

```text
Question:
{question}

Incorrect solution:
{incorrect_solution}

Problem-solving stage:
{newman_stage_name}
{newman_stage_definition}

Error type:
{source_error_name}
{source_error_definition}
```

assistant 정답은 정확히 `aligned` 또는 `not_aligned`다. 두 필드가 매핑상 일관되더라도 풀이에 그 오류가 없으면 not_aligned다. 예전 초안의 ‘최초 미수정 오류만’, OTHER_ERROR, 다중 분류 출력은 추가하지 않는다. 프롬프트의 최종 문구는 본 SFT 전에 사용자 검토를 받는다.

### 6.2 하이퍼파라미터

| 항목 | 값 | 근거/비고 |
|---|---|---|
| A backbone | Qwen/Qwen2.5-Math-7B-Instruct | 기존 RM 계열을 출발점으로 제안 |
| B backbone | deepseek-ai/DeepSeek-R1-0528-Qwen3-8B | 기존 held-out verifier 계열을 출발점으로 제안. A/B backbone 최종 확인 필요 |
| 학습 범위 | Full-parameter SFT | 저장소와 동일 |
| learning rate | 1e-5 | 확인 |
| epochs | 최대 5 | 확인. 모든 epoch 저장 후 test로 best 선택 |
| weight decay | 0.01 | 확인 |
| warmup | 총 optimizer step의 10% | 확인 |
| LR scheduler | linear | 새 설정에 명시할 제안. 기존 SFT 코드는 이 값을 명시하지 않고 프레임워크 기본값 사용 |
| optimizer | AdamW 계열, CPU optimizer offload | 새 실행의 실제 optimizer class와 beta/epsilon을 manifest에 기록 |
| per-device train batch | 8 | 확인 |
| gradient accumulation | 4 | 확인 |
| 기준 학습 GPU 수 | 1 | 7B용 기준. effective batch 32 |
| per-device test loss 평가 batch | 1 | 기존 eval batch 확인. validation은 사용하지 않음 |
| max sequence length | 4096 | 확인. N/E 정의 포함 후 길이 재측정 |
| precision | BF16 | 확인 |
| gradient checkpointing | true, use_reentrant=false | 확인 |
| DeepSpeed | ZeRO-2 + CPU optimizer offload | 확인 |
| padding | left, pad loss mask=-100 | 확인 |
| loss 구간 | assistant aligned/not_aligned 및 EOS만 | 학습 방식 승계, 프롬프트는 mask |
| seed/data seed | 42 | 확인 |
| logging | 10 step, W&B | 확인 |
| model 저장/test 평가 | 매 epoch, 모든 checkpoint 보관 | 저장 주기는 확인. test 선택/전부 보관은 사용자 지시 |
| checkpoint 선택 | SFT test의 binary macro-F1 최대, 동률이면 negative false acceptance 최소, 이후 test loss | 선택 순서는 제안. test에서 선택하는 원칙은 확정 |
| verifier 생성 길이 | 최대 10 tokens | 기존 binary 출력 설정 승계. 각 tokenizer에서 두 정답 문자열과 EOS가 충분히 들어가는지 확인 |

A/B를 각자의 half로 별도 학습한다. B가 다른 backbone이면 템플릿과 tokenizer는 해당 모델 것을 사용하되 출력 계약/데이터 구성/학습 설정은 동일하게 적용한다. SFT의 teacher forcing에는 sampling temperature가 없다. RM 평가와 RL 보상 호출의 decoding 설정은 별도다. 매 epoch의 모델 및 저장된 재개용 checkpoint를 모두 보관한다. `save_total_limit`에 의한 자동 삭제를 사용하지 않는다. 저장 형식별 필요 용량을 사전에 계산하고 용량이 부족하면 사용자와 보관 정책을 논의한다.

초기에는 출처/유형의 실제 분포로 학습하는 안이다. 클래스 불균형이 큰 경우 train 분포와 test 진단 결과를 보고 class-balanced sampling 변경안을 사용자와 논의한다. 자료 확인 전 임의의 배수로 복제하지 않는다. test 진단을 보고 설계를 바꾼 경우에도 그 이력을 기록한다.

### 6.3 A/B SFT 평가와 보상 판별력 진단

고정된 SFT test의 positive/negative 쌍에서 각 모델을 따로 평가한다. 정확 일치 parser를 사용하고, `not_aligned`에 포함된 문자열 `aligned`를 substring 검색으로 수락하지 않는다.

| 지표 | 정의 |
|---|---|
| binary accuracy / macro-F1 | aligned, not_aligned 두 클래스 성능 |
| negative recall | negative 중 not_aligned로 올바르게 거부한 비율 |
| negative false acceptance | negative 중 aligned로 잘못 수락한 비율 |
| positive recall | positive 중 aligned로 수락한 비율 |
| invalid | 두 출력 외의 응답 비율 |
| same-stage / different-stage negative | 같은 Newman 단계의 다른 원본 유형을 구분하는지 |
| 유형별 / 단위 허용 질문별 성능 | 전체 평균에 가려지는 약점과 쉬운 negative 효과 확인 |

invalid가 있으면 negative recall과 false acceptance를 단순 보수 관계로 처리하지 말고 invalid를 별도 집계한다. A/B 데이터 수, 문제 수, 16개 유형별 positive/negative 수를 함께 제시한다.

SFT checkpoint 비교는 greedy decoding으로 고정하고, 실제 reward 경로와 맞춘 **n=2, T=0.6, 둘 다 aligned** 평가도 선택 모델에 대해 보고하는 안이다. 두 방식의 결과를 혼합하지 않는다. A/B 각각의 decoding 설정을 저장한다.

예시 진단: 동일 Q가 ‘12개씩 4묶음의 합계’일 때 `12×4=40`은 계산 오류, `15×4=60`은 Q의 값 참조 오류, `12+4=16`은 연산자 오류로 구분할 수 있는지 본다. 이는 설계 설명용 예이며 원본 학습 사례로 간주하지 않는다.

높은 random-negative test 성능만으로 실제 RL reward에 적합하다고 결론내리지 않는다. 새 Student rollout에도 A/B를 적용해 수락률, 불일치 및 구체적인 오판 사례를 보고한다. 별도의 API 의미 검수나 hard-negative 보충 학습을 추가하려면 방법과 범위를 사용자와 먼저 확정한다. 임의의 10%/80% 통과 기준이나 새 학습 라벨을 자동 도입하지 않는다.

## 7. Student 지시문 초안

```text
You are simulating a student's attempt at a mathematics problem.

Write an incorrect solution whose main error occurs at the specified
problem-solving stage and matches the specified error type.
Write the attempt in the student's own voice, as if the student believes it is correct.
Show enough working for the error to be identifiable, and give one final answer.
Do not explain the assigned error, identify it as a mistake, or correct it afterward.
Use ordinary mathematical notation. Do not add answer tags.

Problem-solving stage: {newman_stage_name}
Stage definition: {newman_stage_definition}
Error type: {source_error_name}
Error-type definition: {source_error_definition}
```

user 메시지에는 `{question}`을 넣는다. 위 definition은 승인 taxonomy에서 읽어오며 문제마다 LLM이 새로 작성하지 않는다. 원본의 넓은 오류 유형을 개별 문제의 구체적 실행 지침으로 바꾸지 않는다.

단계 정의는 4개를 고정하고, 예시 풀이를 Student에게 제공하지 않는 안이다. Reading 등 이 연구의 운영상 범위가 일반 정의보다 넓은 경우 mapping 문서의 범위를 명시적으로 맞춘다. 정의가 다르면서 같은 단계명만 사용하는 불일치를 피한다.

## 8. RL 보상 설계

이 절은 이전 대화에서 합의한 오답 보상, 학생다움/다양성의 분리 실험, 0.5 가중치를 새 조건에 연결한 제안이다. 저장소의 기존 descriptive verifier를 재사용하는 것은 아니다.

### 8.1 최종 답 판정

모든 rollout의 최종 답 추출/정오 판정에 **gpt-5-nano, reasoning effort=low**를 사용한다. 최신 사용자 지시이며 기본 reasoning 값에 맡기지 않는다. 입력은 Q, 정답, 답 형식 계약, 생성 풀이이고 target N/E와 RM 판정은 숨긴다.

- 명확한 최종 답: `extracted_answer`와 `verdict` 반환.
- 최종 답 불명확: 둘 다 JSON null.
- 답은 추출되지만 비교 기준 자체가 모호함: 추출 답을 보존하고 verdict는 null.
- API 오류나 응답 파싱 실패: 채점 미완료로 재시도/중단. 학생의 의미상 null로 처리해 불이익을 주지 않는다.
- Student에게 answer 태그를 요구하지 않는다.

### 8.2 오류 조건 일치

오답으로 확인된 S만 **frozen RM A**에 보낸다. `(Q,S,N,E)`를 동일 모델로 n=2, temperature 0.6, top_p 1.0, top_k 비활성, repetition penalty 1.0으로 호출한다. 두 출력이 모두 정확히 `aligned`여야 통과한다.

`r_RM = 1[ A_1(Q,S,N,E)=aligned AND A_2(Q,S,N,E)=aligned ]`.

test에서는 동일한 계약으로 **별도 학습한 frozen verifier B**를 두 번 호출한다. A/B의 학습 데이터 분리와 각 모델의 확률적 2회 호출을 구분한다. 같은 모델을 두 번 호출한다고 판정 오류가 통계적으로 독립이 되지는 않는다.

`N == mapping(E)`는 입력 구성 단계에서 assert한다. 단계와 유형을 따로 맞혔다며 보상을 이중 지급하지 않는다. 정상 응답의 not_aligned 또는 invalid는 불통과로 집계하고, 서버 장애는 재시도/채점 실패로 구분한다.

### 8.3 공통 보상

\[
r_i^{base}=\begin{cases}
-0.75 & \text{정답 또는 의미상 최종 답 판정 불가}\\
1 & \text{오답이며 RM A 두 번 모두 aligned}\\
0 & \text{오답이지만 RM A 통과 실패}
\end{cases}
\]

\[
r_i^{trunc}=-0.5\,\mathbf{1}[\text{최대 길이에 도달했고 EOS 없음}]
\]

KL은 GRPO objective의 beta로 적용하며 보상에 다시 더하지 않는다. `<answer>` 태그 보상은 사용하지 않는다.

### 8.4 두 실험군

| 실험 | 보상 |
|---|---|
| student_likeness | `base + 0.5 × student_likeness + truncation` |
| diversity | `base + 0.5 × diversity + truncation` |

둘을 동시에 더하는 실험과 공통 보상만 있는 RL ablation은 기본 계획에 넣지 않는다. 학습 전 Base 비교는 유지한다.

통과 집합 G는 **같은 Q/N/E 조건의 8개 rollout 중 오답이며 RM을 통과한 풀이**다. 서로 다른 조건의 풀이를 같은 그룹으로 합치지 않는다. |G|<2이면 두 보조 점수 모두 0이다.

- Diversity: `1 − max_j sentence_BLEU(S_i,S_j)/100`. full solution을 사용하며 sacrebleu 13a, exp smoothing, effective_order=true, 대소문자 유지 설정을 고정한다.
- Student likeness: **gpt-5-nano, reasoning effort=low**로 G 안의 모든 unordered pair를 비교한다. 최대 28쌍. A/B 순서는 seed로 무작위화하고 무승부를 허용한다. `(승리 수 + 0.5 × 무승부 수) / (|G|-1)`로 정규화한다.
- 학생다움 judge에는 앞서 승인한 MathEDU 실제 풀이 2개(id 13427, 8584)의 **문제와 풀이만** 예시로 준다. 오류 라벨/교사 설명은 넣지 않는다. 두 예시의 문제는 SFT train half-A 또는 예시 전용 pool에 두고 test에 포함하지 않는 안이다.
- judge 지시문은 두 예시를 참고하여 A/B 중 어느 문체가 실제 학생 풀이와 더 유사한지만 비교하도록 유지한다.

그룹 내 상대 학생다움 점수의 평균은 |G|≥2일 때 0.5다. 따라서 학습 로그의 전체 평균 보조 보상을 절대적인 학생다움 향상 지표로 사용하지 않는다. 최종 평가는 모델 간 출력의 직접 비교로 수행한다.

## 9. RL 하이퍼파라미터

| 항목 | 설정 | 상태 |
|---|---|---|
| Student 초기 모델 | Qwen/Qwen2.5-7B-Instruct | 비교 가능성을 위한 제안 |
| precision / attention | BF16 / SDPA | 저장소 최종 설정 |
| optimizer learning rate | 1e-6 | 확인 |
| epochs | 2 | 확인 |
| warmup / scheduler | 10% / linear decay | 확인 |
| rollout group size | 8 | 확인 |
| rollout temperature | 1.0 | 확인 |
| top_p / top_k | 1.0 / 비활성 | 확인. TRL 0, vLLM API -1 등 실제 의미를 adapter에서 통일 |
| repetition penalty | 1.0 | 확인 |
| max prompt / completion | 1024 / 1024 tokens | 출발값. 새 taxonomy prompt 길이 측정 필요 |
| per-device batch | 8 completions | 확인 |
| gradient accumulation | 2 | 확인 |
| training GPU 수 | 3 | 기존 7B용 구성 |
| effective batch | 48 completions = 6 조건 | 3 × 8 × 2; G=8 |
| beta / epsilon | 0.04 / 0.2 | 확인 |
| loss_type | dapo | 확인 |
| scale_rewards | group | 확인 |
| num_iterations | 1 | 확인 |
| max_grad_norm | 1.0 | 확인 |
| gradient checkpointing | true | 확인 |
| DeepSpeed | ZeRO-2 + CPU optimizer offload | 확인 |
| truncated completion mask | false | 확인. truncation 패널티의 gradient 유지 |
| vLLM IS correction | 활성, sequence_mask | 실행 기록에서 확인. 버전별 실제 설정 키 확인 후 명시 |
| bias-corrected KL | 활성 | 실행 기록에서 확인 |
| 모델 snapshot | 0.5 epoch마다 | 확인. 0.5/1.0/1.5/2.0 |
| 재개 checkpoint | 50 step마다, 전부 보관 | 저장 주기는 확인. 기존 최신 1개 rotation은 사용자 지시로 해제 |
| logging / seed | 매 step / 42 | 확인 |
| 평가 checkpoint 선택 | test에서 best 선택 | 사용자 확정. 구체 지표는 아래 제안 |

새 데이터에서 epoch당 step은 **새 train 조건 수에 따라 다시 계산**한다. 과거의 341 step/epoch, 총 682 step을 복사하지 않는다. 기준 구성에서는 대략 `조건 수 ÷ 6` optimizer steps/epoch이며 마지막 batch 및 sampler 처리에 따른 실제 값은 trainer가 기록한다.

GPU 수가 변하면 effective batch를 유지할 수 있는 per-device batch/accumulation 조합을 계산해 사용자와 확정한다. GPU를 늘리고 accumulation을 그대로 두어 실험마다 업데이트 수가 바뀌는 일을 피한다.

Student checkpoint 선택 지표는 **test의 half-B Joint success**를 우선 제안한다. 사용자가 기존 방식인 test 평균 reward를 유지하려면 그 지표로 고정한다. 어느 쪽이든 선택 지표를 먼저 확정하고 모든 checkpoint의 test 결과를 함께 보관한다. RM/Student 모두 test 선택에 따른 낙관성을 명시하며, validation 기반 선택을 도입하지 않는다.

### 9.1 API/serving 설정과 gpt-5-nano reasoning low

기존 실행에서 안정화한 수치를 출발점으로 삼되 새로운 호출 길이와 rate limit을 측정한다.

| 항목 | 설정 |
|---|---|
| answer grader 모델 / reasoning effort | **gpt-5-nano / low** — 사용자 확정 |
| student-likeness judge 모델 / reasoning effort | **gpt-5-nano / low** — 사용자 확정 |
| 두 API의 temperature | 명시하지 않음. Student/RM의 temperature와 별개 |
| answer grader max output / timeout / attempts | 8000 / 120초 / 6회 |
| 학생다움 judge max output / timeout / attempts | 8000 / 120초 / 6회 |
| 공유 API 연결 풀 keep-alive | 600초 |
| answer grader / style judge 동시성 상한 | 192 / 128 |
| A/B verifier max output / timeout / attempts | 10 / 120초 / 4회 |
| verifier 동시성 상한 | 256 |

실행 config의 두 역할에 각각 명시한다. 키 이름은 새 모듈의 계약 예시다.

```yaml
answer_grader:
  model: gpt-5-nano
  reasoning_effort: low
  temperature: null
  max_output_tokens: 8000

student_likeness_judge:
  model: gpt-5-nano
  reasoning_effort: low
  temperature: null
  max_output_tokens: 8000
```

`tutee_error/rl/src/tutee_rl/clients.py`에서 answer checker와 pairwise judge 모두 이 설정을 Responses 요청의 `"reasoning": {"effort": "low"}`로 전달하는 경로를 확인했다.[S7] 새 코드도 두 역할에 실제로 전달되는지 확인한다. 설정 파일에만 low를 적고 요청에서 빠뜨리지 않는다.

low는 reasoning의 노력 수준을 낮추는 설정이다. 답변 토큰 한도를 줄이거나 Student의 sampling temperature를 낮추라는 지시로 해석하지 않는다. 기존 최대 출력 8000은 우선 유지하며 reasoning 토큰, 최종 출력 토큰, 지연, 파싱 실패를 분리 기록한다. 사용 가능한 endpoint/model에서 오류가 나면 low를 조용히 제거해 기본값으로 실행하지 말고 원인을 기록한다.

이전 기본 reasoning 실행의 API 캐시는 low 실행과 공유하지 않는다. 모델, 프롬프트, reasoning effort와 출력 설정을 캐시 키/`run_meta.json`/`generation_meta.json`에 포함한다. 이 변경과 실제 전송값을 `rl/EXPERIMENTS.md`에 남긴다.

동시성은 상한이다. 48-rollout step의 실제 호출량과 오류율에 맞춰 조절한다. 계정의 지원 파라미터/모델 ID를 확인하며 적용하지 않은 temperature/seed를 적용했다고 기록하지 않는다.

## 10. 평가 설계

### 10.1 비교 모델

- 동일한 Qwen2.5-7B-Instruct의 학습 전 Base.
- Student-likeness RL의 test best checkpoint.
- Diversity RL의 test best checkpoint.
- gpt-5.6-sol 및 GPT-5.1 등 강한 API baseline: 실제 호출 가능한 모델 ID를 고정하고 같은 조건을 제공한다.

API baseline에도 문제별 상세 오답 경로를 제공하지 않는다. 모든 모델의 최종 비교는 기본적으로 조건당 8회 생성으로 맞춘다. 비용 때문에 1회 생성한 모델은 pass@8/그룹 실패율 비교에서 제외하고 sample success만 별도 표기한다.

### 10.2 별도 학습한 half-B verifier로 평가

Student test 생성물은 gpt-5-nano로 정오를 판정하고 **오답만 B에 n=2, T=0.6으로 검증**한다. A는 RL 보상용이고 B는 Student test와 baseline 평가용이다. 학습 중 로그의 A 성공률과 최종 표의 B 성공률을 이름부터 구분한다.

B는 새 taxonomy의 half-B로 별도 SFT한 checkpoint를 사용한다. 기존 descriptive half-B 모델이나 A checkpoint를 이름만 바꿔 평가하지 않는다. B는 RL reward endpoint에서 호출하지 않는다. 테스트를 통한 Student checkpoint 선택에는 B가 관여하므로 ‘모델 선택에도 사용하지 않은 평가기’라고 부르지 않는다.

A/B 데이터 분리는 공유된 taxonomy나 annotation 오류를 제거하지 않는다. 두 모델이 높은 수락률을 보인다는 이유만으로 정확성을 입증하지 않는다. A/B 불일치 예시와 오류 유형별 결과를 보고하고, 추가 API judge/사람 검수는 필요 범위를 사용자와 정한 뒤 시행한다.

### 10.3 보고 지표

| 지표 | 정의/분모 |
|---|---|
| Wrong rate | 전체 생성 풀이 중 최종 답이 오답인 비율 |
| A acceptance given wrong | 오답 중 보상 RM A가 2/2 aligned로 수락한 비율 |
| B acceptance given wrong | 오답 중 test verifier B가 2/2 aligned로 수락한 비율 |
| B Joint success | 전체 풀이 중 오답이며 B 2/2 aligned인 비율 |
| A/B disagreement | 같은 오답에 대한 A/B 통과 판정 불일치율 |
| 유형별/단계별 성공률 | 목표 E와 N별로 B Joint success를 묶어 보고 |
| Student likeness | 모델 간 A/B 후보 직접 비교의 승률/무승부율 |
| Diversity | 성공 풀이 내 BLEU 기반 다양성 및 고유 풀이 수 |
| Zero-success group | 조건당 8회 중 B 성공 풀이가 0개인 비율 |
| Null/truncation/invalid | 각각 별도 집계 |

binary verifier는 N/E 조합의 정렬 여부 하나를 출력한다. 별도 단계 판정 실험 없이 ‘Newman 단계만의 정확도’나 16개 유형 분류 정확도를 계산한 것처럼 보고하지 않는다. 유형별/단계별 표는 **목표 조건별로 나눈 binary 성공률**이다.

A/B 불일치는 어느 쪽이 틀렸는지의 정답 라벨이 아니다. RL 생성물의 ‘RM false acceptance’, ‘추가 오류’, ‘오류 해설’ 비율은 독립 검수가 있는 표본에서만 별도로 계산하고 검수 방식/표본 수를 적는다. 고정 SFT test에서의 negative false acceptance와도 구분한다.

전체 micro 평균과 원본 유형별 macro 평균을 함께 제시한다. 단위 변환 허용/그 외 질문의 성능도 나눈다. ‘단위 변환 조건을 허용 질문에만 줬다’는 평가 조건을 표에 명시한다.

신뢰구간은 **질문 그룹 단위 paired bootstrap**으로 계산한다. 같은 Q의 여러 조건과 8개 rollout을 한 묶음으로 resample한다. 1000회 bootstrap을 출발값으로 사용한다. 이 구간은 선택된 checkpoint를 고정한 평가 표본의 불확실성이며, test로 best를 선택한 낙관성이나 반복 학습 seed 분산을 해결하지 않는다.

학생다움 비교에서는 evaluator 모델 A/B와 후보 A/B를 혼동하지 않게 필드명을 구분한다. 동일 조건의 Base/RL 출력을 직접 비교하되 두 출력이 B 기준으로 조건을 충족하는 쌍의 승률과 비교 가능 표본 수를 보고하는 안이다. 전체 조건 충족률도 나란히 제시한다.

## 11. 실행 환경과 자원

### 11.1 7B 기준

- A/B full SFT: 7B 기준 A100 80GB 1장 + CPU optimizer offload를 출발점으로 순차 실행한다. B의 8B backbone은 별도 smoke에서 메모리 여유를 확인한다.
- RL: 학습용 3장과 rollout/RM serving용 1장의 총 4장 구성을 출발점으로 한다.
- 기존 serving은 한 GPU에 rollout 메모리 비율 0.50, RM 0.35를 사용했다. 새 N/E 정의 길이와 binary 출력에 맞춰 실제 KV cache 여유를 확인한다. B는 RL 보상 서버에 함께 상주시킬 필요가 없고 test 시 별도로 로드한다.
- 기존 SFT README에 CPU RAM 사용 약 229 GiB와 컨테이너 한도 384 GiB가 보고돼 있다. GPU 여유만 보고 여러 full SFT를 동시에 시작하지 않는다. 새 run의 peak RAM을 측정한다.
- 기존 7B 재개 checkpoint가 약 114 GB였다는 기록을 참고해 가중치 저장과 optimizer 재개 저장을 분리한다. 새 저장량은 실측한다. 모든 checkpoint 보관 방침에 따라 저장 횟수 × 실제 용량으로 디스크 요구량을 산정하고 자동 삭제하지 않는다.

### 11.2 환경 고정

확인한 저장소 lock의 주요 버전:

| 구성 | SFT 환경 | RL 환경 |
|---|---|---|
| torch | 2.11.0+cu128 | 2.13.0+cu129 |
| transformers | 5.17.0 | 5.17.0 |
| DeepSpeed | 0.19.7 | 0.19.7 |
| accelerate | 1.15.0 | 1.15.0 |
| TRL | 별도 Trainer SFT | 1.14.0 |
| vLLM | 미사용 | 0.30.0+cu129 |
| openai | 3.19.2 | 3.20.0 |
| sacrebleu | 미사용 | 2.6.0 |

이는 저장소에서 확인한 기록이며 여기서 해당 GPU 환경을 새로 실행 검증한 것은 아니다. 각 작업의 lock을 별도 환경으로 재현한 뒤 import, 단일 forward/backward, vLLM weight sync를 확인한다. 새 환경에 맞춰 바꾼 버전은 별도 lock으로 남긴다.

이전 질문의 Qwen3-30B-A3B-Instruct-2507은 아직 이번 RM이나 Student의 확정 모델로 지정되지 않았다. 이를 선택하면 모델 교체 실험으로 분리하고 ZeRO-3/FSDP, 병렬화, 배치와 자원을 다시 정한다. 7B용 1장/4장 설정을 그대로 적용하지 않는다.

## 12. 제안 코드 구조

아래 경로는 신규 구현 대상이며 아직 실행한 코드가 아니다.

| 경로 | 역할 |
|---|---|
| `newman_experiment/configs/taxonomy.yaml` | 영석 분류 16개, 제외 10개, source alias, 정의/표 provenance |
| `configs/data.yaml` | 원본/MathQA/GSM8K 경로, 기존 ok 필터, 질문 그룹 80:20/half 설정 |
| `configs/verifier_half_a.yaml` | 보상 RM A full SFT |
| `configs/verifier_half_b.yaml` | test verifier B full SFT |
| `configs/rl_common.yaml` | Student/GRPO, API 두 역할의 reasoning_effort=low |
| `configs/student_likeness.yaml` | 학생다움 실험 |
| `configs/diversity.yaml` | 다양성 실험 |
| `configs/evaluation.yaml` | B checkpoint, test 생성/채점/신뢰구간 |
| `prompts/*.txt` | binary verifier, Student, answer grader, style judge |
| `src/data_adapters.py` | 네 원본 로더와 Q 복원 |
| `src/taxonomy.py` | source label resolver, 영석 분류 매핑 |
| `src/unit_eligibility.py` | 기존 인덱스 보정, Q 대조, 허용 여부 lookup |
| `src/data_prepare.py` | 품질 필터, 전역 Q 그룹, split/half, 길이 검사 |
| `src/negative_sampling.py` | 다른 E' 선택, N'=mapping(E'), 단위 후보 제한, 고정 seed |
| `src/verifier_format.py` | N/E 조건 입력, assistant-only mask, 정확 일치 parser |
| `src/verifier_client.py` | A/B endpoint 분리, n=2 호출과 캐시 |
| `src/rewards.py` | 정오 → A 정렬 → 보조 보상 |
| `src/evaluate.py` | 정오 → B 정렬, 지표와 paired bootstrap |
| `scripts/prepare_data.py` | mapping/split/half/negative/eligibility audit |
| `scripts/train_verifier.py` | --role reward/test와 각 half config로 별도 SFT |
| `scripts/eval_verifier.py` | 동일 SFT test의 binary 평가 |
| `scripts/train_student.py` | GRPO |
| `scripts/eval_student.py` | 모든 checkpoint의 B 기반 test 및 best 선택 |
| `manifests/` | 원본 해시, 전역 split/half, 고정 negative, unit allowlist, 제외 사유 |
| `outputs/` | run별 생성/판정/점수/metadata/checkpoint |

verifier 캐시 키에는 **Q, S, target N/E**, taxonomy/프롬프트 해시, role A/B, checkpoint, decoding, replicate index를 포함한다. 같은 Q/S에 다른 target E를 붙인 판정은 다른 요청이다. A/B 캐시는 공유하지 않는다. n=2의 두 샘플이 캐시 때문에 한 응답의 복사본이 되지 않게 한다.

API 캐시는 model ID, reasoning effort, 출력 설정, 예시/프롬프트 해시를 포함하고 style judge는 후보 순서도 포함한다. 두 judge의 raw response/usage/request ID를 보존한다. 재개 시 같은 조건의 캐시만 재사용한다.

## 13. 구현과 실행 순서

1. **재라벨링 반영:** 최신 D열을 파싱하고 16개 포함/10개 제외 및 원본 라벨 보존을 검증한다.
2. **단위 허용 목록 준비:** GSM8K 기존 목록을 Q 해시로 변환한다. 미확인 SFT용 목록의 파일/경로를 찾고, 없으면 데이터 준비의 미완료 항목으로 보고한다.
3. **data audit:** 기존 품질 필터, 전역 Q 중복, 80:20, train half-A/B, 입력 길이를 확정한다. RL test와 SFT train의 겹침도 제거한다.
4. **negative 생성:** 각 영역 안에서 1:1 쌍을 만든다. 유형별/half별 수와 단위 restriction, 후보 없음 사유를 보고한다.
5. **연구 설정 확정:** 남은 프롬프트 문구, backbone, RL 조건 수/배분, checkpoint 선택 지표를 사용자와 확정한다. 이미 정한 half/단위 제한/low를 다시 승인 요청하지 않는다.
6. **mock 및 smoke:** binary parser, loss mask, split/half 누출, reward 분기, API low 실제 전송, 저장/복원 확인. 각 backbone은 짧은 SFT smoke로 점검한다.
7. **A/B 본 SFT:** 각자의 공개 backbone에서 각각 최대 5 epoch. 모든 checkpoint 저장 후 test 지표로 각 best를 선택한다.
8. **reward 경로 점검:** Student 생성물에 정오 → A 2회 → aux 경로 적용. B test 판정과 구분해 지표를 기록한다.
9. **Student-likeness RL:** 2 epoch, 0.5 epoch마다 모델 저장/test 평가.
10. **Diversity RL:** 같은 초기 Student와 동일 조건 manifest, 보조 항만 바꾼다.
11. **최종 비교:** 각 test best, Base, API baseline을 같은 Q/N/E와 B 기준으로 비교한다. 모든 checkpoint 결과와 test 선택 사실을 함께 보고한다.

핵심 검증 항목:

- D열 ‘제외’가 원본/negative/RL 조건에서 모두 빠지는가.
- EIC와 Stepwise의 Unit conversion 라벨을 잘못 합치지 않았는가.
- A/B/test 간 같은 질문과 그 파생 풀이가 섞이지 않는가.
- negative의 E는 원래 E와 다르고 N은 그 E의 매핑과 일치하는가.
- 단위 negative/RL 조건은 확인된 허용 Q에만 배정되는가.
- 라벨별 positive/negative가 모두 있으며, 단위 negative 0건 같은 공백을 숨기지 않는가.
- verifier input에 target 조건은 들어가고 원본 정답 라벨/paired label은 새지 않는가.
- `not_aligned`를 `aligned`로 오인하지 않는가.
- RL 호출은 A, Student test 호출은 B인지 실제 checkpoint ID로 확인하는가.
- gpt-5-nano 두 역할 모두 요청에 low가 포함되고 이전 캐시와 분리되는가.
- 정답/null/오답, verifier 불통과, truncation, |G|=0/1/2/8 보상이 정의와 맞는가.

run 이름은 `<experiment>_seed42_<YYYYmmdd_HHMMSS>`. 예를 들어 `verifier_half_a`, `verifier_half_b`, `newman_student_likeness`, `newman_diversity`를 experiment prefix로 사용한다. 실행 설정 변경과 결과는 `rl/EXPERIMENTS.md`에 실제 metadata를 근거로 기록한다.

## 14. 확정 사항과 남은 확인 사항

**이미 확정되어 재질문하지 않을 항목**

- 최신 파일의 영석 분류를 적용하고 원본 유형을 보존한다.
- RM A와 평가 verifier B를 각각 다른 학습 half로 SFT한다.
- 같은 Q/S에 다른 원본 유형을 붙이는 binary negative를 만들고 두 단위 유형은 허용 Q에만 배정한다.
- GSM8K의 기존 단위 변환 허용 목록을 활용한다.
- gpt-5-nano는 answer grader/style judge 모두 reasoning effort=low.
- train:test=8:2, validation 없음, 모든 checkpoint 보관, test에서 best 선택.
- 기존 두 보조 보상 실험과 각 0.5 가중치, answer 태그 제거, n=2 verifier 호출을 유지한다.

**실행 전 남은 자료/설계 확인**

| 항목 | 현재 계획의 처리 |
|---|---|
| 별도로 골라 둔 SFT 단위 허용 Q 목록 | 현재 main에서 미확인. 로컬/다른 기록의 파일 경로 확인 필요. GSM8K 목록으로 정확히 연결되는 Q만 우선 판정 |
| C 생성 이력이 없는 원본의 포함 범위 | 기존 ok-only 합의를 자동 해제하지 않음. 새로 확장할 풀의 규모를 제시하고 결정 |
| A/B backbone | A Qwen2.5-Math-7B, B DeepSeek-R1-0528-Qwen3-8B를 기존 구성에 맞춘 초안으로 둠 |
| GSM8K 원본 범위/조건 배정 | 원본 train만 vs train+test, Q당 조건 수, 유형별 균형은 audit 후 확정 |
| Student/verifier/answer/style 프롬프트 | 새 N/E를 받는 문구와 정의를 실제 텍스트로 제시해 승인. 기존 승인된 스타일 원칙은 유지 |
| checkpoint 선택 지표 | SFT binary macro-F1, Student B Joint success를 제안. test를 쓰는 원칙은 확정 |

자료가 없는 부분을 구현 완료로 표시하거나 연구 설계를 임의로 채우지 않는다. 위 확인과 무관한 parser, manifest, 스크립트, 환경/연결 검증은 먼저 준비할 수 있다.

## 15. 출처

- [S1] SFT 설정: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/verifier_sft/config/descriptive_verifier_v2.json
- [S2] SFT 구현: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/verifier_sft/train_descriptive_verifier.py
- [S3] SFT 환경/운영 기록: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/verifier_sft/README.md
- [S4] RL 최종 설정: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/rl/configs/common.yaml
- [S5] RL 실제 실행 기록: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/rl/EXPERIMENTS.md
- [S6] RL 구현: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/rl/scripts/train.py
- [S7] API 요청 구현: https://github.com/WooYoungSeok/tutee_error/blob/a95df533902332310d3d629ed7ace423980cdf0d/rl/src/tutee_rl/clients.py
- [R1] Negative/프롬프트 구현: https://github.com/WooYoungSeok/llm_tutee_tutor/blob/972f0c3866a48520c87c254f45dcd9c875da8797/finetuning/train_new_label_0622.py
- [R2] GSM8K 단위 변환 허용 목록/인덱스 보정: https://github.com/WooYoungSeok/llm_tutee_tutor/blob/972f0c3866a48520c87c254f45dcd9c875da8797/RL_new_cluster_2prm_0623/data/fix_labels.py
- [R3] base 정답 문제 subset용 별도 코드: https://github.com/WooYoungSeok/llm_tutee_tutor/blob/972f0c3866a48520c87c254f45dcd9c875da8797/RL_new_cluster_2prm_0623/data/build_train_subset.py
- [M1] 최신 사용자 매핑표: Newman_relabeling_영석_마무리 (1)(1).xlsx, Newman 재분류 시트 D열. 2026-09-30 업로드본, SHA-256은 2.2절. 원본 파일은 수정하지 않았다.
- [N1] White, A. L. (2009). A Revaluation of Newman's Error Analysis. https://www.mav.vic.edu.au/Tenant/C0000019/00000001/downloads/Resources/annual-conferences/2009/08White.pdf

이 계획서는 코드와 실험을 이미 수행했다는 보고서가 아니다. 기존 설정의 확인 결과와 새 설계 제안을 구분하여 기록한 구현 명세다.
