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

`scripts/build_kaggle_notebook.py` copies the S2 4×L4 starter and inlines current `arc_loader.py` / `arc_decoder.py` / `arc_solver.py`. Competition submit is a separate user command. Kernel push is not a submit.
