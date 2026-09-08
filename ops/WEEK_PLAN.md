# ARC Prize 2026 — план локального решения, revision 3

Версия: `arc2-week-2026-09-05-v3-sft-community`; актуализация 2026-09-08 по запросу пользователя.
Competition: `arc-prize-2026-arc-agi-2`.
История S1–S3 и факты M0 сохраняются.
Архив: `ops/archive/WEEK_PLAN_v1.md`, `ops/archive/WEEK_PLAN_v2.md`.
Исполнитель не переписывает историю попыток; статусы — в `STATE.json`, факты — append-only в `JOURNAL.md`.

## Критерий недели

Главный вопрос после каждого запуска: **что проверенное останется, даже если public score не вырастет?**

Не критерий: любые scored submits «в погоне за золотом». Не стратегия: клонировать чужие public notebooks и крутить их как основной цикл. Цель — локальное решение, полезное сообществу: воспроизводимый датасет, рецепт SFT уже скачанного Qwen, receipts/hashes и notebook, который документирует действия.

Gold/cutoff со снимка 2026-09-05 устарели и не являются целью этой ревизии. Champion 30.56 — исторический якорь, не обещание роста.

## Что уже осталось (не выбрасывать)

- Champion: Mikelou perfpatch, submission `56004028`, public **30.56**.
- S1 COMPLETE: `56034406`, **27.36** (отклонён).
- S2 COMPLETE: `56045262`, **30.28** (отклонён как champion).
- S3 `56068142` — last recorded PENDING; **не ретраить submit**. Read-only сверка допустима.
- Portable runner/scorer: `src/arc2/`, `scripts/cpu_contract_tests.py` PASS.
- Public eval challenges на NFS (solver-only): SHA `e7c62a4bd211867c6b538f66b8013b81f299663c82ca062f49a52bf439d6e4e8`.
- Eval solutions только у scorer: SHA `84be4f4f39b79e82c36d565fc878830988b094917f052ee7069aef30b33ca8f1`.
- Qwen `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1` на NFS: tar SHA `cee6e64f3b4f759813f378bdd644d5780a55b540339a7a4e2bfd17faa4fe71ee`, каталог `models/qwen3_4b_grids15_sft139-bf16-1/`.
- Env `envs/ngpu01/py3.11-cu124-unsloth-wip`: **torch 2.6.0+cu124**, **unsloth 2025.9.7**, CPU import `FastLanguageModel` OK. Stdlib venv не трогать.
- GPU lease ARC-2 на 2026-09-08: не открывался. Не стартовать S4+.

## Неподвижные правила

1. Competition submit только по отдельной явной команде на конкретную попытку. Kernel push ≠ submit. Эта ревизия **не** авторизует submit.
2. Hidden test считается только на Kaggle, Internet OFF. Public candidate cache нельзя запекать в scored notebook.
3. Solver не читает evaluation/hidden solutions. Training solutions — только в train-only пути SFT, не в inference solver.
4. GPU на NSU — только после `resource_queue.py` **RESERVED** через `nsu-quadro`, heartbeat ≤60 s, release после выхода process tree. Одна A100 на job ARC-2. Peak VRAM цель ≤22 GiB.
5. Не клонировать чужие notebooks как основной метод. Чужой код можно цитировать с license/hash, если он нужен как справка, но deliverable — свой датасет/рецепт/адаптер/writeup.
6. Каждый GPU/CPU запуск должен оставить проверяемый артефакт: manifest, hash, freeze, recipe, adapter, report или documented notebook. Запуск «просто посмотреть LB» запрещён.

## Путь M0 / M1 (локальный, без сабмита)

NFS root: `/home/scientists/gluz_d_s/kaggle/projects/arc-prize-2026-arc-agi-2/`

| Каталог | Назначение |
|---|---|
| `data/public-eval/` | evaluation challenges, solver input |
| `data/scorer-only/` | evaluation solutions, только scorer |
| `data/public-train/` | official training challenges **и** solutions (SFT only) |
| `data/sft/<dataset-id>/` | packed examples, split manifest, SHA-256 |
| `models/qwen3_4b_grids15_sft139-bf16-1/` | база, уже на месте |
| `models/sft/<run-id>/` | LoRA/adapters + adapter hash |
| `envs/ngpu01/py3.11-cu124-unsloth-wip/` | pinned ML env |
| `code/m0-portable-v1/` | runner/scorer |
| `runs/sft/<run-id>/` | logs, VRAM, recipe freeze, lease receipt |

### Разрешённые данные для SFT

- Official public **training** challenges + solutions (локальные SHA уже есть: challenges `779eaba8…`, solutions `9f07a38b…`).
- Документированные synthetic примеры, построенные **только** из training (рецепт + seed + hash). Без evaluation solutions и без hidden test.
- Не тащить Kaggle token/SSH keys на NSU.

### Стадии этой ревизии

**M0-ENV receipts (остаток):** pip-freeze, model file list, import receipt. Статус: import OK; freeze на NFS. Не считать COMPLETE без записанного freeze/hash в `ops/local_runs/`.

**M0-SMOKE (опционально, короткий):** одна A100 ≤30 min, load Qwen, один train step **на training example**, не full public-eval cache. Нужны: recipe, RESERVED lease, heartbeat wrapper. **В этом ходе не запускать**, пока нет wrapper + явного старта smoke.

**M1-DATA:** скопировать public-train на NFS с SHA; собрать versioned SFT dataset (task ids, pack format, train/held-in-train split, contamination check vs eval IDs). Артефакт остаётся даже при нулевом LB.

**M1-SFT:** дообучение уже скачанного Qwen (LoRA/Unsloth) на M1-DATA, chunks через очередь, receipts (loss, tokens, adapter hash, VRAM). Это **новый research stage**, не fork чужого notebook. Длинный unattended SFT не стартовать без готового recipe и lease.

**M1-WRITEUP:** notebook/markdown, который повторяет для других: какие файлы, какие hashes, как поднять env, как запустить короткий SFT, чего нельзя класть в scored kernel. Это community deliverable.

**Позже, только если адаптер проверен локально:** короткий Kaggle commit (Internet OFF) с pinned adapter как dataset; scored submit — отдельная команда пользователя. A100-секунды ≠ L4.

### Что сознательно отложено

S4 seed/view, S5 TRM-clone, S6 VARC-clone, S7 portfolio-from-clones — **не primary**. Они тратят submit/quota и не оставляют своего датасета/SFT. История V2 сохранена в архиве. Не начинать их, пока M1-DATA и хотя бы один SFT receipt не существуют.

## Validation (сохраняется как инструмент, не как повод слать LB)

Calibration-12 / Holdout-8 IDs и SHA `b798899dc1452d681b6849c3c1b93237ab5df6bd5193be53b90a14ef2f379155` без изменения выборки.
Primary: micro exact pass@2 по test outputs. Legacy task-macro отдельно.
Для SFT: сравнение adapter vs frozen base **на training-held split и/или Calibration без утечки eval solutions в train**. Full-120 — benchmark, не независимый holdout.

## Бюджет compute

Как в V2: одна A100, 8 CPU, 64 GiB RAM, peak ≤22 GiB, chunks ≤120 min, pilot ≤30 min. Диск 40–60 GiB план. Очередь: `nsu-quadro` + `resource_queue.py`. Kaggle GPU quota не жечь на clone-commits. Эта ревизия не выделяет 6 quota-h на S4–S7.

## Команды пользователю

- «Подготовь вычисления … без сабмита» / эта ревизия: M1-DATA, SFT recipe, receipts. Нет kernel push и нет submit.
- «Засабмить следующее решение»: только если есть frozen adapter + writeup + отдельная явная авторизация на **этот** submit. Иначе NO_NEW_CANDIDATE.

## Источники

- [Правила, evaluation, L4 multiplier](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/).
- Runbook: `ops/EXTERNAL_COMPUTE.md`.
- Executor: `ops/LIGHT_MODEL_PROMPT.md`.
