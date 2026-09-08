#!/usr/bin/env python3
"""Pack official public-train ARC-2 tasks into Qwen chat strings for SFT.

Evaluation / hidden IDs never enter the train split. Solutions stay in this
train-only artifact; the inference solver does not read it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "arc2"))

from arc_loader import convert_grid_to_string  # noqa: E402

EXPECTED = {
    "arc-agi_training_challenges.json": "779eaba89790ebad9af02514a7efc0aefaf2cf8236f046a31bbf8b9ec48f20f5",
    "arc-agi_training_solutions.json": "9f07a38bd25af5e83aa5bf85c5cb1a1fefdb30f6a755256fa65429e697ca97f9",
    "arc-agi_evaluation_challenges.json": "e7c62a4bd211867c6b538f66b8013b81f299663c82ca062f49a52bf439d6e4e8",
}

DATASET_ID = "sft-public-train-v1"
HOLDOUT_N = 32
SEED_TAG = "arc2-m1-sft-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_pair(inp, out) -> str:
    grid_input = convert_grid_to_string(inp)
    grid_output = convert_grid_to_string(out)
    return f"<|im_start|>user\n{grid_input}<|im_end|><|im_start|>assistant\n{grid_output}<|im_end|>"


def fmt_query(inp) -> str:
    return "<|im_start|>user\n" + convert_grid_to_string(inp) + "<|im_end|><|im_start|>assistant\n"


def fmt_reply(out) -> str:
    return convert_grid_to_string(out) + "<|im_end|>"


def pack_task(task_id: str, task: dict, solutions: list, split: str) -> list[dict]:
    train = task["train"]
    tests = task["test"]
    rows = []
    if not train:
        return rows
    demo = "".join(fmt_pair(x["input"], x["output"]) for x in train)
    rows.append(
        {
            "task_id": task_id,
            "example_id": f"{task_id}.demo",
            "kind": "train_pairs",
            "split": split,
            "text": demo,
        }
    )
    if len(train) >= 2:
        for idx, held in enumerate(train):
            ctx = [p for j, p in enumerate(train) if j != idx]
            text = "".join(fmt_pair(x["input"], x["output"]) for x in ctx)
            text += fmt_query(held["input"]) + fmt_reply(held["output"])
            rows.append(
                {
                    "task_id": task_id,
                    "example_id": f"{task_id}.loo.{idx}",
                    "kind": "leave_one_out",
                    "split": split,
                    "text": text,
                }
            )
    if solutions and len(solutions) == len(tests):
        for idx, (probe, sol) in enumerate(zip(tests, solutions)):
            text = demo + fmt_query(probe["input"]) + fmt_reply(sol)
            rows.append(
                {
                    "task_id": task_id,
                    "example_id": f"{task_id}.test.{idx}",
                    "kind": "supervised_test",
                    "split": split,
                    "text": text,
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-challenges", required=True, type=Path)
    parser.add_argument("--train-solutions", required=True, type=Path)
    parser.add_argument("--eval-challenges", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    hashes = {}
    for label, path in [
        ("arc-agi_training_challenges.json", args.train_challenges),
        ("arc-agi_training_solutions.json", args.train_solutions),
        ("arc-agi_evaluation_challenges.json", args.eval_challenges),
    ]:
        digest = sha256_file(path)
        expected = EXPECTED[label]
        if digest != expected:
            raise SystemExit(f"hash mismatch {label}: {digest} != {expected}")
        hashes[label] = digest

    challenges = load_json(args.train_challenges)
    solutions = load_json(args.train_solutions)
    eval_ids = set(load_json(args.eval_challenges))
    train_ids = sorted(challenges)
    leaked = sorted(set(train_ids) & eval_ids)
    if leaked:
        raise SystemExit(f"eval IDs leaked into train: {leaked[:8]}")

    holdout_ids = train_ids[-HOLDOUT_N:]
    holdout_set = set(holdout_ids)
    train_split_ids = [task_id for task_id in train_ids if task_id not in holdout_set]

    rows = []
    skipped = []
    for task_id in train_ids:
        if task_id not in solutions:
            skipped.append(task_id)
            continue
        split = "holdout" if task_id in holdout_set else "train"
        rows.extend(pack_task(task_id, challenges[task_id], solutions[task_id], split))

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / "examples.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    jsonl_bytes = jsonl_path.read_bytes()
    manifest = {
        "dataset_id": DATASET_ID,
        "seed_tag": SEED_TAG,
        "n_tasks": len(train_ids),
        "n_train_split_tasks": len(train_split_ids),
        "n_holdout_tasks": len(holdout_ids),
        "n_examples": len(rows),
        "n_skipped_missing_solutions": len(skipped),
        "holdout_ids": holdout_ids,
        "eval_id_count": len(eval_ids),
        "contamination_eval_ids_in_train": [],
        "kinds": sorted({row["kind"] for row in rows}),
        "source_sha256": hashes,
        "examples_sha256": sha256_bytes(jsonl_bytes),
        "examples_bytes": len(jsonl_bytes),
        "notes": "Train-only SFT corpus. Do not mount into the scored solver as a solutions cache.",
    }
    manifest_path = out / "manifest.json"
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    (out / "manifest.sha256").write_text(sha256_bytes(manifest_text.encode("utf-8")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_dir": str(out), "n_examples": len(rows), "n_holdout": len(holdout_ids)}))


if __name__ == "__main__":
    main()
