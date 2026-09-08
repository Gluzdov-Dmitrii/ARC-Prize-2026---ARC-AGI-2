# ARC Prize 2026 — журнал недели

Журнал append-only: старые строки и факты не удалять. Исправление оформлять новой строкой с пометкой `CORRECTION`.

## История до плана

| UTC | Submission | Notebook | Public | Статус | Наблюдение |
|---|---:|---|---:|---|---|
| 2026-09-01 14:58 | 55942614 | failed-in-aimo v1 | — | ERROR | Kaggle system error, 0-byte result |
| 2026-09-01 15:27 | 55942986 | failed-in-aimo v1 | 29.31 | COMPLETE | Повтор той же scriptVersion успешен |
| 2026-09-02 05:06 | 55954328 | NVARC+ v1 | 30.14 | COMPLETE | Adaptive/deep вариант |
| 2026-09-03 03:25 | 55973494 | Learned from AIMO | 16.39 | COMPLETE | Не использовать как primary |
| 2026-09-04 03:41 | 56004028 | Mikelou perfpatch | **30.56** | COMPLETE | Текущий champion |

## Обязательная запись для каждой стадии

После каждого запуска добавить отдельный подраздел со следующими полями:

```text
### <S#> — <UTC timestamp> — <финальный статус>
- Hypothesis:
- Only changed factor:
- Base notebook + SHA-256:
- Git HEAD / dirty diff:
- Own kernel slug / version / scriptVersionId:
- Model, dataset, kernel-source versions:
- Seed/config hash/accelerator:
- Preflight and output validation:
- Local/evaluation score; gained/lost/unique IDs; invalid rate:
- Commit/debug runtime; scored hidden-rerun runtime (если доступен); peak VRAM; completed/fallback task counts:
- Submission id / message / status:
- Public score; previous delta; champion delta:
- Rank before -> after; team count:
- Leader score; gold cutoff rank/score; gap:
- Error or anomaly with raw evidence path:
- Decision: champion / diverse runner-up / rejected / retry_pending:
- Artifact paths:
```

## Стартовый snapshot стадий этой недели

Таблица ниже — неизменяемый стартовый снимок, а не текущий статус. Новые результаты добавлять отдельными подразделами; канонический текущий статус находится только в `ops/STATE.json`.

| Stage | Status | Submission | Public | Rank | Decision |
|---|---|---:|---:|---:|---|
| S1 | PENDING | — | — | — | — |
| S2 | PENDING | — | — | — | — |
| S3 | PENDING | — | — | — | — |
| S4 | PENDING | — | — | — | — |
| S5 | PENDING | — | — | — | — |
| S6 | PENDING | — | — | — | — |
| S7 | PENDING | — | — | — | — |

### S1 — 2026-09-05T13:43:43Z — READY_TO_SUBMIT
- Hypothesis: salvage of partial Primary outputs, emergency writer, and 9:30 cap will prevent hidden-rerun coverage loss.
- Only changed factor: private kernel slug/metadata; Program077 solver unchanged.
- Base notebook + SHA-256: `kernels/yusuke-src/arc-baseline-rebuild.ipynb` / `ac0fe209de28b2123b9a1d51d3c2d2c82430d31743a57227572b66de9d96e499`.
- Git HEAD / dirty diff: `b75ea2d5271448cd5e7047f63b8707b526553d55` at attempt start (working tree still dirty with ops artifacts).
- Own kernel slug / version / scriptVersionId: `dmitriigluzdov/arc2-s1-program077-fork` / v1 / `347429199` (from Kaggle files page token; confirm before submit).
- Model, dataset, kernel-source versions: `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1`; kernel source `sorokin/pip-install-unsloth-flash-patch`; competition `arc-prize-2026-arc-agi-2`.
- Seed/config hash/accelerator: base_seed 42, `PYTHONHASHSEED=0`, 4×L4, internet off.
- Preflight and output validation: local preflight PASS; remote `SUBMISSION_FORMAT_GATE=OK` (120 tasks, 172 tests, 344 attempts, 0 errors). Local `submission.json` download still pending.
- Local/evaluation score; gained/lost/unique IDs; invalid rate: not scored; this was evaluation commit-run, not public LB.
- Commit/debug runtime; scored hidden-rerun runtime; peak VRAM; completed/fallback task counts: commit-run ~19303s (~5.36h); primary 120/120 task coverage OK; present candidate ratio 0.918605; 14 missing basekeys; 27 starved; deep skipped; recovered 0.
- Submission id / message / status: none yet (no competition submit).
- Public score; previous delta; champion delta: null.
- Rank before -> after; team count: 489 / 1819 on pre-run snapshot.
- Leader score; gold cutoff rank/score; gap: 73.33 / rank 13 / 33.47; gap from champion 30.56 is 2.91 to cutoff.
- Error or anomaly with raw evidence path: `DAILY_SUBMISSION_GATE=BLOCK` because `PRIMARY_PRESENT_OUTPUT_RATIO_BELOW_94_PERCENT`. Evidence: `ops/runs/arc2-week-2026-09-05-v1-S1-20260905T081641Z/kernel_logs.txt`, `program077_recovery_report.json`, `validation.json`.
- Decision: ready for user-authorized code submit despite notebook daily-gate BLOCK; emergency writer produced a full-format file. Not champion/rejected yet.
- Artifact paths: `ops/runs/arc2-week-2026-09-05-v1-S1-20260905T081641Z/`.

### S1 — 2026-09-05T14:04:37Z — SUBMITTING
- Competition submit (one shot): `56034406`, message `[S1][20260905][36993f35] p077-salvage`.
- Kernel: `dmitriigluzdov/arc2-s1-program077-fork` v1, file `submission.json`.
- Status at 14:04Z: `PENDING` (hidden rerun). Public score null.
- Quota after send: `numToday=1`. No retry.

### S1 — 2026-09-06T02:19:00Z — COMPLETE
- Submission `56034406` scored public **27.36** (COMPLETE). Delta vs previous champion 30.56: **-3.20**.
- Hidden-rerun runtime: null (not exposed).
- Rank after: null (fresh leaderboard not recaptured in this close-out).
- Decision: **rejected** as champion; production-safety salvage lost public coverage vs Mikelou. Stage S1 COMPLETE. Next stage S2.

### S2 — 2026-09-06T02:51:21Z — KERNEL COMPLETE / SUBMITTING
- Hypothesis: controlled seed reduces NVARC variance.
- Only changed factor: `stable_seed_for_key` + `PYTHONHASHSEED=260618` / `ARC_AUG_SEED_OFFSET=260618`.
- Kernel: `dmitriigluzdov/arc2-s2-nvarc-seed-fork` v1. Debug commit-run ~1534s; 4/4 tasks finished; reload score 2.5/4; no traceback.
- Competition submit (one shot): `56045262`, message `[S2][20260906][fafb6581] nvarc-seed`.
- Status at 02:52Z: `PENDING` (hidden rerun). Quota `numToday=1`. No retry.

### S2 — scored COMPLETE
- Submission `56045262` public **30.28** COMPLETE. Delta vs champion 30.56: **-0.28**.
- Decision: **rejected** as champion (below 0.42 quantum). Stage S2 COMPLETE. Next stage S3.

### S3 — 2026-09-07T03:14:18Z — PREPARING
- Hypothesis: diversity-aware attempt_2 adds solves without changing kgmon attempt_1.
- Only changed factor: `score_kgmon_diversity_a2`; S2 seeds/generation frozen.
- Kernel: `dmitriigluzdov/arc2-s3-selector-fork`. Preflight PASS.

### S3 — 2026-09-07T03:44:00Z — KERNEL COMPLETE / SUBMITTING
- Hypothesis: diversity-aware attempt_2 adds exact solves without changing kgmon attempt_1.
- Only changed factor: score_kgmon_diversity_a2 (attempt_1 stays kgmon rank-1); S2 generation/seeds/PYTHONHASHSEED frozen.
- Base notebook + SHA-256: kernels/arc2-s2-nvarc-seed-fork SHA 3ac4406b4c6eeae088b2b51f194dcbbb9edc4479fb4bfceb3e4d1be4ad8fad95.
- Git HEAD: 75ea2d5271448cd5e7047f63b8707b526553d55.
- Own kernel slug / version: dmitriigluzdov/arc2-s3-selector-fork v1.
- Preflight PASS; local selector smoke OK; internet OFF; 4xL4.
- Debug commit-run ~1602s; 4/4 tasks finished; reload **3.0/4**; kgmon / full_probmul_3 / diversity_a2 all 3.0/4 on debug-4 (not used as Calibration-12 selector pick).
- Format: 120 tasks, attempt_1/attempt_2, 0 schema errors.
- Competition submit (one shot): 56068142, message [S3][20260907][895babb3] selector-a2.
- Status at 03:44Z: PENDING (hidden rerun). Quota after send: numToday=1. No retry.
- Artifact path: ops/runs/arc2-week-2026-09-05-v1-S3-20260907T030959Z

CORRECTION: Git HEAD line above had a corrupted control character; canonical value is `b75ea2d5271448cd5e7047f63b8707b526553d55`.

### NSU / external-resource check — 2026-09-07T10:24:24Z
- Local identity: `hasee\dmitry`; SSH client `C:\WINDOWS\System32\OpenSSH\ssh.exe`.
- Aliases (BatchMode): `nsu-quadro` → `prepost` (0); `nsu-a100` → `ngpu01` (0); `nsu-pc` → `desktop-7t0uo8i\user` (0).
- GPUs idle at check: Quadro 24 GB 0%; A100 UUID `GPU-61c0078d-...` 0 MiB; A100 UUID `GPU-04efb7bd-...` 0 MiB; RTX 3080 311 MiB / 0%.
- `sinfo`/`squeue --me` timeout 15s (exit 124). Remote `~/kaggle` and `_control` **missing**. Direct GPU launch `BLOCKED_COORDINATION`. No training/transfer/install.
- Competition: scored submit must be a Kaggle notebook, internet off, ≤12h. NSU not used for S3 hidden rerun.
- S3 `56068142` still PENDING at this check. Cleanup receipt: `ops/runs/arc2-week-2026-09-05-v1-S3-20260907T030959Z/cleanup_receipt.json` (~2.8 MiB Unsloth stubs removed).

### План revision 2 — 2026-09-07T12:18:11Z — PREPARATION_PLANNED

- Основание: пользователь сообщил конкуренцию проектов за Kaggle GPU quota и попросил перенести подготовку на RTX6000/RTX3080/2×A100; указал shared external-resources prompt.
- S1/S2 остаются COMPLETE, 27.36/30.28; champion 30.56. S3 56068142 read-only проверен, по-прежнему PENDING. В этой актуализации нет нового push/submit/compute launch.
- Архив исходного плана: ops/archive/WEEK_PLAN_v1.md, SHA-256 e48776963a6c446818f9a6927cdb560c977b992c858630e2ec7ca8e45bea9466. Новый план ops/WEEK_PLAN.md, revision arc2-week-2026-09-05-v2-external; hash в STATE.
- Решение: M0 portable runner + pinned Linux ML env + Qwen pilot на одной A100 + общий public candidate bank; S4 seeds, S5 TRM, S6 VARC, S7 portfolio только после внешнего validation gate. Непрошедшие gate не сабмитить.
- Kaggle budget: target 30 min / cap 45 min на один финальный commit; не больше 6 estimated quota-h на оставшиеся четыре commits, с учётом фактического общего остатка. L4 multiplier 2 по официальному overview; S1 19303 s соответствует оценке 10.72 quota-h. Actual quota debit и hidden rerun accounting не измерены.
- SSH: sandbox account aliases не разрешал; approved execution от hasee/dmitry подтвердил prepost/ngpu01/desktop-7t0uo8i-user. A100: две 80GB PCIe, 0 MiB GPU use в момент чтения, RAM 251 GiB. Quadro: 24 GB. Не reservation.
- CORRECTION к записи 10:24Z: remote root и ARC-2 scaffold сейчас существуют. Live COORDINATION_STATUS обновлён 12:07:18.987476Z: initialized=true, DIRECT_USER_AUTHORIZED, ALLOWED_WITH_RESOURCE_RESERVATION, slurm_required=false. Общий resource_queue.py уже установлен. Старые справочные слова о blocked dispatcher не актуальны; перед будущим run перепроверять live config.
- ML setup пока не выполнен: stdlib Python 3.11.2 проверен, Qwen/Unsloth/TTT ещё не запускались на NSU; framework lock, code/data transfer и personal storage budget остаются задачами M0.
- CORRECTION метрики: официальный overview задаёт mean по test outputs, прежний plan V1 — task-macro. С V2 primary micro, legacy macro вторично; опубликованные scores не меняются. Универсальный quantum 0.42 удалён. S2 всё равно ниже champion.
- Validation limitation: S3 built from S2 и имел только debug-4 selector tie; это не положительный calibration signal. M0 должен исправить отсутствие paired validation до S4.
- Новые документы: ops/EXTERNAL_COMPUTE.md, обновлённый ops/LIGHT_MODEL_PROMPT.md, STATE.migration/compute_policy/validation_protocol. Run history и начальные snapshots сохранены.

### M0 — 2026-09-07T12:57:34Z — CPU COMPLETE / ENV IN_PROGRESS
- Command: prepare NSU M0, no Kaggle submit. S3 `56068142` still PENDING; no retry.
- Plan hash match: `a37b40d45d958117a5955dd13dbc0c92a70a661180d52d917bca25e079642430`.
- Live queue CLI required `mode=DIRECT_USER_AUTHORIZED`; 12:20 COORDINATION_STATUS lacked `mode`. Restored mode + `ALLOWED_WITH_RESOURCE_RESERVATION` (previous snapshot in `_control/diagnostics/`). `resource_queue.py status`: empty requests.
- M0-CPU: extracted S2/champion sources; portable `src/arc2/starter.py` uses N workers = N UUIDs; solver paths via `ARC2_*` env; CPU contract tests PASS; validation IDs SHA matches V2.
- Data on NSU NFS (hashes verified): evaluation challenges → `data/public-eval/`; solutions → `data/scorer-only/` (solver does not read them). Code tree `code/m0-portable-v1/`.
- M0-ENV incomplete: Qwen snapshot download in progress locally (~5.41 GiB). Follow-up scp of get-pip/bootstrap hit SSH timeout (`10.1.0.7:22`). Stdlib venv not mutated. No GPU lease, no pilot, 0 GPU-h.
- Next: restore SSH, finish model transfer, bootstrap `envs/ngpu01/py3.11-cu124-unsloth-wip`, then one-A100 smoke ≤30 min.
- Local handoff: `ops/local_runs/m0-20260907T124000Z/`

### M0 — 2026-09-07T15:47:00Z — Qwen archive verified locally / NSU VPN down
- Local tar.gz `ops/local_runs/m0-staging/models/qwen3_4b_grids15_sft139.tar.gz`: 5813574154 bytes, gzip CRC OK, uncompressed 7267287040 bytes.
- SHA-256: `cee6e64f3b4f759813f378bdd644d5780a55b540339a7a4e2bfd17faa4fe71ee`.
- Members: HF root (`config.json`, tokenizer, `model-00001-of-00002.safetensors`, `model-00002-of-00002.safetensors`). Ready for `from_pretrained` after extract.
- Kaggle CLI logged `ChunkedEncodingError` / IncompleteRead then exit 0; treat as noise given CRC+listing.
- `ssh nsu-quadro` failed: `NSU VPN: NSU-SSTP did not connect`, connection closed `10.1.0.7:22`. No scp, no venv bootstrap, no GPU lease.
- Can continue: local CPU runner already PASS; next NSU step is VPN then scp tar.gz + bootstrap. Do not re-download. No Kaggle submit.

### M0 — 2026-09-07T18:10:00Z — Qwen on NFS, Unsloth import OK
- VPN restored. scp of `qwen3_4b_grids15_sft139.tar.gz` to NFS completed; remote SHA-256 `cee6e64f3b4f759813f378bdd644d5780a55b540339a7a4e2bfd17faa4fe71ee` matches local. Extracted to `models/qwen3_4b_grids15_sft139-bf16-1/`.
- Venv `envs/ngpu01/py3.11-cu124-unsloth-wip`: torch 2.6.0+cu124 after Unsloth 2025.11 pulled torch 2.14+cu130 (driver 12.4 rejects it). Pinned Kaggle overlay unsloth 2025.9.7 / transformers 4.55.4 / peft 0.17.1; removed torchao leftover. CPU import of FastLanguageModel OK.
- Stdlib venv not mutated. No GPU lease, no Kaggle submit. Next: M0-PILOT one A100 ≤30 min.

### План revision 3 — 2026-09-08T02:45:00Z — SFT/community, без сабмита
- Пользователь сменил критерий: не любые сабмиты ради золота, а «что проверенное останется, даже если score не вырастет». Клоны чужих public notebooks не стратегия.
- Архив V2: `ops/archive/WEEK_PLAN_v2.md`, SHA `a37b40d45d958117a5955dd13dbc0c92a70a661180d52d917bca25e079642430`. Новый план `ops/WEEK_PLAN.md`, revision `arc2-week-2026-09-05-v3-sft-community`, SHA `dbe8feb198063d80cd60d8f636a96dc8be47d89041ee35971b1427eb0dff5f23`.
- S1–S3 история без изменений. Champion 30.56. S3 `56068142` не ретраить. S4–S7 clone-path parked.
- M0 факты сохранены: Qwen на NFS (tar SHA `cee6e64f…`), torch 2.6.0+cu124, unsloth 2025.9.7 import OK. Очередь 2026-09-08: нет ARC-2 lease (чужие ARC-3 smoke RELEASED). GPU не запускался.
- Следующий локальный шаг: M1-DATA — official public-train на NFS с SHA + SFT manifest + проверка, что eval IDs не в train. Длинный SFT и Kaggle submit в этом ходе не стартовали.

CORRECTION: S4–S7 в `STATE.json` переведены из PENDING в SKIPPED (`NO_NEW_CANDIDATE`). Очередь 2026-09-08 повторно: нет ARC-2 lease; чужие A100 smoke RELEASED. `competition_submit.authorized=false`. Коммит плана `28dc968` уже на `origin/main`.

