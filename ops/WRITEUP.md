# ARC-2 M1 community writeup

How to reproduce the leftover artifacts for `arc-prize-2026-arc-agi-2`. This is documentation, not a scored kernel.

## What stays even if public LB is flat

1. Official public-train hashes:
   - `arc-agi_training_challenges.json` SHA-256 `779eaba89790ebad9af02514a7efc0aefaf2cf8236f046a31bbf8b9ec48f20f5`
   - `arc-agi_training_solutions.json` SHA-256 `9f07a38bd25af5e83aa5bf85c5cb1a1fefdb30f6a755256fa65429e697ca97f9`
2. Packed SFT corpus `sft-public-train-v1` (`scripts/pack_sft_dataset.py`): train-only examples, holdout of 32 **training** IDs, contamination check vs evaluation challenge IDs.
3. Base Qwen `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1`, local tar SHA-256 `cee6e64f3b4f759813f378bdd644d5780a55b540339a7a4e2bfd17faa4fe71ee`.
4. Env recipe: `scripts/install_ml_env.sh` — torch 2.6.0+cu124, `unsloth==2025.9.7` `--no-deps`. Do not install latest Unsloth extras (they pull CUDA 13 / torch 2.14).
5. SFT recipe: `configs/sft_recipe_v1.json`. LoRA `r=256` matches per-task TTT in `src/arc2/arc_solver.py` so the adapter can replace random `default_weights`.
6. Adapter run `arc2-m1-sft-20260908T0805Z`: 160 steps, train_loss 0.187, peak 11.7 GiB on one A100. `adapter_model.safetensors` SHA-256 `2ef3b65720eee8e1ff20c55934dfb3a63371350d2b1e9217c2a86912e3ee1d07` (1057197776 bytes). Receipt: `ops/local_runs/arc2-m1-sft-20260908T0805Z/receipt.json`.

Packed corpus `sft-public-train-v1`: 5308 examples, examples SHA-256 `e9f43ed0e0db5f118d4e8e45a44aeddcaeeb9c302538e5a437217264d20c4bee`, eval-ID contamination empty. Manifest copy: `configs/sft-public-train-v1.manifest.json`.

## What must not go in a scored Kaggle kernel

- Evaluation or hidden solutions.
- Public candidate caches from local eval.
- Internet downloads. Hidden test is scored on Kaggle with Internet OFF.
- Kaggle tokens or SSH keys.

## Short SFT on one GPU

1. Pack: `python scripts/pack_sft_dataset.py --train-challenges ... --train-solutions ... --eval-challenges ... --output-dir data/sft/sft-public-train-v1`
2. Reserve one A100 via `resource_queue.py` on `nsu-quadro`. Heartbeat ≤60s. Release after the process tree exits.
3. Smoke (`--mode smoke`, 1 step) then a timed SFT chunk (`scripts/train_sft.py`).
4. Inference still runs per-task TTT. The adapter is only the new initialization.

## Notebook

`scripts/build_kaggle_notebook.py` copies the S2 4×L4 starter, replaces the Chinese markdown with a short original English note, and inlines current `arc_loader.py` / `arc_decoder.py` / `arc_solver.py`. Competition submit is a separate user command. Kernel push is not a submit.

## M2 (2-epoch adapter)

- Same train-only corpus `sft-public-train-v1` (examples SHA-256 `e9f43ed0e0db5f118d4e8e45a44aeddcaeeb9c302538e5a437217264d20c4bee`).
- Recipe `configs/sft_recipe_v2.json`: 2 epochs, seq 2048, LoRA `r=256`.
- Run `arc2-m2-sft-20260909T0605Z` on one A100: 2566 steps, train_loss **0.0583**, 3004 s, peak 11.7 GiB. RTX 3080 10 GB is below that peak.
- `adapter_ttt.safetensors` 1057197744 B, SHA-256 `3225701eacd6aafeee257a54fc9c1b33676e0e1625d88d7ba5a7ee50e38fe9e1`. Receipt: `ops/local_runs/arc2-m2-sft-20260909T0605Z/receipt.json`.
- Kaggle dataset `dmitriigluzdov/arc2-m2-sft-adapter-v1`. Notebook `kernels/arc2-m2-sft-adapter/` (title `ARC-AGI-2 public-train LoRA`). The solver writes `adapter_load.json` so a missed load is visible in logs.
- Scored public **30.14** (`56119847`). Below champion 30.56. Keep the notebook private.

## M3 (TTT-matched 1-epoch adapter)

- New pack `sft-public-train-v2` (`scripts/pack_sft_ttt.py`): same 8 geometries + 2 color perms as TTT, `last_is_challenge` on train pairs only. 16000 views, 15488 train / 512 holdout. examples SHA-256 `161a5e720b083ab815b2498e5f1bb64969a0fd3fe943a6c3f2923f975ce39493`. No eval IDs. No training-task test solutions.
- Recipe `configs/sft_recipe_v3.json`: 1 epoch from the **base** Qwen (not the M2 adapter), LR `2e-5`, seq 2048. Skip examples longer than 2048 so the completion collator stays valid.
- Run `arc2-m3-sft-20260910T0338Z` on one A100: 13552 examples used, 1936 skipped, train_loss **0.1585**, 3526 s, peak 11.7 GiB. Lease RELEASED.
- `adapter_ttt.safetensors` 1057197744 B, SHA-256 `c5972c8fffab19261b561197909bbd989a017dbf5fd76d219f183995c171a287`. Receipt: `ops/local_runs/arc2-m3-sft-20260910T0338Z/receipt.json`.
- Kaggle dataset `dmitriigluzdov/arc2-m3-sft-adapter-v1`. Notebook `kernels/arc2-m3-sft-adapter/` (title/slug `arc2-m3-ttt-lora`), private, Internet off.
- Commit-run COMPLETE; adapter loaded 506/506. Competition submit `56138632` scored public **30.14**. Same as M2. Keep the notebook private.

## M4 (scaled M3 LoRA)

- Same frozen adapter `dmitriigluzdov/arc2-m3-sft-adapter-v1` (SHA-256 `c5972c8fffab19261b561197909bbd989a017dbf5fd76d219f183995c171a287`).
- Inference-only change: `ARC2_ADAPTER_SCALE=0.25` on LoRA A/B tensors; embed and lm_head stay at the trained values. Per-task TTT unchanged.
- Notebook `kernels/arc2-m4-lora-scale/` (title/slug `arc2-m4-lora-scale`), private, Internet off.
- Commit-run COMPLETE; adapter loaded 506/506, scale=0.25, lora=504. Competition submit `56159237` PENDING. Keep the notebook private.
