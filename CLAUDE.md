# tutee_error — 에이전트 공통 규칙

현재 진행 중인 실험은 `newman_experiment/`다. 그 안의 [`AGENTS.md`](newman_experiment/AGENTS.md)를 먼저 읽는다.
사용자와의 대화는 한국어로 한다.

- 연구 설계(프롬프트, 보상·loss, RM 출력 계약, 열린 sampling·batch 값)는 사용자와 먼저 확정한다. 확정된 결정은 다시 묻지 않는다.
- 설정·결과는 run이 남긴 메타데이터에서 읽어 `rl/EXPERIMENTS.md`에 기록한다(계획 / 실행 확인 구분).
- run 이름 = 출력 폴더 = W&B 이름 = `<experiment>_seed42_<YYYYmmdd_HHMMSS>` (Asia/Seoul).
- git commit·push는 하지 않고 전체 명령 블록(add → status → commit → push → 새 PR → merge → `git fetch origin && git merge origin/main`)을 사용자에게 준다. 브랜치는 `rl-grpo`.
- checkpoint는 모두 보관하고 자동 삭제하지 않는다.
- `.env` 값은 절대 출력하지 않는다. 저장소는 public이다.
- `rl/`, `verifier_sft/`는 완료된 Eedi 실험 코드다. 수정하지 않고 import해서 재사용한다.
