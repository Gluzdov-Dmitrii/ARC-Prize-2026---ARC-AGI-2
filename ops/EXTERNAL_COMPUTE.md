# ARC-2 — перенос подготовки на NSU

Дата: 2026-09-07, дополнение 2026-09-08 (revision 3). Checklist путей, очереди и env. **Не** отчёт об успешном Qwen GPU-run: CPU import OK, GPU smoke/SFT ещё не выполнялись.

Revision 3 (2026-09-08): критерий — leftover verified artifacts (датасет, SFT recipe/adapter hashes, writeup), не clone-notebook submits. SFT уже скачанного Qwen — основной research path. Evaluation solutions не входят в train. Hidden test только на Kaggle Internet OFF. ARC-2 GPU lease на момент ревизии не открывался.

## Подтверждённое состояние

Прочитаны AGENT_PROMPT, README, SETUP_STATUS, ACCESS, WORKFLOW, RESOURCE_POLICY из
`C:/Users/Dmitry/Desktop/Kaggle/Kaggle Agents/external-resources/`.

При текущей проверке SSH через пользовательский Windows OpenSSH:
- `nsu-quadro hostname` -> `prepost`;
- `nsu-a100 hostname` -> `ngpu01`;
- `nsu-pc whoami` -> `desktop-7t0uo8i\\user`.
Из sandbox-аккаунта aliases не разрешались; штатное approved execution от `hasee\\dmitry` успешно. Ошибка alias в sandbox не означает отсутствие доступа.

Live `ngpu01`: две A100 80GB PCIe, по 81920 MiB, обе показывали 0 MiB compute memory; RAM 251 GiB. Live `prepost`: Quadro RTX 6000, 24576 MiB, 5 MiB used. Это снимки, не выделение ресурсов. RTX 3080 10 GB/Windows и RAM ~32 GB — данные справочника, свежий memory snapshot на PC не снимался.

Важное уточнение: SETUP_STATUS/RESOURCE_POLICY ещё описывали неактивный диспетчер. Фактический
`/home/scientists/gluz_d_s/kaggle/_control/COORDINATION_STATUS.json` обновлён 2026-09-07T12:07:18.987476+00:00 и содержит:
`initialized=true, mode=DIRECT_USER_AUTHORIZED, gpu_launches=ALLOWED_WITH_RESOURCE_RESERVATION, slurm_required=false`.
Основание в записи: пользователь временно предоставил все три машины для своей работы; режим действует до изменения/отзыва. Не блокировать запуск только из-за Slurm. Перед будущим run перечитать запись: состояние может измениться.

Project manifest ARC-2: empty workspace scaffold, no inputs transferred. Stdlib Python 3.11.2 на A100 запускается; PyTorch/Unsloth/Qwen ещё не проверены.

## Пути

Linux общий NFS project root (одна копия для обоих Linux hosts):
`/home/scientists/gluz_d_s/kaggle/projects/arc-prize-2026-arc-agi-2`

Windows project root:
`C:/Users/User/kaggle/projects/arc-prize-2026-arc-agi-2`

Существующие baseline interpreters, которые не изменять:
- A100: `<Linux project>/envs/ngpu01/py3.11-stdlib-v1/bin/python`;
- Quadro: `<Linux project>/envs/prepost/py3.11-stdlib-v1/bin/python`;
- PC: `<Windows project>/envs/desktop-7t0uo8i/py3.12-stdlib-v1/Scripts/python.exe`.

Новые versioned code/env/data/models/runs создавать внутри этого проекта. Shared /home free 7 TiB не является персональным лимитом; перед bulk staging подтвердить разрешённый бюджет и проверить ROOT/PROJECT manifests. Начальная оценка 40–60 GiB.

Факт 2026-09-07/08 на Linux NFS (не дублировать на Quadro отдельно от этой копии):
- `code/m0-portable-v1/` — portable runner;
- `data/public-eval/` — evaluation challenges;
- `data/scorer-only/` — evaluation solutions (не в solver, не в SFT);
- `data/public-train/` — создать: official training challenges+solutions;
- `data/sft/<dataset-id>/` — packed SFT split + SHA;
- `models/qwen3_4b_grids15_sft139-bf16-1/` — база, tar SHA `cee6e64f3b4f759813f378bdd644d5780a55b540339a7a4e2bfd17faa4fe71ee`;
- `models/sft/<run-id>/` — будущие адаптеры;
- `envs/ngpu01/py3.11-cu124-unsloth-wip` — torch 2.6.0+cu124, unsloth 2025.9.7.

## Использование действующей общей очереди

Production queue calls выполняются только через `nsu-quadro`; скрипт проверяет hostname:
`/home/scientists/gluz_d_s/kaggle/_control/resource_queue.py`.
Очередь уже есть; второй dispatcher/приватную очередь не создавать.

Read-only status:
```powershell
ssh -o BatchMode=yes nsu-quadro /usr/bin/python3 /home/scientists/gluz_d_s/kaggle/_control/resource_queue.py status
```

CLI локальной копии скрипта прочитан. Перед использованием сверить remote help/version. Запрос готового run через тот же Python/скрипт:
```text
request --id <unique-run-id> --owner <agent-id> --token <owner-token>
        --project arc-prize-2026-arc-agi-2 --run-path <absolute-run-path>
        --pool a100 --count 1 --cpu 8 --ram-gib 64
        --disk-gib <planned-growth> --minutes 120
```

Это шаблон аргументов, не запущенный request. Все значения заполнить фактическими данными; READY означает, что code, env и inputs уже подготовлены. State RESERVED с полученными UUID обязателен до запуска; exit 3 / WAITING_RESOURCE — ждать тем же ID. Вызовы started, heartbeat, release требуют того же id/token. При started передать PID и точное process-start identity; heartbeat <=60 s через supervisor, release только после проверки окончания всего process tree. При отмене ещё ожидающего request использовать cancel. Потеря SSH не освобождает lease.

Очередь сама процессы не запускает, лимиты memory/disk не обеспечивает и не обнаруживает все посторонние GPU-процессы. Wrapper должен сверять actual UUID/process state, применять CPU/RAM/VRAM/time caps, вести heartbeat и обеспечивать cleanup. Разработать/проверить wrapper до GPU-run, не ограничиваться ручной записью reservation.
При конкуренции один GPU job ARC-2, chunks <=2 h. Второй A100 — только если разрешён второй слот, нет ожидающих проектов и runner поддерживает task shards. Не запускать четыре Qwen-копии на одной A100 ради имитации L4×4.

## Portable runner: что именно изменить

Исходники для reference:
- champion: `kernels/arc2-mikelou-perfpatch-fork/arc-agi2-lb33-89-minimal-perfpatch.ipynb`;
- deterministic reference: `kernels/arc2-s2-nvarc-seed-fork/arc-agi2-lb33-89-minimal-perfpatch.ipynb`;
- S3: `kernels/arc2-s3-selector-fork/arc-agi2-lb33-89-minimal-perfpatch.ipynb`.

Новый исходник держать в `src/arc2/`, CLI/сборщик в `scripts/`, конфиги в `configs/`. Эти каталоги/CLI будут созданы исполнителем M0; сейчас это спецификация, не готовые команды.

1. Извлечь arc_loader.py, arc_decoder.py, arc_solver.py и starter.py из notebook. Импорты/установка окружения отделены от запуска; изменённые источники имеют diff к baseline.
2. Runner принимает `--input --model --output-dir --task-manifest --devices --seed --max-seconds --mode smoke|eval|full`. Решение не принимает solutions path; scorer — отдельная CPU-команда. Paths обязательны, скрытых Kaggle-путей вне packaging нет.
3. Заменить `range(4)`, `mp.spawn(...nprocs=4)` и назначение `CUDA_VISIBLE_DEVICES=str(rank)`: использовать список выделенных UUID, process-local ordinal и число разрешённых workers. Queue sentinels соответствуют workers. Под Slurm сохранять назначенную visibility.
4. Убрать зависимость полного прохода от одного Kaggle env-флага: внешний `--mode full` должен исполнять production algorithm на открытых задачах. Kaggle wrapper использует подтверждённый platform rerun signal только для выбора smoke/full, никакого поиска hidden cohort по IDs/размеру.
5. Вынести budgets/seeds в конфиг. A100 исполняет те же train/augment/token/search caps, BF16 и attention backend, что target L4; не увеличивать их автоматически по VRAM. Runtime equivalence проверяется отдельно.
6. Deadline/watchdog распространяется на model loading, TTT, DFS/rescore, дочерние процессы и finalization. Сохранять результаты атомарно по каждой задаче. Resume только по полному совпадению lineage/config/input hash; partial write не считается завершённой задачей.
7. Candidate bank хранит task/test key, grid, источник/seed, decoder scores, validity, counters и timings. Если feature отсутствует, selector не подставляет выдуманный score. Solutions не входят в solver cache.
8. Формат JSON: динамическое множество IDs и длина test lists, две attempts, целые цвета 0..9, допустимые прямоугольные grids, никаких hard-coded 120 задач. Проверки на synthetic 1/3/multiple-test задачи, timeout, OOM/worker failure, повторный resume.
9. Notebook собирается из тех же источников и frozen config; перенос не создаёт расходящиеся local/Kaggle реализации.

## ML environment и данные

Начать с одного Linux/A100-окружения. Зафиксировать фактические версии successful Kaggle S2 image и dependency wheels, затем создать отдельный `envs/ngpu01/<python>-<lock-hash>/`. Не копировать Windows venv и не запускать pip unpinned latest.
Совместимость включает driver, torch CUDA build, Triton/PTX, Unsloth patch и Python ABI. Python 3.11 stdlib scaffolding не гарантирует wheel compatibility с Kaggle image; при иной Python ABI подготовить совместимый user-level interpreter либо отдельный документированный lock. Драйверы и system Python не менять.

Веса Qwen:
`sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1`.
Kaggle kernel dependency:
`sorokin/pip-install-unsloth-flash-patch`.
Точные file hashes/version receipts сохранить до запуска. Kaggle image metadata содержит private-byod URI: не считать его доступным Docker image для NSU; если pull недоступен, воспроизвести совместимый user environment по receipts.

Competition downloads/auth остаются на локальном Windows-клиенте; на NSU переносить разрешённые открытые данные, код и веса через scp/SFTP с hashes. Не переносить Kaggle token/SSH keys. Для train-only будущего обучения использовать public training и разрешённые synthetic данные; evaluation ответы не должны попадать в training.
Кеши PIP/HF/TORCH/TRITON и TMPDIR привязать к проекту/run. Не загружать public candidate bank в scoring notebook. Новые общие веса/адаптеры при необходимости публикуются как versioned Kaggle input в рамках отдельной разрешённой подготовки; сам код не должен их скачивать из Internet при scored run.

Revision 3 делает SFT уже скачанного Qwen основным research stage, а не «после четырёх clone-стадий». Train-only: official public training и documented synthetic из training. Evaluation/hidden answers в train не входят. Полный public-eval candidate cache больше не обязательный leftover недели; короткий reserved smoke (load + один train step) — опциональный receipt перед длинным SFT. Длинный unattended SFT не стартовать без versioned dataset, recipe и lease.

## Проверка и готовность

M0 CPU contract: scorer micro-accuracy, legacy macro отдельно; shape/remount/resume/failure tests; проверка отсутствия solutions в solver.
M0 A100 smoke (optional, ≤30 min): load Qwen, один train step на **training** example, env/VRAM receipt, lease cleanup. Не полный eval cache.
M1-DATA: NFS `data/public-train/` + `data/sft/<id>/` manifest, SHA, contamination check vs eval IDs.
M1-SFT: LoRA/Unsloth на базе `qwen3_4b_grids15_sft139-bf16-1`, adapter hash, recipe freeze. Kaggle scored kernel — отдельная поздняя опция; Internet OFF, без public prediction cache.
Ни одного competition submit в этой ревизии без новой явной команды. LIGHT_MODEL_PROMPT revision 3.

## Что сохранять и чистить

Сохранять code/config/env/input hashes, команды, host/GPU UUID/lease, timings, peak VRAM/RAM/disk, paired scores, gained/lost/unique matrix, fallback coverage, cleanup receipt. Local handoff: `ops/local_runs/<run-id>/`.
Retention pin: Qwen base, SFT datasets, adapter receipts и writeup. Clone-stage candidate banks не обязательны. Архивы загрузки удалять только после hash verification в своей project subtree. Weights/caches не в git. Общий NFS не дублировать между A100 и Quadro.

## Первичные источники

- [Правила исполнения, external data и метрика](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/).
- [NVIDIA: совместимость CUDA kernels между архитектурами](https://docs.nvidia.com/cuda/archive/12.4.1/ampere-compatibility-guide/index.html).
- [FlashAttention: поддерживаемые GPU/backends](https://github.com/Dao-AILab/flash-attention).
