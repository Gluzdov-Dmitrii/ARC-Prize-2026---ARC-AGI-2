# ARC Prize 2026 — план на 7 сабмитов

Версия плана: `arc2-week-2026-09-05-v1`  
Competition: `arc-prize-2026-arc-agi-2`  
Цель недели: выйти из зоны `30.56` к устойчивым `35–37+` public и собрать два разных финальных кандидата: сильный champion и устойчивый/diverse runner-up.

Этот файл во время недели не редактируется. Исполнитель меняет статусы только в `ops/STATE.json` и дописывает факты в `ops/JOURNAL.md`.

## Исходная точка

- Текущий champion: submission `56004028`, Mikelou perfpatch, public `30.56`, rank `489` на снимке 2026-09-05.
- Другие валидные результаты: baseline `29.31`, NVARC+ `30.14`, Learned from AIMO `16.39`.
- Текущая ориентировочная gold-зона: rank `1–13`; cutoff `33.47`. Это только public-снимок, медаль определяется final private leaderboard.
- Не считать локальные `kernels/*-out/submission.json` полноценной CV: commit-run обрабатывал только четыре debug-задачи.

## Неподвижные правила недели

1. Одна стадия проверяет один главный фактор. Не смешивать дополнительные идеи.
2. Один scored competition submit на одну команду пользователя. После `COMPLETE` остановиться.
3. До submit обязательны: успешный Kaggle commit-run, валидный `submission.json`, Internet OFF, все inputs закреплены, прогноз runtime не более 10.5 часа и fail-safe до 11:50.
4. `attempt_1` после S2 сохраняет текущий лучший neural primary, если стадия явно не говорит иначе. Новизна в основном идёт в `attempt_2`.
5. Для открытой evaluation-выборки фиксировать exact-match, gained/lost IDs, unique solves, invalid/shape rate, runtime и peak VRAM. Public LB не является единственным критерием.
6. Никаких автоматических повторных submit после неопределённого ответа API. Сначала искать submission по уникальному message.
7. Исходники `kernels/*-src` не перезаписывать: делать собственный приватный fork/копию стадии.
8. Champion обновляется при улучшении public минимум на один наблюдаемый квант (`0.42` п.п.) либо при равном score и заметно лучшей надёжности/runtime. Diverse runner-up хранится отдельно.

## Зафиксированный validation protocol V1

- Никакого ручного отбора задач. Набор из 20 public-evaluation task IDs получен сортировкой по `SHA256("arc2-week-2026-09-05-v1:" + task_id)` и зафиксирован ниже.
- Calibration-12: `a32d8b75, 9aaea919, 3a25b0d8, a47bf94d, cb2d8a2c, 1ae2feb7, 8e5c0c38, cbebaa4b, 2c181942, 5dbc8537, 4a21e3da, 271d71e2`.
- Holdout-8: `13e47133, 31f7f899, b9e38dc0, 3e6067c3, 4e34c42c, b5ca7ac4, 67e490f4, 2d0172a1`.
- SHA-256 файла из этих 20 IDs по одному на строку с финальным newline: `b798899dc1452d681b6849c3c1b93237ab5df6bd5193be53b90a14ef2f379155`.
- Параметр выбирается только по Calibration-12; после выбора Holdout-8 оценивается один раз и не используется для дополнительной подгонки в той же стадии.
- Метрика повторяет competition: для test output успех, если truth в `attempt_1` или `attempt_2`; task credit — среднее по его test outputs; итог — среднее task credit. Gained/lost/unique считаются по ключу `<task_id>_<test_index>` относительно замороженного base.
- Public solutions загружаются только scorer после генерации кандидатов. Solver не получает ответы. Debug-4 допустим только как smoke, не как основание для выбора selector/gate.
- Один validation commit-run: не более 2.5 часа. Все S3–S7 используют один и тот же manifest и budgets; любое отклонение записывается как protocol violation.

## S1 — production-safety anchor

- База: `kernels/yusuke-src/arc-baseline-rebuild.ipynb` (Program077).
- Гипотеза: salvage частичных результатов, emergency writer и cap 9:30 устранят потерю coverage при hidden rerun.
- Единственное изменение: заменить upstream metadata на собственный приватный kernel slug; solver Program077 не менять.
- Preflight: проверить runtime fingerprints, четыре L4, прикреплённую Qwen-модель, schema, создание fallback submission и успешный debug commit-run.
- Сигнал: valid COMPLETE без unhandled quality-gate; public не хуже `30.56`. Даже при равном score ценна подтверждённая надёжность.

## S2 — deterministic NVARC reproduction

- База: собственный текущий champion `kernels/arc2-mikelou-perfpatch-fork/arc-agi2-lb33-89-minimal-perfpatch.ipynb`.
- Гипотеза: контролируемый seed уменьшит разброс NVARC и приблизит воспроизводимость публичного `33.89` baseline.
- Единственное алгоритмическое изменение: заменить process-randomized `hash(task_id)` на стабильный per-task seed и задать `PYTHONHASHSEED`; реализацию взять из `kernels/original-kg-src/arc-agi2-original-kg.ipynb`. Perfpatch и остальные параметры не менять.
- Preflight: одинаковые outputs двух повторных дешёвых smoke-проходов там, где CUDA это допускает; логировать все остаточные различия.
- Сигнал: `>=33.47` — вход в текущую public gold-зону; `>=30.56` при меньшем разбросе — кандидат на robust runner-up.

## S3 — selector для второго attempt

- База: лучший из S1/S2 по правилу champion; candidate generation, seeds, task order и budgets заморожены.
- Гипотеза: второй selector даст дополнительные exact solves без ухудшения primary.
- Единственное изменение: выбор `attempt_2`. Сравнить на фиксированном evaluation-slice `score_kgmon`, `score_full_probmul_3` и diversity-aware вариант; `attempt_1` оставить прежним.
- Выбор до submit: selector с лучшим pass@2; tie-break — больше unique solves, затем меньше invalid outputs.
- Сигнал: хотя бы один unique solve на фиксированном slice и не больше одной lost-задачи; на LB ожидается `+0.42` п.п. или подтверждение отсутствия эффекта.

## S4 — seed/view diversity в остаточном бюджете

- База: champion после S3; использовать adaptive skeleton из `kernels/nvarcplus-src/arc2-nvarc-v1.ipynb`.
- Гипотеза: независимый train/eval augmentation seed и иной view order полезнее для `attempt_2`, чем ещё один почти идентичный rank-2 beam.
- Единственное изменение: второй seed/view portfolio только для unprocessed outputs или outputs с менее чем двумя различными valid candidates. Primary pass не менять.
- Зафиксированный deep config только для phase 2: `LORA_SEED=137`, `TRAIN_AUG_SEED=17`, `EVAL_AUG_SEED=29`, `N_EVAL_AUG=3`, `MIN_PROB=0.1`, `DFS_WINDOW=600`, `SCORE_SEED_OFFSET=7`; порядок — unprocessed, затем меньше distinct candidates, затем меньший input-only estimated work.
- Ограничение: phase 2 стартует только после завершения primary, если осталось не менее 20 минут; task cap рассчитывается существующей формулой NVARC+; последние 10 минут неприкосновенны для finalization. Phase 2 не может удалить primary candidates.
- Сигнал: рост unique solves и сокращение `oracle pass@k -> pass@2` gap; отсутствие регрессии coverage/runtime.

## S5 — независимый TRM candidate

- База: `kernels/trm-src/arc-2026-nvarc-trm-aggressive-cost-order.ipynb`.
- Гипотеза: pretrained TRM решает другой класс задач и даёт реальную комплементарность Qwen.
- Единственное изменение к проверенному NVARC primary: GPU3 выполняет TRM, затем присоединяется к NVARC; `attempt_1 = NVARC rank1`, `attempt_2 = TRM rank1`, duplicate fallback как в notebook.
- Preflight: проверить обе прикреплённые TRM datasets, лицензионные receipts, 2k/4k checkpoints, handoff GPU3, hard stop и валидный partial fallback. До run разрешено только операционно закрепить точные dataset version IDs и SHA-256 файлов для `christopherdaleman/arc-proof-search-trm-2026-source` (MIT-0) и `cpmpml/arc-prize-trm-031` (CC0); если версию нельзя зафиксировать, не запускать.
- Сигнал: хотя бы один TRM-only exact solve на открытой evaluation-выборке либо LB `+0.42`; отдельно измерить потерю NVARC coverage из-за трёх стартовых workers.

## S6 — независимый VARC candidate

- База: `kernels/fayche-src/arc-prize-2026-solver.ipynb`.
- Гипотеза: независимый ARCViT/VARC test-time learner даст unique solutions как второй attempt.
- Единственное изменение: собственный private metadata/slug; архитектуру, `ttt_steps=60`, NVARC primary и merge rule upstream не менять.
- Preflight: на protocol V1 отдельно измерить NVARC-only и NVARC+VARC, VARC-only unique outputs, дополнительный runtime и потерю primary coverage. Проверить, что VARC никогда не заменяет отличный NVARC `attempt_1` и что timeout оставляет valid fallback.
- Сигнал: хотя бы один VARC-only solve либо hidden LB `+0.42`; вариант отклонить как final component при отсутствии unique solve и заметной потере NVARC coverage.

## S7 — evidence-gated portfolio

- База: champion и сохранённый diverse runner-up из S1–S6.
- Гипотеза: OOF-правило выбора из Qwen primary, seed portfolio, TRM и VARC лучше безусловного смешивания.
- Единственное изменение: финальный selector/gating; новых solver families и новых гиперпараметров не добавлять.
- Включать компонент только если S1–S6 подтвердили unique solve или независимый сигнал без существенной потери coverage.
- `attempt_1`: champion neural. `attempt_2`: лучший отличающийся кандидат по OOF gate. Hard stop 10:30, 80 минут на finalization/fallback.
- Сигнал: лучший pass@2, нулевой invalid rate, полный hidden coverage и валидный `submission.json` даже при частичном timeout.

## После S7

- Не выбирать две финальные submissions только по близким public score.
- Кандидат 1: максимальный подтверждённый score.
- Кандидат 2: наиболее устойчивый и отличающийся по solved-task matrix/seed/solver family.
- Недельную аналитику делает руководитель по `ops/STATE.json`, `ops/JOURNAL.md` и сохранённым run manifests.
