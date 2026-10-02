# 에이전트 인수인계 — Newman 실험 (`newman_experiment/`)

다른 서버에서 `git clone` 후 이 실험을 이어받는 에이전트(Claude Code 등)를 위한 문서다. 사용자와의 대화는 한국어로 한다.

## 0. 먼저 읽을 것 (순서대로)

1. 이 문서
2. [`docs/decisions.md`](docs/decisions.md): 사용자 결정 기록. **계획서보다 우선한다**
3. [`docs/experiment_plan.md`](docs/experiment_plan.md): 계획서 원문(작업 규칙 포함)
4. [`README.md`](README.md): 실행 명령, 파일 구조
5. [`../rl/EXPERIMENTS.md`](../rl/EXPERIMENTS.md)의 "Newman" 절: 계획 값과 실행 확인 값

## 1. 작업 규칙 (사용자 확정, 반드시 지킨다)

1. **연구 설계는 사용자와 먼저 확정한다.** 대상은 프롬프트(Student / 답 채점 / 학생다움 judge / verifier), RM 목표와 출력 계약, reward·loss 식, 열린 sampling·batch 값, API 답 추출 방식이다. 이미 확정된 결정(`docs/decisions.md`)은 다시 묻지 않고 변경안만 논의한다. 환경 설정, 실행 스크립트, mock/smoke 테스트, 결과 의미를 바꾸지 않는 속도 개선은 묻지 않고 해도 된다. sampling 분포나 effective batch를 바꾸는 속도 개선은 설계 변경이다.
   - 코드 장치: 결정이 없는 값은 config에 `REQUIRED`로 둔다. 사용자가 확인한 초안 텍스트·값은 `python scripts/approve.py <item> --note "..."`로 파일 해시를 기록한다. 실제 run은 `REQUIRED`가 남아 있거나, 승인이 없거나, 승인 뒤 내용이 바뀌었으면 시작하지 않는다. **사용자 확인 없이 approve 하지 않는다.**
2. **기록은 `rl/EXPERIMENTS.md`에.** 값은 run이 남긴 `run_meta.json`, `generation_meta.json`, `metrics.json`, `summary.json`에서 읽는다(`python scripts/record_experiment.py outputs/<run>`). 실행 전은 **계획**, 실행 후는 **실행 확인**으로 구분하고, 결정 이력과 중단 run 및 그 이유도 남긴다.
3. **run 이름 = 출력 폴더 = W&B run 이름** = `<experiment>_seed42_<YYYYmmdd_HHMMSS>`, Asia/Seoul 기준(스크립트가 자동으로 만든다). 재개는 같은 이름을 쓰고, 설정이 다른 새 실험은 새 시각을 쓴다.
4. **Git은 사용자가 실행한다.** commit/push를 대신 하지 말고 전체 명령 블록을 준다(8절). 브랜치는 `rl-grpo` 하나이며, 바꾸거나 지우지 않는다.
5. **분할과 checkpoint.** SFT는 train:test 8:2이고 validation이 없으며 SFT test에서 best를 고른다(낙관적이라고 명시). RL은 사용자 결정(2026-09-30)으로 train을 train/validation 90:10으로 나누고 validation에서 best를 고르며, test는 보고용이다. 모델 snapshot과 재개 checkpoint는 **모두 보관**하고 자동 삭제하지 않는다.

그 밖에 지킬 것:
- `../rl/`, `../verifier_sft/` 코드는 수정하지 않는다. 이전 Eedi 실험 결과를 재현하는 코드이고 import해서 재사용하는 모듈이다.
- **`.env` 값을 출력하지 않는다**(cat/sed 금지). 키가 있는지는 `source env.sh` 뒤 `[ -n "${OPENAI_API_KEY:-}" ]`로만 확인한다. 저장소는 **public**이니 비밀정보를 커밋하지 않는다.
- smoke 실행은 run 이름을 `smoke_`로 시작한다. 이 경우에만 mock 보상, 미승인 초안, 미검증 데이터가 허용된다.
- 계획서의 원래 문구와 사용자 결정이 다르면 `docs/decisions.md`를 따르고, 새 결정은 그 표에 추가한다.

## 2. 현재 상태 (2026-10-02)

| 항목 | 상태 |
|---|---|
| 코드 | 완료. 단위 테스트 53개(네트워크·GPU 없음) |
| 데이터 | 검증된 워크북(sha256 `9324bac2…`)으로 준비 완료, 커밋 대상: `data/prepared/sft`(half A 1,081 / half B 1,063 / test 528 앵커, 쌍 행 2,162 / 2,126 / 1,056), `data/prepared/rl`(train 6,336 / validation 704 / test 1,752 조건), `manifests/`, `reports/data_audit.md`, `reports/format_check_*.md`(실패 0) |
| smoke (이전 서버, A100 × 2) | verifier SFT → 평가, GRPO(mock) 3 step + 재개, Student 평가까지 통과 |
| verifier SFT (2026-10-01, A100 80GB × 2) | 1차(16개 유형 전체 negative)는 데이터셋 지름길로 폐기. **2차**(`data/prepared/sft`, 같은 데이터셋 negative)와 **3차**(`data/prepared_v3/sft`, + 다른 데이터셋·다른 단계 negative, `configs/*_v3.yaml`) A/B 학습·평가. best는 HF private `WooYoungSeok/newman-<run>-<checkpoint>`(3차 A는 epoch-4도 업로드). API verifier(gpt-5.6-sol, gpt-5.1) 비교와 test 간 교차 평가 결과는 `../rl/EXPERIMENTS.md` N8–N11, `reports/verifier_comparison_*.md`. 2026-10-02 결정: 8 epoch 재학습 없이 v3 A/B epoch-5를 RL에 사용 |
| 승인 | 6개 모두 완료(2026-10-02에 `answer_judge_prompt`, `student_likeness_prompt` 추가) |
| `REQUIRED` | 없음. A = v3 A epoch-5, B = v3 B epoch-5 (HF private, 사용자 결정 2026-10-02) |
| RL (2026-10-02, A100 80GB × 4) | 1 epoch(1,056 step), 0.25 epoch마다 snapshot·재개 저장. tmux `newman`에서 `run_rl_pipeline.sh student_likeness diversity` 실행 중(첫 run `newman_student_likeness_seed42_20261002_121157`). API baseline gpt-5.6-sol 조건당 1회 생성 완료(`outputs/api_baselines/gpt-5.6-sol`, B 채점은 평가 단계). 기록 `rl/EXPERIMENTS.md` N12 |
| 열린 결정 | `docs/decisions.md`의 "열린 결정" 표 |
| 디스크 | 새 서버 2 TiB. RL은 0.25 epoch마다 snapshot 15 GB + 재개 checkpoint 실측 122 GB를 run당 4개씩 보관(run당 약 0.55 TB) |

## 3. 새 서버 준비

```bash
git clone https://github.com/WooYoungSeok/tutee_error.git && cd tutee_error
git checkout rl-grpo && git pull
(cd rl && bash setup_server.sh)             # ~/venv/rl    (driver 535 기준 cu129 스택)
(cd verifier_sft && bash setup_server.sh)   # ~/venv/tutee
# tutee_error/.env (사용자가 올림): OPENAI_API_KEY, HF_TOKEN, WANDB_API_KEY, WANDB_PROJECT
#   반드시 KEY=value 형식(= 양옆 공백 없이). rl/verifier_sft의 setup/env.sh는 .env를 셸로 실행한다
cd newman_experiment && bash setup_server.sh   # openpyxl, 테스트, GSM8K 다운로드(고정 리비전·해시 확인)
source env.sh        # RL venv (verifier SFT는 source env.sh sft)
```

- 워크북은 git에 없다(`data/raw/` 제외). 준비된 데이터와 `manifests/taxonomy_mapping.json`(26행의 이름·정의·D열 원문)이 커밋되어 있으므로 **데이터를 다시 만들 때만** `data/raw/`에 올리면 된다. macOS에서 올린 한글 파일 이름(NFD)도 인식한다.
- GPU: verifier SFT는 GPU 1장으로 A 다음 B 순서로 돌린다(한 run이 host RAM 약 229 GiB를 쓰므로 동시 실행 금지). RL 기본 배치는 GPU 4장(0–2 학습, 3 rollout+verifier)이다. 장수가 다르면 effective batch 48을 유지할 조합을 사용자와 정하고 config를 바꾼다(`train_student.py`가 불일치를 거부한다).
- 디스크: `train_student.py`와 `train_verifier.py`가 예상 저장량(모든 checkpoint 보관)을 여유 공간과 비교해 모자라면 시작하지 않는다.

## 4. 다음 단계 (순서대로)

1. **남은 승인(RL 전까지)**: `../rl/prompts/answer_judge_*.txt` + `prompts/gsm8k_answer_contract.txt`, `../rl/prompts/student_likeness_*.txt` + MathEDU 예시를 사용자에게 보여 주고 확인을 받은 뒤 `approve.py`를 실행한다. verifier SFT는 승인 없이 바로 진행 가능.
2. **verifier SFT**: 먼저 smoke(`README.md`)를 돌린 뒤 `tmux new -s newman_sft 'bash scripts/run_sft_pipeline.sh'`
   (A 학습 → B 학습과 A 평가 동시 → B 평가, 로그 `logs/sft_pipeline.log`). 따로 돌릴 때는
   `GPU=0 bash scripts/run_train_verifier.sh configs/verifier_half_a.yaml` → `configs/verifier_half_b.yaml`
   - 2026-10-01: 사용자 지시로 A100 80GB × 2 서버(이전 서버)에서 SFT만 먼저 시작했다. 진행 상황은 `rl/EXPERIMENTS.md` Newman 절.
3. **verifier 평가·선택**: `source env.sh sft; python scripts/eval_verifier.py --config configs/verifier_half_a.yaml --run_dir outputs/<run> --include_base`(B도 같게). best는 `test_eval/summary.json`의 `best_checkpoint_path`에 남는다. 이를 `configs/rl_common.yaml`의 `verifier.checkpoint`(A), `evaluation.verifier.checkpoint`(B)에 적는다(필요하면 HF private 업로드 후 hub id). 결과는 `rl/EXPERIMENTS.md`에 기록한다.
4. **서빙 확인**: `bash scripts/launch_eval_servers.sh configs/diversity.yaml`, `python scripts/check_verifier_server.py --config configs/diversity.yaml --role a` / `--role b`
6. **RL**: `python scripts/make_smoke_data.py` + `configs/smoke/rl_mock.yaml`(GPU 번호를 서버에 맞게)로 smoke → `tmux new -s newman 'bash scripts/run_rl_pipeline.sh student_likeness diversity'`. 파이프라인은 학습 → validation으로 snapshot 선택 → test(base + 모든 snapshot) 보고 순서다.
7. **API baseline·비교**: `generate_api_baseline.py --model gpt-5.6-sol` → `evaluate_student.py --api_dirs ...` → `compare_student_likeness.py`
8. 매 단계 뒤 `rl/EXPERIMENTS.md` 기록과 git 명령 블록 전달.

## 5. 이 실험의 설계 방식 (비슷한 실험을 설계할 때 재사용)

- **결정과 초안을 코드에서 분리한다.** 사용자가 정할 값은 `REQUIRED`, 초안 텍스트는 해시 기반 승인(`src/newman/approvals.py`, `preflight.py`)으로 막는다. smoke는 예외로 두어 인프라를 먼저 검증한다.
- **원자료가 진실의 원천이다.** 매핑표(워크북)를 매 준비 때 다시 읽어 config와 한 글자라도 다르면 멈춘다(`taxonomy.verify_workbook`). 외부 목록(단위 허용 목록)은 출처 커밋·파일 해시와 함께 원문을 그대로 들여오고, 원본 데이터 내용과 대조한다(`unit_eligibility.content_audit`).
- **누출은 구조로 막는다.** 모든 데이터원을 한 문제 키로 묶은 전역 그룹에서 split을 한 번만 정한다. 층별로 독립된 난수를 써서, 나중의 결정(RL 범위 등)이 이미 정한 분할을 흔들지 않게 한다. 준비 스크립트가 불변식(그룹 하나당 split 하나, N = mapping(E), 단위 제한, 1:1 쌍, validation/test와 verifier 학습 데이터의 분리)을 점검하고, 하나라도 실패하면 쓰지 않는다.
- **run은 스스로를 기록한다.** 설정 체인과 해시, 데이터·프롬프트·taxonomy 해시, 승인 상태, git 커밋, 패키지 버전, 실제 optimizer, 실제 API 요청 필드, 저장 크기 실측값을 남긴다. EXPERIMENTS.md는 이 기록에서만 옮긴다.
- **기존 검증 코드를 재사용하고 수정하지 않는다.** 보상 클라이언트와 산술(`tutee_rl`), 토큰화·판정·품질 필터(`verifier_common`, `prepare_descriptive_pairs`)를 import한다. 새 실험에 고유한 부분만 새로 쓴다.
- **테스트로 확정 사항을 고정한다.** 계획서 표(16/10, 단계 분포), 확정 하이퍼파라미터, reasoning low의 실제 전송, 보상 분기를 단위 테스트로 고정한다(`tests/`).

## 6. 주의 사항

- 기존 `rl/env.sh`는 `.env`를 `source`하므로 `KEY = value` 줄이 있으면 멈춘다. 이 디렉터리의 `env.sh`는 파싱만 한다.
- 인자를 받는 셸 스크립트 안에서 `source env.sh`를 인자 없이 부르면 호출자 인자가 넘어간다. 스크립트에서는 `source env.sh rl|sft`로 쓴다.
- `gh`가 없는 서버가 있다. PR 전에 `gh` 설치와 `gh auth login`, `git config user.name/user.email`이 필요할 수 있다.
- vLLM 0.30에서 top_k 0과 -1은 모두 "끔"이다. 학습(TRL)과 평가는 0으로 같게 보낸다.
- 첫 step은 warmup 때문에 학습률이 0이다. 그래서 `epoch-0.5` snapshot은 step 수가 적으면 base와 같을 수 있다(smoke에서 확인됨).

## 7. 파일 지도

`configs/`(taxonomy·data·verifier·rl·approvals·smoke), `prompts/`, `src/newman/`(common, taxonomy, sources, unit_eligibility, splits, negatives, rl_conditions, verifier_format, clients, orchestrator, metrics, approvals, preflight), `scripts/`(fetch_sources, prepare_data, check_formatting, approve, train/eval verifier, check_verifier_server, train/evaluate student, generate_api_baseline, compare_student_likeness, record_experiment, make_smoke_data, launch/stop servers, run_rl_pipeline), `data/`, `manifests/`, `reports/`, `docs/`, `tests/`. 자세한 설명은 `README.md`.

## 8. Git 명령 블록 형식 (사용자가 실행)

```bash
cd tutee_error
git branch --show-current            # rl-grpo 이어야 함. 아니면 멈추고 확인
git add <이번 변경 경로들>
git status --short
git diff --cached --stat
git diff --cached
git commit -m "<요약>" -m "Co-Authored-By: <에이전트 표기>"
git push origin rl-grpo
gh pr create --base main --head rl-grpo --title "<제목>" --body-file /tmp/<이름>_pr_body.md
gh pr view --json number,url
gh pr merge --merge
git fetch origin && git merge origin/main
git status --short
```

PR 본문 파일은 실제 변경 목적과 수행한 검증 결과로 미리 작성한다. 매번 새 PR을 만든다.
