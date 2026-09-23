# Descriptive error verifier SFT (v1)

입력 `(question, incorrect solution, error description)` → `aligned` / `not_aligned`.
계획서: `verifier_sft_experiment_plan.md` (2026-09-23). 기존 `llm_tutee_tutor/finetuning/reward_model`
(commit `972f0c38`, `train_0431.py` / `eval_0431.py`)의 학습 흐름을 따르되 데이터는 미리 고정한다.

## 현재 상태

| 단계 | 상태 |
| --- | --- |
| 데이터 준비 (`prepare_descriptive_pairs.py`) | 완료 — 점검 11개 통과, `reports/data_audit.md` |
| 입력 형식·loss mask 점검 (`check_formatting.py`) | 완료 — 7,404개 예시 실패 0, `reports/format_check.md` |
| 단위 테스트 (`tests/`) | 19개 통과 (네트워크·GPU 없음) |
| 학습 / 평가 | 서버에서 실행 예정 (로컬 GPU 8GB로는 7B full SFT 불가) |

## 데이터 (고정)

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
prompts/system.txt, user.txt          학습·추론 공통 지시문 (계획서 7절 원문)
prompts/user_ablation_*.txt           보조 진단용 (풀이 제거 / 설명만)
verifier_common.py                    설정, 프롬프트, 토큰화·loss mask, 응답 판정, 지표
prepare_descriptive_pairs.py          데이터 준비 (로컬에서 실행 완료)
check_formatting.py                   실제 토크나이저로 형식·mask 점검
train_descriptive_verifier.py         full-parameter SFT (assistant 토큰에만 loss)
eval_descriptive_verifier.py          고정 split 평가, 예측 저장, 지표·bootstrap
summarize_results.py                  baseline/SFT 비교표 → reports/verifier_results.md
data/descriptive_v1/                  {train,validation,test}.jsonl, meta.json
manifests/split_manifest.jsonl        모든 사례의 split 또는 제외 사유
manifests/pair_manifest.jsonl         anchor별 donor, 후보 수, 토큰 수
accelerate_config_ds_single.yaml, ds_config.json   reward_model과 같은 DeepSpeed ZeRO-2 설정
```

## 서버 실행 순서 (`verifier_sft/`에서)

```bash
pip install -r requirements.txt                 # 기존 reward_model 환경이면 대부분 설치되어 있음
python -m pytest tests -q                       # 19 passed
python check_formatting.py --limit 50           # 서버 토크나이저로 형식 재확인

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
```

## 확인할 점

- 체크포인트: 7B full SFT라 체크포인트 하나가 가중치 약 15GB + optimizer 상태. `save_total_limit` 2
  (best + 최신). `checkpoints/`는 git에서 제외한다.
- `report_to`는 기존과 같이 `wandb`. 로그인이 없으면 `--report_to none`.
- 기존 코드와의 차이: 평가 샘플을 실행 때마다 새로 뽑지 않고 파일로 고정, 학습 중 평가는 validation만,
  4096 초과 입력을 자르지 않고 중단, 응답 판정은 정규식이 아니라 정확 일치(나머지는 invalid).
- 데이터를 다시 만들 때는 `prepare_descriptive_pairs.py`(로컬, `../data`와 `../outputs` 필요)를 실행하고
  결과를 커밋한다. 서버에서는 다시 만들지 않는다.
