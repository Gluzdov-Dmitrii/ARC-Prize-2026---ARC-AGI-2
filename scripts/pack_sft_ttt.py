#!/usr/bin/env python3
"""Pack public-train tasks in the same view family as per-task TTT.

Inference TTT trains on augmented train pairs with last_is_challenge=True.
It does not use training-task test solutions. This pack follows that format.
Evaluation / hidden IDs never enter the train split.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "arc2"))

from arc_loader import ArcDataset, QwenFormatter  # noqa: E402

EXPECTED = {
    "arc-agi_training_challenges.json": "779eaba89790ebad9af02514a7efc0aefaf2cf8236f046a31bbf8b9ec48f20f5",
    "arc-agi_training_solutions.json": "9f07a38bd25af5e83aa5bf85c5cb1a1fefdb30f6a755256fa65429e697ca97f9",
    "arc-agi_evaluation_challenges.json": "e7c62a4bd211867c6b538f66b8013b81f299663c82ca062f49a52bf439d6e4e8",
}

DATASET_ID = "sft-public-train-v2"
SEED_TAG = "arc2-m3-ttt-aug-v1"
HOLDOUT_N = 32
AUG_N = 2
AUG_SEED = 1


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


def pack_augmented_tasks(challenges: dict, train_ids: list[str], holdout_set: set[str]) -> list[dict]:
    formatter = QwenFormatter(tokenizer=None)
    queries = {}
    for task_id in train_ids:
        train = challenges[task_id]["train"]
        if not train:
            continue
        queries[task_id] = {"train": train, "test": [train[-1]]}
    dataset = ArcDataset(queries=queries, keys=sorted(queries))
    augmented = dataset.augment(n=AUG_N, shfl_keys=True, seed=AUG_SEED)
    rows = []
    for key in augmented.keys:
        task_id = key.split(".")[0]
        train = augmented.queries[key]["train"]
        if not train:
            continue
        rows.append(
            {
                "task_id": task_id,
                "example_id": key,
                "kind": "ttt_aug",
                "split": "holdout" if task_id in holdout_set else "train",
                "text": formatter.fmt_train(train, last_is_challenge=True),
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
        if digest != EXPECTED[label]:
            raise SystemExit(f"hash mismatch {label}: {digest} != {EXPECTED[label]}")
        hashes[label] = digest

    challenges = load_json(args.train_challenges)
    solutions = load_json(args.train_solutions)
    eval_ids = set(load_json(args.eval_challenges))
    train_ids = sorted(challenges)
    leaked = sorted(set(train_ids) & eval_ids)
    if leaked:
        raise SystemExit(f"eval IDs leaked into train: {leaked[:8]}")
    missing = [task_id for task_id in train_ids if task_id not in solutions]
    holdout_ids = train_ids[-HOLDOUT_N:]
    holdout_set = set(holdout_ids)
    train_split_ids = [task_id for task_id in train_ids if task_id not in holdout_set]
    rows = pack_augmented_tasks(challenges, train_ids, holdout_set)
    train_task_ids = {row["task_id"] for row in rows if row["split"] == "train"}
    leaked_rows = sorted(train_task_ids & eval_ids)
    if leaked_rows:
        raise SystemExit(f"eval IDs leaked into packed train rows: {leaked_rows[:8]}")

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
        "n_train_examples": sum(1 for row in rows if row["split"] == "train"),
        "n_holdout_examples": sum(1 for row in rows if row["split"] == "holdout"),
        "n_skipped_missing_solutions": len(missing),
        "holdout_ids": holdout_ids,
        "eval_id_count": len(eval_ids),
        "contamination_eval_ids_in_train": [],
        "kinds": sorted({row["kind"] for row in rows}),
        "augment_n": AUG_N,
        "augment_seed": AUG_SEED,
        "source_sha256": hashes,
        "examples_sha256": sha256_bytes(jsonl_bytes),
        "examples_bytes": len(jsonl_bytes),
        "notes": "TTT-matched train-only views. Do not mount into the scored solver as a solutions cache.",
    }
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    (out / "manifest.json").write_text(manifest_text, encoding="utf-8")
    (out / "manifest.sha256").write_text(sha256_bytes(manifest_text.encode("utf-8")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_dir": str(out), "n_examples": len(rows), "n_train_examples": manifest["n_train_examples"]}))


if __name__ == "__main__":
    main()
