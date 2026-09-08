#!/usr/bin/env python3
"""Train a drop-in LoRA adapter on the packed public-train SFT corpus.

PEFT hyperparameters match src/arc2/arc_solver.py so the adapter can replace
random default_weights before per-task TTT. Evaluation solutions are not used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "arc2"))


PEFT_PARAMS = dict(
    r=256,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "embed_tokens",
        "lm_head",
    ],
    lora_alpha=32,
    lora_dropout=0.0,
    bias="none",
    use_gradient_checkpointing=True,
    random_state=42,
    use_rslora=True,
    loftq_config=None,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_examples(jsonl_path: Path, split: str, max_examples: int | None) -> list[dict]:
    rows = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("split") != split:
                continue
            rows.append({"text": row["text"], "example_id": row["example_id"], "kind": row["kind"]})
            if max_examples is not None and len(rows) >= max_examples:
                break
    if not rows:
        raise SystemExit(f"no examples for split={split}")
    return rows


def tokenize_rows(rows: list[dict], tokenizer, max_seq_length: int) -> list[dict]:
    out = []
    skipped = 0
    for row in rows:
        encoded = tokenizer(
            row["text"],
            truncation=True,
            max_length=max_seq_length,
            add_special_tokens=False,
        )
        ids = encoded["input_ids"]
        if len(ids) < 8:
            skipped += 1
            continue
        out.append({"input_ids": ids, "example_id": row["example_id"], "kind": row["kind"]})
    if not out:
        raise SystemExit("all examples were empty after tokenization")
    return out, skipped


def gpu_mem_gib() -> dict:
    info = {"cuda_available": False}
    try:
        import torch

        info["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            info["device"] = torch.cuda.get_device_name(0)
            info["allocated_gib"] = round(torch.cuda.memory_allocated() / (1024**3), 3)
            info["reserved_gib"] = round(torch.cuda.memory_reserved() / (1024**3), 3)
            if hasattr(torch.cuda, "max_memory_allocated"):
                info["peak_allocated_gib"] = round(torch.cuda.max_memory_allocated() / (1024**3), 3)
    except Exception as exc:  # pragma: no cover - receipt only
        info["error"] = str(exc)
    return info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--dataset-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--recipe", type=Path, default=ROOT / "configs" / "sft_recipe_v1.json")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-examples", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--max-seq-length", type=int, default=0)
    parser.add_argument("--mode", choices=["smoke", "sft"], default="sft")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    train_cfg = dict(recipe["train"])
    if args.mode == "smoke":
        train_cfg.update(
            {
                "max_seq_length": recipe["smoke"]["max_seq_length"],
                "gradient_accumulation_steps": 1,
            }
        )
        max_steps = recipe["smoke"]["max_steps"]
        max_examples = recipe["smoke"]["max_examples"]
    else:
        max_steps = args.max_steps or int(os.environ.get("ARC2_SFT_MAX_STEPS", "200"))
        max_examples = args.max_examples or None
        if max_examples == 0:
            max_examples = None
    if args.max_seq_length:
        train_cfg["max_seq_length"] = args.max_seq_length
    if args.max_examples:
        max_examples = args.max_examples
    if args.max_steps:
        max_steps = args.max_steps

    dataset_dir = args.dataset_dir
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    jsonl_path = dataset_dir / "examples.jsonl"
    if sha256_file(jsonl_path) != manifest["examples_sha256"]:
        raise SystemExit("examples.jsonl hash mismatch vs manifest")
    if manifest.get("contamination_eval_ids_in_train"):
        raise SystemExit("refusing contaminated dataset")

    os.environ.setdefault("UNSLOTH_DISABLE_STATISTICS", "1")
    from unsloth import FastLanguageModel, UnslothTrainingArguments
    from datasets import Dataset
    from arc_solver import QwenDataCollatorForCompletionOnlyLM, UnslothFixedTrainer

    started = time.time()
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(args.model),
        full_finetuning=False,
        load_in_4bit=False,
        local_files_only=True,
        use_gradient_checkpointing="unsloth",
        max_seq_length=int(train_cfg["max_seq_length"]),
    )
    model = FastLanguageModel.get_peft_model(model, **PEFT_PARAMS)
    import torch

    for _name, param in model.named_parameters():
        if param.dtype == torch.float32:
            param.data = param.data.to(torch.bfloat16)

    rows = load_examples(jsonl_path, split=args.split, max_examples=max_examples)
    tokenized, skipped = tokenize_rows(rows, tokenizer, int(train_cfg["max_seq_length"]))
    ds = Dataset.from_list([{"input_ids": row["input_ids"]} for row in tokenized])

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    adapter_dir = out / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)

    train_args = UnslothTrainingArguments(
        output_dir=str(out / "trainer_state"),
        per_device_train_batch_size=int(train_cfg["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(train_cfg["gradient_accumulation_steps"]),
        learning_rate=float(train_cfg["learning_rate"]),
        optim=str(train_cfg["optim"]),
        lr_scheduler_type=str(train_cfg["lr_scheduler_type"]),
        warmup_ratio=float(train_cfg["warmup_ratio"]),
        weight_decay=float(train_cfg["weight_decay"]),
        max_grad_norm=float(train_cfg["max_grad_norm"]),
        bf16=bool(train_cfg["bf16"]),
        fp16=bool(train_cfg["fp16"]),
        seed=int(train_cfg["seed"]),
        max_steps=int(max_steps),
        logging_steps=1 if args.mode == "smoke" else 10,
        save_strategy="no",
        report_to="none",
        dataloader_num_workers=0,
        gradient_checkpointing=True,
        remove_unused_columns=False,
    )
    collator = QwenDataCollatorForCompletionOnlyLM(tokenizer=tokenizer, mlm=False)
    trainer = UnslothFixedTrainer(
        model=model,
        args=train_args,
        train_dataset=ds,
        data_collator=collator,
    )
    train_result = trainer.train()
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    adapter_files = {}
    for path in sorted(adapter_dir.rglob("*")):
        if path.is_file():
            adapter_files[str(path.relative_to(adapter_dir))] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    receipt = {
        "run_id": args.run_id,
        "mode": args.mode,
        "recipe_id": recipe["recipe_id"],
        "dataset_id": manifest["dataset_id"],
        "dataset_examples_sha256": manifest["examples_sha256"],
        "n_examples_used": len(tokenized),
        "n_examples_skipped_short": skipped,
        "max_steps": max_steps,
        "max_seq_length": train_cfg["max_seq_length"],
        "metrics": dict(getattr(train_result, "metrics", {}) or {}),
        "gpu": gpu_mem_gib(),
        "elapsed_s": round(time.time() - started, 2),
        "adapter_files": adapter_files,
        "visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "notes": "Train-only adapter. Do not bake public evaluation solutions into a scored kernel.",
    }
    receipt_path = out / "receipt.json"
    receipt_text = json.dumps(receipt, indent=2) + "\n"
    receipt_path.write_text(receipt_text, encoding="utf-8")
    (out / "receipt.sha256").write_text(sha256_bytes(receipt_text.encode("utf-8")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "run_id": args.run_id, "adapter_dir": str(adapter_dir), "elapsed_s": receipt["elapsed_s"]}))


if __name__ == "__main__":
    main()
