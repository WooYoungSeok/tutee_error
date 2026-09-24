# Descriptive error verifier SFT (v1 · v2)

입력 `(question, incorrect solution, error description)` → `aligned` / `not_aligned`.
계획서: `verifier_sft_experiment_plan.md` (2026-09-23). 기존 `llm_tutee_tutor/finetuning/reward_model`
(commit `972f0c38`, `train_0431.py` / `eval_0431.py`)의 학습 흐름을 따르되 데이터는 미리 고정한다.

## 현재 상태

| 단계 | 상태 |
| --- | --- |
| 데이터 준비 (`prepare_descriptive_pairs.py`) | 완료 — 점검 11개 통과, `reports/data_audit.md` |
| 입력 형식·loss mask 점검 (`check_formatting.py`) | 완료 — 7,404개 예시 실패 0, `reports/format_check.md` |
| 단위 테스트 (`tests/`) | 19개 통과 (네트워크·GPU 없음) |
| 스모크 학습 (4 step) | 완료 (2026-09-24, 엘리스 A100 80GB) — `deepspeed_enabled: true`, 약 5분 |
| v1 학습 | 2026-09-24 서버에서 시작, 214/1488 step에서 중단(v2로 전환). `checkpoint-186`(1 epoch)만 서버에 있음 |
| v1 평가 (test 744행) | gpt-5.6-sol 0.9718 · SFT checkpoint-186 0.9543 · Qwen 학습 전 0(invalid 100%), gpt-4o-mini 추출 시 0.7849 — `reports/eval_*.md` |
| v2 데이터 | 완료 — 라벨이 여러 개인 풀이 제외, 점검 11개 통과, 형식 점검 6,818개 실패 0, `reports/descriptive_v2/` |
| v2 학습 / 평가 | 예정 (`--config config/descriptive_verifier_v2.json`, 5 epoch = 855 step, wandb 기록) |

## v2 데이터 (현재 기준, `config/descriptive_verifier_v2.json`)

v1에서 **같은 풀이에 정규화한 원본 라벨이 2종류 이상 달린 풀이의 사례를 모두 분할 전에 제외**했다
(`filters.exclude_multi_label_solutions`). 같은 풀이는 중복 레코드 키(dataset, 문제, 풀이; NFKC·소문자·공백 제거)에서
라벨만 뺀 기준이고, 라벨은 다른 이유로 이미 빠진 레코드까지 포함한 원본 풀 전체에서 모은다. MathEdu처럼 풀이 하나에
라벨 하나가 되도록 하기 위한 것이다. 해당 풀이: Stepwise 145개(레코드 328, 새로 제외 289), EIC 2개(레코드 4).
그 외 규칙(분할·negative·길이)은 v1과 같고, 분할과 negative는 줄어든 범위에서 다시 계산된다.
학습은 v1의 8 epoch 대신 5 epoch(`training.num_train_epochs`)이다.

| split | 원본 사례(anchor) | 학습 입력 | stepwise anchor |
| --- | --- | --- | --- |
| train | 2,724 | 5,448 | 321 |
| validation | 341 | 682 | 38 |
| test | 344 | 688 | 41 |

v1 test와 같은 anchor는 344개 중 282개이고 negative는 대부분 새로 뽑혔으므로 v1 평가 결과와 직접 비교하지 않는다.
v2의 데이터·manifest·보고서·평가 결과는 모두 `descriptive_v2/` 하위(`data/`, `manifests/`, `reports/`, `outputs/`)에 있다.

## v1 데이터 (고정)

| split | 원본 사례(anchor) | 학습 입력 (positive + negative) |
| --- | --- | --- |
| train | 2,969 | 5,938 |
| validation | 361 | 722 |
| test | 372 | 744 |

- 출처: `../data/full/pool.jsonl` + 설명 생성 run `v4__gpt-5.6-luna__full` (gpt-5.6-luna, 프롬프트 v4).
- 설명 생성 `status == "ok"`만 사용(ambiguous 6, label_conflict 268 제외). 문제 그림·그래프가 없어 풀 수 없는
  MathClean 3건 보류(config에 사유), 동일 중복 레코드 7건 제거 → 3,702건.
- 문제 그룹: NFKC·소문자·공백·구두점을 무시한 문제 텍스트 기준(3,114그룹). 중복 레코드 판정은 공백만 무시
  (연산자 유지). 같은 풀이에 여러 원본 라벨이 달린 사례(Stepwise 교사별 주석 등)는 각각 positive로 두고,
  같은 그룹이라 서로의 negative가 되지 않는다.
- 분할: 문제 그룹 단위 80/10/10, dataset·benchmark·원본 라벨로 층화, seed 42. 설명 프롬프트 개발에 쓴
  dev 40건의 문제 그룹(37개)은 train으로 고정해 test에서 뺐다.
- Negative: 같은 split·같은 dataset·다른 원본 라벨·다른 문제 그룹의 사례 중 균등 추출,
  split마다 `numpy.random.RandomState(42)`. 의미 검수 없음 → 지표는 자동 타깃과의 일치도다.
- 길이: Qwen2.5-Math-7B-Instruct 토크나이저로 최대 2,665토큰(한도 4096 = 모델 max_position_embeddings).

## 파일

```
config/descriptive_verifier_v1.json   입력 경로, 필터, 분할, negative 규칙, 학습·평가 설정
config/descriptive_verifier_v2.json   v1 + 라벨이 여러 개인 풀이 제외, 출력 경로는 descriptive_v2/
prompts/system.txt, user.txt          학습·추론 공통 지시문 (계획서 7절 원문)
prompts/user_ablation_*.txt           보조 진단용 (풀이 제거 / 설명만)
verifier_common.py                    설정, 프롬프트, 토큰화·loss mask, 응답 판정, 지표
prepare_descriptive_pairs.py          데이터 준비 (로컬에서 실행 완료)
check_formatting.py                   실제 토크나이저로 형식·mask 점검
train_descriptive_verifier.py         full-parameter SFT (assistant 토큰에만 loss)
eval_descriptive_verifier.py          고정 split 평가(메인: 정확 일치), 예측 저장, 지표·bootstrap
eval_api_verifier.py                  OpenAI API 모델을 같은 프롬프트·같은 정확 일치로 평가 (참고용)
eval_gpt_parsing.py                   긴 생성 + gpt-4o-mini 판정 추출 (보조 지표; llm_tutee_tutor의
                                      eval_reward_model_gpt_parsing.py 방식)
summarize_results.py                  baseline/SFT 비교표 → <report_dir>/verifier_results.md
data/descriptive_v1/, data/descriptive_v2/        {train,validation,test}.jsonl, meta.json
manifests/, manifests/descriptive_v2/             split_manifest.jsonl(모든 사례의 split 또는 제외 사유),
                                                  pair_manifest.jsonl(anchor별 donor, 후보 수, 토큰 수)
outputs/<name>/, outputs/descriptive_v2/<name>/   평가 예측·지표 (API 응답 원문은 git 제외)
env.sh, setup_server.sh, requirements-lock.txt    서버 환경 (아래)
accelerate_config_ds_single.yaml, ds_config.json   reward_model과 같은 DeepSpeed ZeRO-2 설정
```

## 서버 환경 (엘리스 GPU 서버)

검증한 환경: Ubuntu 22.04, Python 3.10.14, CUDA toolkit `/usr/local/cuda-12.8`, A100 80GB.
정확한 패키지 버전은 `requirements-lock.txt`에 고정했다(torch 2.11.0+cu128, transformers 5.17.0,
deepspeed 0.19.7, accelerate 1.15.0). `requirements.txt`는 하한만 적은 참고용이다.

```bash
git clone https://github.com/WooYoungSeok/tutee_error.git && cd tutee_error/verifier_sft
bash setup_server.sh      # 최초 1회: ~/venv/tutee 생성, lock 설치, 단위 테스트
source env.sh             # 새 셸마다: venv 활성화 + CUDA_HOME (DeepSpeed cpu_adam 컴파일에 필요)
```

venv 위치나 CUDA 경로가 다르면 `TUTEE_VENV`, `CUDA_HOME` 환경변수로 바꾼다.

## 서버 실행 순서 (`verifier_sft/`에서, `source env.sh` 후)

아래 명령은 v1 설정(기본값) 기준이다. v2는 모든 스크립트에 `--config config/descriptive_verifier_v2.json`을 붙인다.
보고서는 설정의 `output.report_dir`(v1 `reports/`, v2 `reports/descriptive_v2/`)에, 평가 결과는
`evaluation.output_dir`에 쓰이므로 두 버전이 서로 덮어쓰지 않는다. `--limit` 실행은 `<name>_limit<N>`에 따로 쓰고 git에서 제외한다.

```bash
python -m pytest tests -q                       # 19 passed
python check_formatting.py --limit 50           # 서버 토크나이저로 형식 재확인 → reports/format_check_limit50.md (git 제외)

# 1) 스모크: 64쌍, 4 step. run_info.json의 deepspeed_enabled가 true인지 확인
CUDA_VISIBLE_DEVICES=0 accelerate launch --config_file accelerate_config_ds_single.yaml \
    train_descriptive_verifier.py --limit 64 --max_steps 4 --report_to none --output_dir checkpoints/smoke

# 2) 학습: 8 epoch, 매 epoch validation loss로 best checkpoint 선택 → checkpoints/<run>/final
CUDA_VISIBLE_DEVICES=0 accelerate launch --config_file accelerate_config_ds_single.yaml \
    train_descriptive_verifier.py

# 3) 평가: SFT 전 backbone과 SFT 모델, 같은 test·같은 decoding
CUDA_VISIBLE_DEVICES=0 python eval_descriptive_verifier.py --model_path Qwen/Qwen2.5-Math-7B-Instruct --name baseline
CUDA_VISIBLE_DEVICES=0 python eval_descriptive_verifier.py --model_path checkpoints/<run>/final --name sft
python summarize_results.py baseline sft

# (보조) 지름길 진단
CUDA_VISIBLE_DEVICES=0 python eval_descriptive_verifier.py --model_path checkpoints/<run>/final --name sft_no_solution --ablation no_solution
CUDA_VISIBLE_DEVICES=0 python eval_descriptive_verifier.py --model_path checkpoints/<run>/final --name sft_description_only --ablation description_only

# (참고) API 모델: 같은 프롬프트·정확 일치. OPENAI_API_KEY는 ../.env. 응답은 캐시되어 재실행 시 남은 행만 호출
python eval_api_verifier.py --api_model gpt-5.6-sol --name gpt-5.6-sol
# (보조) 긴 생성 + gpt-4o-mini 판정 추출. 메인 지표(정확 일치)와 섞지 않는다
CUDA_VISIBLE_DEVICES=1 python eval_gpt_parsing.py --model_path Qwen/Qwen2.5-Math-7B-Instruct --name baseline_gptparse --batch_size 32
```

긴 작업은 tmux에서 실행하고 로그를 남긴다(예: 학습은 `checkpoints/<run>/train.log`, 평가는 `logs/`).

## 확인할 점

- 체크포인트: 중간 체크포인트 하나가 약 114GB(가중치 15GB + DeepSpeed optimizer 상태 `global_step*/` 100GB),
  `final/`은 가중치만 15GB. `save_total_limit` 2(best + 최신)라 학습 중 최대 약 245GB가 필요하다.
  `checkpoints/`는 git에서 제외한다.
- transformers 5는 `warmup_ratio`를 없앴다. 학습 스크립트는 5.x에서 config의 `warmup_ratio` 값을
  `warmup_steps`에 넘기며, 1 미만 float는 비율로 해석되어 4.x와 같은 `ceil(전체 step × 0.1)`이 된다.
  체크포인트의 `training_args.bin`에는 `warmup_steps=0.1`로 기록된다.
- `report_to`는 기존과 같이 `wandb`. 학습 스크립트는 시작할 때 `../.env`를 읽으므로 `.env`에 `WANDB_API_KEY`,
  `WANDB_PROJECT`(선택: `WANDB_ENTITY`)를 적는다. run 이름은 체크포인트 폴더 이름이다. 키가 없으면 `--report_to none`.
- 기존 코드와의 차이: 평가 샘플을 실행 때마다 새로 뽑지 않고 파일로 고정, 학습 중 평가는 validation만,
  4096 초과 입력을 자르지 않고 중단, 응답 판정은 정규식이 아니라 정확 일치(나머지는 invalid).
- 데이터를 다시 만들 때는 `prepare_descriptive_pairs.py`(`../data/full/pool.jsonl`,
  `../outputs/runs/v4__gpt-5.6-luna__full/parsed.jsonl` 등 필요, 저장소에 포함)를 실행하고 결과를 커밋한다.
  v2는 서버에서 만들었고, 같은 코드로 v1 설정을 다시 돌리면 v1의 split·pair 파일과 manifest가 바이트 단위로 같게 나온다.
- 입력 해시: v1 `meta.json`의 입력 sha256 4개는 Windows에서 CRLF로 체크아웃된 파일 기준이고, v2는 `.gitattributes`로
  LF인 파일 기준이라 값이 다르다. 파일 내용은 같다(LF 파일을 CRLF로 바꿔 계산하면 v1 값과 일치).
- Qwen2.5-Math-7B-Instruct(학습 전)는 "라벨만 출력" 지시를 따르지 않고 풀이부터 쓰므로 정확 일치(`max_new_tokens` 10)에서
  모두 invalid다. 판별력은 `eval_gpt_parsing.py`로 보조 확인한다. 이 방식은 판정 없이 끝난 응답에도 gpt-4o-mini가
  판정을 추정할 수 있다(v1 test에서 6건).
