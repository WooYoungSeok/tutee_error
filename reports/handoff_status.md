# 파일럿 진행 상태 보고 (2026-09-23, 프롬프트 v1–v4 및 모델 5종 dev 실행 후 · 전체 라벨링 완료는 9절)

## 1. 완료 여부 구분

| 항목 | 상태 |
| --- | --- |
| 코드 구현 | 완료 (테스트 44개 통과) |
| 데이터 확보 | 완료 (MathEDU 포함 4개 + 질문 출처 MathQA) |
| 샘플링 | 완료 — 200개 고정 (데이터셋별 50, dev 40 / holdout 160) |
| dry-run / mock 검증 | 완료 |
| 실제 API 실행 | **dev 40건: 프롬프트 v1–v4 (gpt-5.4-mini) + v4 × 모델 5종**. holdout 160건은 검토 후 대기 |

## 2. 모델 선택

- 계정 모델 목록에 `gpt-5.5-mini`는 **없다**. `gpt-5.5`, `gpt-5.5-pro`는 있고 mini 계열의
  최신은 `gpt-5.4-mini`다. 사용자 확인 후 `gpt-5.4-mini`로 확정했다.
- 호출 지점: OpenAI **Responses API** (`POST /v1/responses`, SDK `client.responses.create`).
  요청은 `model`, `input`(user 메시지 1개), `max_output_tokens`만 보낸다.
  `temperature`, `reasoning`, `text.format`은 설정했을 때만 포함하며 지금은 보내지 않는다.
- dev 실행에서 `reasoning_tokens`는 0이었고 잘린 응답도 없었다(`max_output_tokens` 2000).
- 인증: 프로젝트 `.env`의 `OPENAI_API_KEY`. 셸에 남아 있던 옛 키가 401을 내서, 프로젝트
  `.env`가 환경변수보다 우선하도록 고쳤다(어떤 변수를 .env에서 읽었는지만 출력하고 값은
  출력하지 않는다). `.env`는 `.gitignore`에 있다.

## 3. 데이터 접근 결과

파일별 URL, 리비전, 바이트 수, SHA-256은 `data/raw/source_manifest.json`에 있다.

| 데이터셋 | 출처 | 리비전 | 파일 | 적격 사례 |
| --- | --- | --- | --- | --- |
| MathEDU | github.com/NYCU-NLP-Lab/MathEDU | `acb1873f1569048d72c90855febc6f367b1e3356` | 22 | 890 / 4,048 |
| MathQA(질문 출처) | math-qa.github.io MathQA.zip | zip sha256 `7344f304…2f07a` | 3 | 37,297 문제 |
| Stepwise | github.com/eth-lre/verify-then-generate | `161019e6cc29968bb9a9ae7f261daf63f00e6fc7` | 1 | 915 / 1,002 |
| MathClean | huggingface MeiyiQiang/MathClean | `27e7028b31196cca06c62686b69ab4d1040a11d3` | 8 | 610 |
| EIC | github.com/LittleCirc1e/EIC | `be8132a826dd7890d5ba92bd0c87451a3275874a` | 34 | 898 / 1,300 |

### MathEDU (알려주신 저장소로 해결)

- 논문이 안내한 anonymous 저장소는 지금도 `410 repository_expired`다. 알려주신
  `NYCU-NLP-Lab/MathEDU`에서 받았다.
- **이 데이터에는 문제 본문이 없다.** 레코드의 `id`가 MathQA 인덱스이며, 저장소의
  `create_finetuned_data.py`가 `concatenate_datasets([math_qa train, validation, test])`로
  붙인 순서를 쓴다. 같은 방식으로 MathQA 원본(train 29,837 + dev 4,475 + test 2,985 = 37,297)을
  받아 Q를 붙였다. README 예시(id 9420 = DE:BC 삼각형 문제)와 일치함을 확인했고 테스트로 고정했다.
- 매핑: Q = MathQA `Problem`, R = `student_process`, A = `teacher_review.error[0].error_type`.
  MathQA `options`, `correct`, `category`, `Rationale`와 교사 첨삭(`error_equation`,
  `teacher_advice_en/ch`), `student_id`는 검수용으로만 보존한다. 지시문의 "Problem → Q"에 따라
  보기(options)는 Q에 넣지 않았다.
- 파일 구성: `time_series_split`(train/val/test 합계 4,048개, 전부 고유)을 풀로 썼다.
  `leave_one_out`은 같은 데이터를 학생별로 다시 나눈 것이라 중복이며(24,288행, 고유 3,959개,
  time_series의 부분집합) 사용하지 않았다.
- 제외: 정답 3,050, 학생 풀이가 빈 문자열 82, 오류가 2개 이상 기록된 레코드 26.
  오류가 여러 개면 A가 한 개의 원래 라벨이 아니게 되므로 합치지 않고 제외하고 보고한다.
- **오류 유형이 지시문의 5개가 아니라 실제로는 8개다.** 문자열을 덮어쓰지 않고 그대로 썼다:
  Wrong mathematical operation/concept 437, Comprehension error 169, Unfinished answer 116,
  Arithmetical error 73, Algebraic error 41, Careless error 28,
  Lack of necessary mathematical concepts 14, Measurement error 12.
  따라서 "5×10" 배분 대신 8개 층에 7/7/6/6/6/6/6/6으로 뽑혔다.
- 학생 분포(표본 50개): student 1–6이 각각 7/7/10/9/10/7.

### Stepwise / MathClean / EIC

이전 보고와 동일하다. 요약하면,

- Stepwise: `None of the above` 87개 제외, 고유 문제 612개라 문제당 1건.
  `error_description` 이 비었다는 이유로는 제외하지 않았다(표본 50개 중 30개 보유).
- MathClean: 8개 파일 전부 확인. 오답+유형이 있는 파일은 `check_type_answer/*` 610개뿐이고,
  `check_correct_answer/*`의 오류 610개는 같은 사례의 중복(유형 명칭만 다름)이라 제외했다.
- EIC: GSM8K 9개 유형 900개를 풀로 사용. `wrong_step_calculation_error` 400개(단계 위치 변형)와
  비정규 라벨 2건 제외. 전부 `is_single_error=true`.
- 데이터셋 사이 중복: Stepwise∩EIC 문제 52개. 먼저 처리되는 Stepwise가 가져간다.

## 4. 고정된 표본 (200개)

| 데이터셋 | 선정 | dev | holdout | 층 배분 |
| --- | --- | --- | --- | --- |
| MathEDU | 50 | 10 | 40 | 8개 유형 7/7/6/6/6/6/6/6 |
| Stepwise | 50 | 10 | 40 | 6개 유형 9/9/8/8/8/8 |
| MathClean | 50 | 10 | 40 | 17/17/16 |
| EIC | 50 | 10 | 40 | 9개 유형 6/6/6/6/6/5/5/5/5 |
| 합계 | **200** | 40 | 160 | 문제 중복 0 |

시드 42. 표본은 `data/manifest/sample_manifest.jsonl`에 고정했고 프롬프트를 고쳐도 다시 뽑지 않는다.

## 5. dev 40건 실행 결과

- run id `v1__gpt-5.4-mini__dev`, 프롬프트 v1 sha256 `1b3c1823…`, 동시성 2.
- 요청 처리: 40/40 성공(`ok`). 실패·잘림·JSON 오류 0건. 평균 지연 약 1.3초.
- 토큰: 입력 25,028 / 출력 2,286 / 합계 27,314. reasoning 토큰 0. 단가는 확인하지 않았으므로
  비용은 적지 않는다.
- 모델 자체 status: ok 38, ambiguous 1(MathClean expression error), label_conflict 1(Stepwise
  "Calculation error easily solved by a calculator" 인데 모델은 비율을 잘못 적용한 오류로 봄).
- 길이: 중앙값 7–8단어. 5–15 단어 밖 2건(3단어 "Arithmetic addition error" 등).
- 중복 C 없음(40개 모두 서로 다름).
- 검토가 필요한 자동 플래그: 문제의 고유 단어를 그대로 쓴 경우 12건(예: "ladder-climbing",
  "tire count", "graves"), evidence_quote가 원문에서 그대로 확인되지 않은 경우 10건.
  이 플래그는 판정이 아니라 표시이며 응답 원문은 고치지 않았다.

산출물:

- `reports/review_v1__gpt-5.4-mini__dev.csv` (Excel용), `…dev.html` — Q/R/A/C/evidence/status/
  기존 annotation/자동 플래그 + 검토 의견 칸.
- `reports/summary_v1__gpt-5.4-mini__dev.md` — 상태 비율, 길이, 중복, 토큰 요약.
- `outputs/runs/v1__gpt-5.4-mini__dev/raw.jsonl` — 원문 응답, usage, 시도별 response/request id.

## 6. 프롬프트 v1 / v2 / v3 / v4 비교 (gpt-5.4-mini, 같은 dev 40건)

프롬프트 파일과 hash는 모두 보존한다. 표본은 재추출하지 않았다.

| | v1 | v2 | v3 | v4 |
| --- | --- | --- | --- | --- |
| 파일 크기 | 1,862 B | 8,134 B | 3,917 B | 3,161 B |
| sha256 | `1b3c182347176be6…` | `15f304a7be10cace…` | `86e57f4075105fa3…` | `28ef5467bbbac5ce…` |
| 요청 처리 성공 | 40/40 | 38/40 | 40/40 | 40/40 |
| 모델 status | ok 38 / amb 1 / conflict 1 | ok 37 / conflict 1 | ok 39 / conflict 1 | ok 38 / conflict 2 |
| 중앙값 길이 | 7단어 | 10단어 | 9단어 | 8단어 |
| 5–15단어 밖 | 2 | 3 | 1 | 2 |
| 문제 고유 단어 사용 | 12 | 16 | 12 | 16 |
| evidence 원문 일치 | 30 | 37 | 37 | 34 |
| 토큰(입력/출력) | 25,028 / 2,286 | 72,908 / 2,146 | 40,708 / 2,024 | 33,388 / 2,168 |

- v4는 v3보다 짧아졌지만(중앙값 9→8단어) **문제 고유 단어 사용이 12→16으로 다시 늘었고**
  evidence 원문 일치는 37→34로 줄었다. v4에서 "step numbers/final answer 생략", 전이 가능성
  점검(TRANSFERABILITY CHECK), 발췌 규칙 일부가 빠진 것과 방향이 일치한다.
- 자동 지표만 보면 gpt-5.4-mini에서는 **v3이 가장 균형이 좋다**(고유 단어 12, evidence 37,
  길이 이탈 1, 처리 실패 0).
- 버전별 status가 갈린 사례 8건은 `reports/compare_v1__vs__v2__vs__v3__vs__v4.md` 표에 있다.
  v4에서 새로 label_conflict가 된 2건(MathClean `4f4f06b721d19046`,
  Stepwise `231586f8d27166cb`)은 사람 확인이 필요하다.

## 7. 모델 비교 (프롬프트 v4 고정, 같은 dev 40건, 5개 모델)

### API 호출 지점 (공식 문서 확인)

- 다섯 모델 모두 **Responses API**(`POST /v1/responses`, SDK `client.responses.create`)로 호출한다.
  Chat Completions도 지원되지만 신규 구현은 Responses 기준이라 그대로 썼다.
- `gpt-5.6-*`, `gpt-6-*`는 reasoning 모델이며 `reasoning.effort`는 none / low / medium /
  high / xhigh / max를 지원하고 **기본값 medium**이다. 이번 실행은 기본값 그대로 두고
  effort를 보내지 않았다(비교 조건을 같게 두기 위해서).
- reasoning 토큰은 출력 토큰으로 과금되고 `max_output_tokens`(2000)에 포함된다.
  다섯 실행 모두 잘린 응답은 없었다.

| 모델 | 문서상 성격 | 단가(입력/출력, 1M) | knowledge cutoff |
| --- | --- | --- | --- |
| `gpt-5.4-mini` | mini 계열 | $0.75 / $4.5 | 2025-08-31 |
| `gpt-5.6-luna` | 저비용·고속 | $0.2 / $1.2 | - |
| `gpt-5.6-terra` | 범용 균형 | $2 / $12 | - |
| `gpt-6-sol` | 복잡한 코딩·에이전트용 | $2 / $10 | 2026-04-20 |
| `gpt-6-luna` | 고빈도 작업용 최경량 | $0.1 / $0.5 | 2026-05-18 |

### 결과 (40건, 프롬프트 v4 sha256 `28ef5467bbbac5ce…`)

| | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra | gpt-6-sol | gpt-6-luna |
| --- | --- | --- | --- | --- | --- |
| 요청 처리 성공 | 40/40 | 39/40 | 40/40 | **40/40** | 39/40 |
| 모델 status | ok 38 / conflict 2 | ok 36 / conflict 3 | ok 35 / conflict 5 | ok 37 / conflict 3 | ok 34 / conflict 5 |
| 중앙값 길이 | 8단어 | 9단어 | 9단어 | 9단어 | 8단어 |
| 5–15단어 밖 | 2 | **0** | **0** | 1 | 2 |
| 문제 고유 단어 사용 | 16 | 12 | 12 | 12 | **10** |
| evidence 원문 일치 | 34 | 35 | 36 | **40** | 36 |
| 출력 토큰(그중 reasoning) | 2,168 (0) | 8,536 (6,644) | 3,270 (1,459) | 7,148 (5,075) | 10,278 (8,399) |
| 중앙값 지연 | 1.2초 | 3.2초 | 2.1초 | 2.9초 | 3.5초 |
| 이번 실행 비용 | $0.035 | $0.017 | $0.106 | $0.138 | **$0.009** |

관찰:

1. **gpt-6-sol이 evidence 충실도에서 유일하게 40/40**이다. 처리 실패도 없다. 맥락 제거(고유 단어
   12)와 길이도 안정적이다.
2. **gpt-6-luna가 맥락 제거는 가장 좋고(10) 비용도 가장 싸다**($0.009 = mini의 1/4, terra의 1/12).
   다만 reasoning 토큰을 가장 많이 쓰고(8,399) 지연도 가장 길다(3.5초).
3. gpt-5.4-mini만 **문제 고유 단어 16**으로 뒤떨어진다. 같은 프롬프트에서 5.6/6 계열이 일관되게
   더 추상적인 묘사를 낸다.
4. **라벨 불일치(label_conflict) 판정은 신형 모델일수록 많다**(mini 2 → sol 3 → terra·gpt-6-luna 5).
   버전 간 status가 갈린 8건 중 MathClean 2건은 **mini만 ok**이고 나머지 네 모델이 모두
   label_conflict다.
   - `mathclean:8351714360a1cde0` — 사용자가 v2 프롬프트에서 "정답인데 오류를 지어내지 말 것"
     예시로 든 바로 그 사다리 문제다. 네 모델이 모두 label_conflict로 잡았고, mini만
     "Adds the repeated climbs instead of …"라는 오류를 만들어냈다.
   - `mathclean:6c8605b2eb64ed2b` — 파라미터화된 직선 문제. 마찬가지로 mini만 ok.
   MathClean 라벨 노이즈에 대한 지시문의 우려와 방향이 같다. 자동 판정으로 쓰지 않고 검토
   대상으로 남긴다.
5. 같은 사례에 대해 **모델이 서로 다른 오류를 지목**하기도 한다. 예: MathEDU "Comprehension error"
   한 건에서 mini는 단리 공식 적용 오류로, 5.6 계열은 대분수→가분수 변환 오류로 봤다.
6. `stepwise:aa3c4787242df63d`(라벨 "Unit conversion error", 실제로는 비율 오류)에서
   gpt-6-luna만 label_conflict로 표시하면서 설명도 함께 냈다. v4 프롬프트는 label_conflict일 때
   description을 null로 강제하지 않으므로 schema 위반은 아니다. v2처럼 강제하려면 프롬프트에
   다시 명시해야 한다.
7. JSON 파싱 실패 2건(gpt-5.6-luna 1, gpt-6-luna 1)은 **모두 같은 MathClean 사례**
   (`49d0c9b1827cc310`)이며, v2에서 깨진 것과 같은 원인이다. LaTeX `\(`가 JSON에서 허용되지 않는
   escape라 발췌를 그대로 복사하면 깨진다. 모델 문제가 아니라 데이터 + "원문 그대로 복사" 규칙의
   조합이다. 구조화 출력(`--json-mode`)으로 막을 수 있으나 적용하지 않았다.

### 실제 API 비용 누적

dev 40건 기준 8회 실행(320 요청) 합계 **약 $0.44**.
holdout 160건 1회 예상: mini $0.25, gpt-5.6-luna $0.07, gpt-5.6-terra $0.68,
gpt-6-sol $0.55, gpt-6-luna $0.04 (이번 dev 토큰 사용량 기준 추정).

산출물:

- `reports/compare_v4_models.{csv,md}` — **5개 모델 × 40건 한 표**, 버전별 길이·고유 단어·
  evidence·status 플래그 + `review_which_is_better` 칸.
- `reports/review_v4__<model>__dev.{csv,html}` — 각 모델 검수표. `description` 오른쪽에 나머지
  모델의 C가 열로 누적된다(mini 검수표에는 v1·v2·v3 프롬프트 열도 함께).
- `reports/compare_v1__vs__v2__vs__v3__vs__v4.{csv,md}` — 프롬프트 4버전 비교(mini 고정).
- `reports/summary_<run_id>.md`, `outputs/runs/<run_id>/raw.jsonl`(원문 응답·usage·시도 기록).

자동 지표는 표시일 뿐이며 어느 쪽이 나은지는 사람 판단이다.

## 8. 다음 단계

1. dev 40건 검수(오류 의미 보존 / 문제 맥락 제거 / 과도한 일반화 방지 3항목).
2. 프롬프트 버전과 모델을 각각 하나씩 고정한다. 자동 지표만 보면 프롬프트는 v3,
   모델은 evidence 충실도를 중시하면 `gpt-6-sol`, 맥락 제거와 비용을 중시하면 `gpt-6-luna`가
   후보다. 판단 근거는 6·7절 표와 비교 CSV에 있다.
3. 고정 후 holdout 160건 실행:
   `python scripts/run_generation.py --split holdout --model <MODEL> --prompt-file prompts/error_description_v<N>.txt`
   (버전·모델별로 별도 run 디렉터리에 저장된다.)
4. MathClean LaTeX 발췌의 JSON escape 문제를 어떻게 처리할지 결정한다(재요청 / 구조화 출력 /
   발췌 규칙 완화). 지금은 원문 그대로 보존만 하고 있다.

이번 파일럿의 자동 통계만으로 C의 전이 가능성이 입증되었다고 말하지 않는다.

## 9. 전체 라벨링 (2026-09-23)

200개 표본이 아니라 적격 레코드 전체에 C를 붙였다. 200개 표본(`data/manifest`)은 그대로다.

### 결정 사항 (사용자 확정)

| 항목 | 값 | 근거 |
| --- | --- | --- |
| 모델 | `gpt-5.6-luna` | 사용자 선택. 7절 표 기준 비용 $0.2/$1.2, 5–15단어 이탈 0 |
| 프롬프트 | v4 (`28ef5467…`) | 모델 5종 비교를 한 버전 |
| 출력 형식 | JSON 모드 (`text.format: json_object`) | 7절 관찰 7의 LaTeX `\(` JSON 깨짐 대응 |
| `max_output_tokens` | 4000 (파일럿 2000) | 사전 확인에서 MathClean 1건이 출력 1,091토큰(reasoning 1,034)을 사용. 상한만 올린 것이라 한도 안의 응답은 달라지지 않음 |
| 범위 | MathEDU·Stepwise·MathClean 적격 풀 + EIC GSM8K·MathQA 9개 유형 | 아래 EIC 구조 참고 |
| EIC 비정규 라벨 | 파일럿과 같이 제외 (9개 유형 밖 18건) | 폴더와 다르지만 9개 유형 안의 라벨(예: missing_step 폴더의 calculation_error)은 `wrong_type` 그대로 포함 |

설정은 `config/full.json`에 있다.

### EIC 저장소 구조 (고정 리비전 `be8132a8`에서 확인)

README 기준 8개 데이터셋 = 4종류 × {GSM8K, MathQA}. 이 프로젝트가 받은 것은 `generated_cases_*`뿐이다.

| 폴더 | 내용 | 판단 |
| --- | --- | --- |
| `generated_cases_*` | GPT-4가 정답 풀이의 한 단계에 오류 1개를 넣은 본 데이터. 9개 유형 × 약 100 + `wrong_step_calculation_error` 400 | 9개 유형만 사용 |
| └ `wrong_step_calculation_error` | 같은 문제(GSM8K 52개, 전부 8단계 풀이)에 계산 실수 위치만 1→8단계로 바꾼 실험. `calculation_error_100`과 문제가 겹치지 않음(GSM8K 0, MathQA 5) | 제외 |
| `incomplete_generated_cases_*` | generated_cases와 같은 문제·같은 오류, 오답 풀이를 첫 오류 단계에서 자른 것 | 받지 않음 |
| `step_number_cases_*` | calculation_error만, 원 풀이 단계 수(2–9)별 50개 | 받지 않음 |
| `EP_robustness_testing_cases_*` | 오류 유무 판별용, 유형별 정답 50 + 오답 50, 필드 3개(`label` yes/no). **GSM8K·MathQA 폴더가 바이트 동일하고 문제는 실제로 MathQA**. 오답 450건은 generated_cases_MathQA 오답 풀이와 동일 | 받지 않음 |

### 코드 변경

- `adapters.adapt_eic(benchmarks=...)`: 기본값 GSM8K(파일럿 정규화 결과 1,300건 동일 확인), `config.eic.benchmarks`로 MathQA 추가.
- `scripts/build_full_pool.py` + `errdesc/fullpool.py`: `data/full/pool.jsonl`(고유 요청), `record_index.jsonl`(모든 레코드 → sample_id/제외 사유).
- `run_generation.py --source full`, `--sample-ids`. run id `v4__gpt-5.6-luna__full`.
- `scripts/export_labels.py` + `errdesc/export.py`: raw 사본에 `generated_error_description` 추가.
  추가 키를 빼면 58개 파일 모두 원본과 바이트 동일함을 확인했다.
- `make_review.py`: split이 full이면 Q/R을 풀에서 읽는다.
- 테스트 44 → 53개.

### 실행 결과 (run `v4__gpt-5.6-luna__full`)

- 요청 3,986건 **전부 `ok`**. 1건(`mathedu:1dff56baaf3387b8`)이 처음에 4000토큰에서 잘렸다 — reasoning은
  516토큰뿐이고 evidence에 LaTeX `\rightarrow`를 옮기다 `\u0007\u0002…`를 반복하는 퇴화 출력이었다.
  같은 명령 재실행(재개)으로 1회 재시도해 성공했다. 최종 응답 중 1건은 출력이 2,068토큰으로 파일럿 한도
  2000이었다면 잘렸을 것이다.
- 비용: 과금 호출 4,000회(사전 확인 13 + 잘림 1 포함), 입력 3,209,514 / 출력 779,719(reasoning 569,850)
  토큰 → **약 $1.58** ($0.2 / $1.2 per 1M). 소요 약 30분(동시성 6, 초당 약 2.3건).

| 데이터셋 | 사례 | ok | ambiguous | label_conflict | 중앙 길이 | 5–15단어 밖 |
| --- | --- | --- | --- | --- | --- | --- |
| EIC (GSM8K 828 / MathQA 894) | 1,722 | 1,684 | 0 | 38 (2.2%) | 9 | 9 |
| MathClean | 610 | 473 | 5 | 132 (21.6%) | 9 | 3 |
| MathEDU | 888 | 866 | 1 | 21 (2.4%) | 10 | 14 |
| Stepwise | 766 | 689 | 0 | 77 (10.1%) | 10 | 5 |

label_conflict가 몰린 원래 라벨:

- MathClean `expression error` **39/64 (61%)**, `logic error` 56/314, `computing error` 37/232.
  `extent`가 "not obvious error"인 사례 117/428(27%) vs "obvious error" 15/182(8%).
- Stepwise `Unit conversion error` **20/45 (44%)**, `Calculation error easily solved by a calculator` 17/112.
- EIC는 `missing_step` 17/190 외에는 거의 없음(합성 단일 오류라 오류 위치가 분명).

자동 플래그(판정 아님): 문제 고유 단어 공유 1,230건(31%, dev에서도 luna 12/40), evidence 원문 불일치
346건(8.7%), 숫자 포함 44건. label_conflict 268건 중 49건은 description도 있다(v4는 null을 강제하지 않음).
같은 C가 2회 이상 나온 것은 119종 363건이며, "minutes/hours 변환 계수 오류"처럼 표현만 다른 거의
같은 설명이 여러 개 있다(정규화·군집은 하지 않았다).

산출물:

- `data/labeled/` — raw 사본 58개 파일(라벨 붙은 행 9,559개, leave_one_out 복사본 포함),
  `labels.jsonl`/`labels.csv`(고유 3,986건), `export_meta.json`. 추가 키를 빼면 58개 모두 원본과 바이트 동일.
- `reports/summary_v4__gpt-5.6-luna__full.md`, `reports/review_v4__gpt-5.6-luna__full.{csv,html}`.
- `outputs/runs/v4__gpt-5.6-luna__full/` — raw.jsonl(원문 응답·시도 기록), parsed.jsonl, run_meta.json.

### 다음에 할 일

1. MathClean `expression error`와 Stepwise `Unit conversion error`의 label_conflict를 사람이 확인한다
   (원래 라벨 노이즈인지, 모델이 오류를 못 찾은 것인지).
2. label_conflict/ambiguous 사례를 학습·평가 데이터에서 뺄지, description이 있는 49건을 어떻게 볼지 정한다.
3. 필요하면 거의 같은 C를 정규화·군집한다.

### 환경 주의

이 PC에서는 Windows "제어된 폴더 액세스"가 `OneDrive\문서` 아래 쓰기를 막아 python이
`FileNotFoundError [WinError 2]`로 실패했다(Defender 이벤트 1123). 사용자가 `python.exe`를
허용 앱에 추가해 해결했다. bash/PowerShell 쓰기는 여전히 막혀 있다.
