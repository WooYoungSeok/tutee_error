# 수학 오류 묘사 C 생성 파일럿

문제 Q, 오답 풀이 R, 원래 오류 라벨 A를 입력으로 받아 짧고 재사용 가능한 자연어 오류 묘사 C를
만드는 파이프라인이다. 상위 taxonomy로 재분류하지 않고, 원본 라벨은 문자열 그대로 보존한다.

verifier / policy 학습은 이 저장소 범위가 아니다.

## 현재 상태 (요약)

| 단계 | 상태 |
| --- | --- |
| 코드 구현 | 완료 (어댑터, 샘플링, 프롬프트 렌더링, API runner, 재개, 검수표) |
| 데이터 확보 | 4개 데이터셋 + MathEDU 질문 출처(MathQA) 확보 완료 |
| 샘플링 | **200개 고정** (데이터셋별 50개, dev 10 + holdout 40) |
| dry-run / mock 검증 | 완료 (네트워크 호출 없음) |
| 실제 API 실행 | **dev 40건 × 프롬프트 v1–v4 (gpt-5.4-mini) + v4 × 모델 5종 완료**, holdout 160건은 검토 후 |
| 전체 라벨링 | **완료: 적격 풀 전체 3,986건 모두 ok** (gpt-5.6-luna, 프롬프트 v4, 약 $1.58) → `data/labeled/` (아래 "전체 라벨링") |
| Verifier SFT | 데이터 준비·형식 점검 완료, 학습·평가는 서버에서 → `verifier_sft/README.md` |

자세한 내용은 `reports/data_inspection.md`, `reports/handoff_status.md` 참고.

## 설치

```bash
pip install -r requirements.txt
```

인증은 환경변수로 한다. 키를 저장소나 로그에 넣지 않는다.

```bash
cp .env.example .env   # 그리고 .env 안에서 OPENAI_API_KEY 값을 채운다 (.env는 git 제외)
```

## 실행 순서

```bash
python scripts/fetch_sources.py                 # 원자료 내려받기 + SHA-256/리비전 기록
python scripts/build_samples.py                 # 정규화, 점검 보고서, 200개 표본 고정
python scripts/run_generation.py --split dev --dry-run   # 호출 없이 요청 내용 확인
python scripts/run_generation.py --split dev --mock      # 호출 없이 파이프라인 전체 확인
python scripts/run_generation.py --split dev                  # 1차 유료 실행 (dev 40건)
python scripts/make_review.py v1__gpt-5.4-mini__dev           # 사람이 볼 검수표 + 요약
python scripts/run_generation.py --split holdout              # dev 검토 후 별도 명령
```

`scripts/list_models.py`는 키로 볼 수 있는 모델 ID 목록만 확인한다(생성 과금 없음).
가격은 이 엔드포인트로 알 수 없으므로 공식 가격 페이지에서 확인한 값을 dry-run에
`--price-input`, `--price-output`으로 넘겨야 비용 추정이 나온다.

### 모델 설정

현재 `config/pilot.json`의 `model`은 `gpt-5.4-mini`이고, `--model`로 바꿔 실행한다.
호출은 세 모델 모두 Responses API(`client.responses.create`, `POST /v1/responses`)를 쓴다.

| 모델 | 성격 | reasoning.effort | 단가(입력/출력, 1M) |
| --- | --- | --- | --- |
| `gpt-5.4-mini` | mini 계열 | 이번 실행에서 reasoning 토큰 0 | $0.75 / $4.5 |
| `gpt-5.6-luna` | 저비용·고속 | none–max, 기본 medium | $0.2 / $1.2 |
| `gpt-5.6-terra` | 범용 균형 | none–max, 기본 medium | $2 / $12 |
| `gpt-6-sol` | 복잡한 작업용 | none–max, 기본 medium | $2 / $10 |
| `gpt-6-luna` | 고빈도 작업용 최경량 | none–max, 기본 medium | $0.1 / $0.5 |

reasoning 토큰은 출력으로 과금되고 `max_output_tokens`에 포함된다(현재 2000, 잘림 없음).
계정 모델 목록에 `gpt-5.5-mini`는 없다(`gpt-5.5`, `gpt-5.5-pro`는 있음).

`model`은 반드시 명시해야 한다(`config/pilot.json` 또는 `--model`). 설정이 없으면
API 호출 없이 오류로 끝나고, 데이터 준비와 dry-run은 그대로 동작한다. 비싼 모델로
자동 대체(fallback)하지 않는다.

지원하지 않는 파라미터는 보내지 않는다. `temperature`, `reasoning_effort`,
`response_format_json`은 설정했을 때만 요청에 포함된다.

## 디렉터리

```
prompts/error_description_v1.txt   사용자 확정 프롬프트 v1 (수정 금지, 아래 hash 참고)
prompts/error_description_v2.txt   사용자 확정 프롬프트 v2 (비교 실행용, 수정 금지)
prompts/error_description_v3.txt   사용자 확정 프롬프트 v3 (비교 실행용, 수정 금지)
prompts/error_description_v4.txt   사용자 확정 프롬프트 v4 (비교 실행용, 수정 금지)
config/pilot.json                  seed, 표본 수, 모델, 생성 파라미터
config/full.json                   전체 라벨링 설정 (모델, 프롬프트, EIC 벤치마크)
src/errdesc/                       sources, adapters, sampling, prompt, runner, validate, review, fullpool, export
scripts/                           fetch_sources / build_samples / run_generation / make_review / compare_runs / list_models / build_full_pool / export_labels
data/raw/                          원자료 원본 + source_manifest.json (URL, revision, SHA-256)
data/normalized/                   데이터셋별 정규화 레코드 (제외 사유 포함)
data/manifest/                     고정된 표본 manifest + meta
data/full/                         전체 라벨링 요청 풀 + 레코드 인덱스
data/labeled/                      raw 사본 + generated_error_description (전체 라벨링 결과)
outputs/runs/<run_id>/             raw.jsonl(원문 응답 포함), parsed.jsonl, run_meta.json
reports/                           데이터 점검 보고서, 검수 CSV/HTML, 실행 요약
tests/                             네트워크 없는 검증 (53개)
```

프롬프트 SHA-256
- v1: `1b3c182347176be6b65945aece0523d6911f8f7763e960f21d00d24975d59a0a`
- v2: `15f304a7be10cace7508c323ddd41c0ad94d8d332bae7eb41f3b90d4decfd772`
- v3: `86e57f4075105fa37c5fbab216c7dd909b97d2167b62176edf10c7b32c8d611e`
- v4: `28ef5467bbbac5cec81290d4f0bd9d7cf83d2efe80efe1f858600916cb4f0a7c`

다른 버전으로 돌릴 때는 config를 고치지 말고 `--prompt-file`을 쓴다. run id가
`v2__<model>__<split>`로 분리되어 기존 결과를 덮어쓰지 않는다.

```bash
python scripts/run_generation.py --split dev --prompt-file prompts/error_description_v4.txt
python scripts/run_generation.py --split dev --model gpt-5.6-luna --prompt-file prompts/error_description_v4.txt
# 여러 run을 한 표로 비교 (baseline 먼저, 몇 개든 가능; 열 이름은 달라지는 부분만 남는다)
python scripts/compare_runs.py v1__gpt-5.4-mini__dev v2__gpt-5.4-mini__dev v3__gpt-5.4-mini__dev v4__gpt-5.4-mini__dev
python scripts/compare_runs.py v4__gpt-5.4-mini__dev v4__gpt-5.6-luna__dev v4__gpt-5.6-terra__dev v4__gpt-6-sol__dev v4__gpt-6-luna__dev --out-name compare_v4_models
# 검수표에 다른 run의 C를 열로 누적
python scripts/make_review.py v4__gpt-5.4-mini__dev --compare-run v1__gpt-5.4-mini__dev v2__gpt-5.4-mini__dev v3__gpt-5.4-mini__dev
```

## 전체 라벨링 (표본이 아닌 적격 풀 전체)

200개 고정 표본과 별개로, 적격 레코드 전체에 C를 붙인다. 설정은 `config/full.json`
(gpt-5.6-luna, 프롬프트 v4, JSON 모드, `max_output_tokens` 4000, 동시성 6).

```bash
python scripts/build_full_pool.py                                            # data/full/ (호출 없음)
python scripts/run_generation.py --config config/full.json --source full --dry-run --price-input 0.2 --price-output 1.2
python scripts/run_generation.py --config config/full.json --source full     # 재개 가능, 같은 명령 반복
python scripts/make_review.py v4__gpt-5.6-luna__full                         # 요약·검수표
python scripts/export_labels.py                                              # data/labeled/
```

범위:

| 데이터셋 | 대상 | 고유 호출 |
| --- | --- | --- |
| MathEDU | 파일럿과 같은 적격 풀 | 888 |
| Stepwise | 파일럿과 같은 적격 풀 | 766 |
| MathClean | 파일럿과 같은 적격 풀 | 610 |
| EIC | `generated_cases_GSM8K` + `generated_cases_MathQA`의 9개 오류 유형 | 1,722 |

- EIC에서 `wrong_step_calculation_error`(오류 단계 위치 실험)와 9개 유형 밖의 비정규 라벨은
  파일럿과 같이 제외한다. EIC 저장소의 `incomplete_generated_cases_*`(같은 사례를 오류 단계에서
  자른 것), `step_number_cases_*`(calculation_error 단계 수 실험), `EP_robustness_testing_cases_*`
  (정답/오답 판별용; 오답은 generated_cases_MathQA의 복사본, 두 폴더가 바이트 동일)는 받지 않는다.
- 문제·풀이·라벨이 같은 레코드(`sample_id` 동일)는 한 번만 호출하고 결과를 공유한다.
- EIC 어댑터의 기본값은 GSM8K만이므로 `build_samples.py`와 200개 표본은 바뀌지 않는다.

출력 (`data/raw`는 읽기만 한다):

- `data/labeled/<dataset>/...` — 어댑터가 읽은 raw 파일마다 같은 경로·형식의 사본. 각 행에
  `generated_error_description` 키 하나만 추가된다(이 키를 빼면 원본과 바이트 단위로 같다).
  - 라벨이 붙은 행: `{"labeled": true, "description", "status", "evidence_quote", "sample_id", "run_id"}`
  - 나머지: `{"labeled": false, "reason": <제외 사유 또는 not_generated:<처리 상태>>}`
  - MathEDU `leave_one_out/*`는 `time_series_split` 행의 완전 복사본이므로 그 행의 라벨을 그대로 붙인다.
  - Stepwise 원본에는 이미 `error_description` 필드가 있어 키 이름을 따로 두었다.
- `data/labeled/labels.jsonl`, `labels.csv` — 고유 사례당 한 행(Q, R, A, C, status, evidence, source ids).
- `data/labeled/export_meta.json` — run, 모델, 프롬프트 hash, 파일별·데이터셋별 집계.

`status`가 `label_conflict`/`ambiguous`인 사례도 지우지 않고 그대로 둔다(v4는 이때 description을
null로 강제하지 않는다). 걸러 쓸지는 사용 단계에서 정한다.

## 데이터 매핑

| 데이터셋 | Q | R | A | 검수용 |
| --- | --- | --- | --- | --- |
| MathEDU | MathQA `Problem` (레코드 `id`로 조인) | `student_process` | `teacher_review.error[0].error_type` | student_id, student_answer, error_equation, teacher_advice_en/ch, MathQA options/correct/category/Rationale |
| Stepwise | `problem` | `student_incorrect_solution` (리스트를 줄바꿈으로 연결, 원본 리스트 보존) | `error_category` | incorrect_index, incorrect_step, error_description, reference_solution, dialog_history, student_correct_response |
| MathClean | `question` | `answer` (평가 대상 풀이이며 정답 풀이가 아님) | `type` | extent, 난이도 파일 |
| EIC | `question` | `transformed_solution` | `wrong_type` | original_solution, original_answer, transformed_answer, wrong_step, explanation, is_single_error |

API 요청에는 Q, R, A 세 항목만 들어간다. annotations와 원본 raw 레코드는 보내지 않는다.

MathEDU 레코드에는 문제 본문이 없다. `id`는 MathQA의
`concat(train, validation, test)` 인덱스이며(저장소의 `create_finetuned_data.py`와 동일),
`scripts/fetch_sources.py`가 MathQA 원본(37,297문제)을 함께 받아 Q를 붙인다.
정답 답안, 빈 풀이, 교사 오류가 2개 이상인 레코드는 제외하고 사유를 기록한다.

## 표본 규칙

- 시드 42(`config/pilot.json`에서 변경 가능), 데이터셋별 50개, 원래 라벨별 균등 층화.
- 부족한 층은 있는 만큼만 쓰고 남는 수를 결정론적으로 재배분한다. 복제는 하지 않는다.
- 한 문제(question group)당 한 사례. 데이터셋 사이 중복도 한 번만 쓰고 보고한다.
- dev 10 / holdout 40. 같은 문제가 dev와 holdout에 나뉘어 들어가지 않는다.
- 표본은 고정이다. 프롬프트를 고쳐도 다시 뽑지 않는다.

## 재개와 재시도

- 같은 `sample_id + 입력 hash + 프롬프트 hash + 모델 + 생성 설정`으로 성공한 요청은 다시 호출하지 않는다.
- 잘린 응답(`incomplete`)과 JSON 오류는 성공으로 저장하지 않으므로 다음 실행에서 다시 시도한다.
- 429/타임아웃/일시적 서버 오류만 backoff 재시도한다. 인증·모델 ID·파라미터 오류는 즉시 중단된다.
- 시도별 response id와 request id를 저장한다. 타임아웃 후 재시도는 중복 과금 가능성이 있으므로
  exactly-once를 보장한다고 말하지 않는다.

## 검수

`scripts/make_review.py <run_id>` 는 다음을 만든다.

- `reports/review_<run_id>.csv` (Excel용 utf-8-sig) — dataset, sample_id, split, Q, R, A, C,
  evidence_quote, status, 기존 annotation, 자동 플래그, 검토 의견 칸 3개 + 자유 서술.
  `--compare-run <run_id> [<run_id> …]`를 주면 각 run의 C가 오른쪽에 순서대로 한 열씩 추가된다
  (설명이 없으면 `(no description: <status>)`). 이때 그 run 자신의 열 이름도
  `description__<run_id>`로 바뀌어, 모든 C 열이 어느 run의 결과인지 드러난다.
- `reports/review_<run_id>.html` — 같은 내용을 읽기 쉽게.
- `reports/summary_<run_id>.md` — 상태 비율, 길이 분포, 중복 C, 토큰/오류 요약.

자동 플래그(길이, 숫자 포함, 문제와 공유하는 단어, evidence 원문 확인 실패, 중복 C)는
검토 표시일 뿐 정답 판정이 아니다. 같은 C가 여러 문제에 나오는 것은 목표에 부합할 수 있다.
모델 응답 원문은 어떤 경우에도 수정하지 않는다.

## 테스트

```bash
python -m pytest tests -q -p no:cacheprovider
```

네트워크를 쓰지 않는다(53개). 데이터별 필드 매핑, 표본 중복·분할 누출, placeholder 치환 안전성,
JSON/null 검증, 재개 시 중복 호출 방지, 잘린 응답 처리, 재시도/치명적 오류 구분, 전체 풀 중복 제거,
EIC 벤치마크 선택, 내보내기의 행 대응·원본 보존을 확인한다.

Windows에서 프로젝트가 `문서`/`바탕 화면` 아래에 있고 "제어된 폴더 액세스"가 켜져 있으면
python의 파일 쓰기가 `FileNotFoundError [WinError 2]`로 막힌다. python.exe를 허용 앱에 추가해야
한다(`-p no:cacheprovider`는 pytest 캐시 쓰기를 피하기 위한 것).

## 출처 주의

MathEDU만 실제 학생 풀이다. Stepwise, MathClean, EIC는 모델이 만든 풀이를 포함한다.
네 데이터셋을 묶어 "실제 학생 데이터"라고 설명하지 않는다.
