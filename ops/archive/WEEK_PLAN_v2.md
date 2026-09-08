# ARC Prize 2026 — план оставшихся сабмитов, revision 2

Версия: `arc2-week-2026-09-05-v2-external`; актуализация руководителем 2026-09-07 по запросу пользователя.
Competition: `arc-prize-2026-arc-agi-2`. История недели и ID S1–S7 сохраняются.
Исходный план: `ops/archive/WEEK_PLAN_v1.md`. Исполнитель не редактирует текущий план; работает через STATE и append-only JOURNAL.

## Решение и исходная точка

Подготовку, public-evaluation, перебор seeds и проверку дополнительных solver families перенести на NSU. В Kaggle — только короткий интеграционный Save & Run All финального кандидата и разрешённый пользователем scored submission. Обновление дневного лимита не обязывает тратить попытку на неподготовленное решение.

- Champion: Mikelou perfpatch, submission 56004028, public 30.56.
- S1 COMPLETE: 27.36; commit-run 19303 s (5.36 h). Надёжность формата не дала выигрыша качества.
- S2 COMPLETE: 30.28; commit-run 1534 s. Стабильные seeds сами по себе пока не улучшили champion.
- S3 submission 56068142 остаётся PENDING при текущей read-only проверке 2026-09-07; не отправлять повторно. История не переписывается.
- S3 фактически построен на S2, а не на исходном champion. Его debug-4 (3.0/4, selectors tied) — smoke, не доказательство выигрыша selector и не выполненная Calibration-12.
- Ранг и gold cutoff из 5 сентября устарели; обновлять при следующем готовом submission, не выдавать за текущие.
- Цель 35–37+ остаётся исследовательским ориентиром, не прогнозом на четыре следующих попытки.

## Ресурсы и бюджет

Основной профиль ARC-2: одна A100 80 GB, один model worker, 8 CPU threads, до 64 GiB RAM; ограничить рабочий peak VRAM до 22 GiB для переносимости на L4 24 GB. Увеличение контекста, batch, числа кандидатов и search budget за счёт 80 GB запрещено без отдельного эксперимента совместимости. Вторую A100 использовать для независимого shard только при общей резервации и отсутствии ожидающего проекта. Это не объединённые 160 GB и не обязательный distributed training.

RTX 6000 в справочнике — Quadro/Turing 24 GB, а не Ada. Текущий solver явно приводит параметры к BF16: совместимость не доказана. FP16/SDPA-порт — отдельный эксперимент, в критический путь недели его не включать. RTX 3080 — 10 GB/Windows, меньше наблюдавшегося peak 17.1 GB: только CPU-подготовка или небольшая модель после отдельной проверки.

NSU: chunks <=120 минут с сохранением после каждой задачи и освобождением ресурса между chunks при конкуренции. Первый pilot <=30 минут; первоначальный бюджет каждой S4–S6 — до 4 GPU-h, продолжение до 8 GPU-h суммарно только при положительном pilot и записи причины. Полная базовая evaluation — до 16 GPU-h; оценку уточнить по pilot. Это пределы планирования, а не обещанные runtime.
Начальная оценка диска ARC-2: 40–60 GiB (окружение, одна копия модели, wheels, checkpoints и candidate cache); расширение до 100 GiB только по фактическому inventory и подтверждённому бюджету shared storage.

Kaggle: целевой commit-run <=30 минут wall-clock; внутренний hard stop 45 минут, включая setup/finalization. L4×4 сейчас списывает обычную GPU-квоту с коэффициентом 2: четыре 30-минутных commits = около 4 quota-h, четыре 45-минутных = 6 quota-h. Общий потолок ARC-2 для оставшихся S4–S7: 6 quota-h на подготовительные commits, уменьшать его при меньшем account-wide остатке/резервах других проектов. Никаких GPU validation sweeps на Kaggle.
Дневной submission-limit, недельная GPU-квота и доступность/concurrency — разные ограничения. `submission-limits` показывает только первое. Учёт hidden rerun в недельной квоте здесь НЕ подтверждён для ARC-2: фиксировать отдельно и не обещать бесплатный scoring. Полный runtime hidden <=12 h; вычисления останавливаются в 10:30, finalization/fallback завершается до 11:50. Время до появления score включает очередь и обфускацию, это не GPU-runtime.

## M0 — перенос и восстановление baseline, без competition submit

Подробный checklist: `ops/EXTERNAL_COMPUTE.md`. Это обязательная предпосылка S4–S7, статусы в `STATE.migration`.

1. CPU: зафиксировать код champion/S2/S3, input/model hashes и окружение успешного S2. Выделить portable runner из notebook, не менять solver-математику.
2. Runtime: явные пути, task manifest, device list, seed и режим smoke/eval/full; число workers равно числу разрешённых устройств. Убрать hard-coded четыре процесса и перенумерацию чужих GPU. Отделить scorer от solver.
3. Environment: отдельное Linux ML-окружение по фактическому lock; существующее stdlib-only venv не изменять. Согласовать Python/Torch/CUDA/Unsloth/Triton с драйвером и Kaggle image; не считать успешный CUDA probe проверкой Qwen.
4. Pilot: после общего resource reservation — одна A100, реальная загрузка Qwen, train/DFS/rescore минимум одной задачи, измерения RAM/VRAM/runtime, завершение worker/lease. Затем paired Calibration-12 для исходного champion и S2; S3 selector сравнивается на сохранённых candidates S2 без повторного GPU generation.
5. Выбрать external baseline по парному сравнению. Champion LB и выбранный reproducible external baseline хранить отдельно. При отсутствии доказанного выигрыша S2 не объявлять его champion. Для legacy нестабильного seed записать эффективные per-task seeds и ограничения воспроизводимости.
6. Один раз собрать полный public-evaluation candidate cache замороженной базы, chunks <=2 h. Остальные варианты сначала на Calibration-12; полную evaluation получает только finalist.
7. Экспортировать manifests, candidate bank и scorer report в проект, сохранить нужные remote inputs для конкретных следующих runs; очистить только свои ненужные промежуточные файлы.

M0 не занимает дневную попытку. Пока S3 PENDING, можно выполнять M0 и внешнюю подготовку; новая competition submission запрещена до сверки S3.

## Validation V2

Сохраняем прежние task IDs, чтобы не менять выборку вслед за результатами:
- Calibration-12: `a32d8b75,9aaea919,3a25b0d8,a47bf94d,cb2d8a2c,1ae2feb7,8e5c0c38,cbebaa4b,2c181942,5dbc8537,4a21e3da,271d71e2`.
- Holdout-8: `13e47133,31f7f899,b9e38dc0,3e6067c3,4e34c42c,b5ca7ac4,67e490f4,2d0172a1`.
- SHA-256 IDs по одному на строку с финальным newline: `b798899dc1452d681b6849c3c1b93237ab5df6bd5193be53b90a14ef2f379155`.
- Primary metric V2 по текущему официальному описанию: `100 * correct_test_outputs / all_test_outputs`, correct = exact match хотя бы одного attempt. Дополнительно сохранять legacy task-macro для сопоставления старых логов; не смешивать его с primary и не пересчитывать опубликованные LB scores.
- Убрать старое правило «минимальный квант 0.42»: он не универсален. Любой строго больший scored public обновляет best_public; маленькую разницу не объявлять статистически надёжным улучшением.
- Solver получает только train-пары и test-inputs. Evaluation solutions доступны отдельному scorer после заморозки outputs, не модели/selector во время генерации. Public candidate caches разрешены только для внешних сравнений; hidden predictions всегда вычисляются заново.
- Для каждого варианта: pass@1, pass@2, gained/lost test keys, independent unique solves, candidate coverage и fallback rate, score distributions, runtime/VRAM. Полнота JSON отдельно от полноты реально найденных решений.
- Calibration используется для выбора из заранее ограниченных вариантов. Holdout-8 — однократная проверка frozen finalist стадии; повторное использование между стадиями раскрывается, это уже не независимый финальный holdout. Full-120 после выбора — сравнительный benchmark, не unbiased CV.
- Для генерирующих GPU-экспериментов одинаковые seeds, augmentation/step/token/candidate caps и backend у пары. Качество фиксированного объёма поиска и качество при time limit измерять раздельно: скорость A100 нельзя считать скоростью L4.
- CPU selectors оцениваются на одном и том же банке candidates; GPU рескоринг нужен только если отсутствует необходимая feature. Ключ кеша включает input/content hash, code, model, env/backend, seed, budget и task ID.
- Порог допуска S4–S6: Calibration pass@2 растёт, есть >=1 gained output; у frozen finalist на Holdout-8 нет net regression, invalid rate 0, primary coverage не ухудшена. Один gain на 12 задачах — слабый сигнал; для финального решения проверить full-120, особенно потери и runtime.
- При провале gate стадия становится SKIPPED_VALIDATION (статус стадии SKIPPED с причиной), квоту не тратить. Технический сбой — RETRY_PENDING той же стадии. S7 без допущенных компонентов может закончиться NO_NEW_CANDIDATE без submission.

## Следующие четыре стадии

| Стадия | Подготовка вне Kaggle | Кандидат для Kaggle и критерий |
|---|---|---|
| S4 seed/view diversity | На одной A100 primary + прежний фиксированный deep config; candidates и selector на CPU. Ограничить deep только outputs с <2 distinct candidates; сравнить с замороженной базой. | Только прошедший gate portfolio в остаточном бюджете. Primary сохраняется. Если deep не даёт gain, SKIPPED. |
| S5 TRM | Существующий `kernels/trm-src/arc-2026-nvarc-trm-aggressive-cost-order.ipynb`: отдельно измерить TRM и NVARC, paired gains/losses, затем объединить candidates на CPU. | В Kaggle проверить реальный layout 3×NVARC + GPU3 TRM/handoff. Не считать sequential A100-run доказательством 4-L4 concurrency; если coverage падает, отклонить. |
| S6 VARC | Существующий `kernels/fayche-src/arc-prize-2026-solver.ipynb`, `ttt_steps=60`: одна A100, отдельная оценка unique solves и расходов. Начать лишь после кандидата/отчёта S5. | Добавлять VARC только при доказанной пользе; ограничить pilot, не строить новый training pipeline и не повышать steps. При отсутствии gain SKIPPED. |
| S7 portfolio | На CPU выбрать между не более чем тремя frozen правилами по общему candidate bank; затем единственный full-120 прогон выбранного портфеля вне Kaggle. | Лучший проверенный primary + полезный отличный attempt_2. Никаких новых solver families/весов. При отсутствии улучшения сохранить прежние submissions и не отправлять дубль. |

S4 deep config из V1: `LORA_SEED=137, TRAIN_AUG_SEED=17, EVAL_AUG_SEED=29, N_EVAL_AUG=3, MIN_PROB=0.1, DFS_WINDOW=600, SCORE_SEED_OFFSET=7`. Phase2 только после primary и при >=20 min остатка; прежняя формула per-task cap, остановка вычислений не позже общего cap 10:30. Не удалять primary candidates.
S5 до загрузки закрепляет версии/хеши и license receipts `christopherdaleman/arc-proof-search-trm-2026-source` и `cpmpml/arc-prize-trm-031`; готовые checkpoints, не полное обучение TRM с нуля.
S7 три допустимых правила: (1) champion attempt2; (2) лучший независимый solver rank1 с duplicate fallback; (3) S3 diversity selector на объединённом банке. Выбор только на calibration; не подбирать дополнительные пороги на holdout.

## Короткий Kaggle commit

После внешнего gate отправлять одну private notebook version: реальный GPU smoke на малом открытом наборе, imports/train/infer/merge/fallback и полный schema-valid output для открытого mount. Записывать долю реально вычисленных outputs; fallback не выдавать за solve.
В scored rerun — тот же solver на всех текущих скрытых задачах, полный budget, без public prediction cache и без ограничения debug-ID. Уже используемый platform rerun signal проверить как отдельную ветку теста; не определять hidden по известному числу/ID задач. Если менялся runtime/backend/worker topology, проверить этот путь на NSU в full-режиме на открытом mount и интеграционно на L4.
Не применять CPU/dummy Save Version как способ пропустить GPU-совместимость. При превышении 45 min собственный commit останавливается с сохранённым fallback, но readiness считается FAILED: автоматического submit не делать. Общий watchdog включает все subprocesses.

## Ежедневное выполнение и журнал

Команда «Засабмить следующее решение» разрешает подготовить и отправить не более одной следующей допущенной стадии. До submit можно последовательно пропустить отклонённые по validation стадии с записью причин. Если требуется M0, сначала выполнить его в пределах доступного compute; календарный день можно завершить без submit с точным статусом подготовки.
Перед любой записью перечитывать STATE, сохранять чужие новые события; один исполнитель меняет состояние, второй не редактирует активную стадию.
Сначала закрыть существующий pending submission read-only. После любого submit call только проверка статуса, ни одного retry в той же команде, включая ERROR/timeout.
Для подготовки вести `STATE.migration`, `STATE.compute_policy`, `ops/local_runs/<run_id>/`; для Kaggle — прежние `ops/runs/<attempt_id>/`. Отчёт: local score и uncertainty, ресурсы/lease, env hashes, cache lineage, GPU-h, Kaggle quota-h до/после, submitted version и LB/rank delta. Недоступные значения null + причина. Candidate cache/weights в git не помещать.
GPU-h NSU = сумма времени реально выделенных устройств; Kaggle quota-h = показания платформы, а 2×wall-clock только оценка. Время ожидания ресурса и hidden scoring duration — отдельные поля.
Сохранять best_public и diverse runner-up отдельно. После S7 руководитель сравнивает эффективность методов на единицу compute и формирует следующую неделю.

## Источники

- [Официальные code requirements, evaluation и L4 quota multiplier](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/).
- [Kaggle GPU usage](https://www.kaggle.com/docs/efficient-gpu-usage).
- [Code submissions и rerun](https://www.kaggle.com/docs/competitions).
- Ресурсы: `C:/Users/Dmitry/Desktop/Kaggle/Kaggle Agents/external-resources/`; текущий remote `_control/COORDINATION_STATUS.json` проверен 2026-09-07, `DIRECT_USER_AUTHORIZED`, резервация обязательна.
- Техническая реализация переноса и точные пути: `ops/EXTERNAL_COMPUTE.md`.
