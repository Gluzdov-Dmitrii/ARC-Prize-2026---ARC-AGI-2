"""Portable NVARC starter: N workers = N allocated devices; paths from CLI/env."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.multiprocessing as mp

DEBUG4 = ["0934a4d8", "36a08778", "981571dc", "aa4ec2a5"]
CALIBRATION12 = [
    "a32d8b75",
    "9aaea919",
    "3a25b0d8",
    "a47bf94d",
    "cb2d8a2c",
    "1ae2feb7",
    "8e5c0c38",
    "cbebaa4b",
    "2c181942",
    "5dbc8537",
    "4a21e3da",
    "271d71e2",
]


def parse_devices(raw: str) -> list[str]:
    devices = [part.strip() for part in raw.split(",") if part.strip()]
    if not devices:
        raise SystemExit("Need at least one --devices UUID or ordinal")
    return devices


def load_task_ids(manifest_path: str | None, mode: str, all_keys: list[str]) -> list[str]:
    if manifest_path:
        text = Path(manifest_path).read_text(encoding="utf-8")
        ids = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
        missing = [task_id for task_id in ids if task_id not in all_keys]
        if missing:
            raise SystemExit(f"task-manifest IDs not in input: {missing[:8]}")
        return ids
    if mode == "smoke":
        return [task_id for task_id in DEBUG4 if task_id in all_keys]
    if mode == "eval":
        return [task_id for task_id in CALIBRATION12 if task_id in all_keys]
    if mode == "full":
        return sorted(all_keys)
    raise SystemExit(f"unknown mode {mode}")


def local_worker(rank, queue, end_time, devices, worker_dir):
    os.environ["CUDA_VISIBLE_DEVICES"] = devices[rank]
    torch.set_default_device("cpu")
    worker_dir = Path(worker_dir)
    worker_dir.mkdir(parents=True, exist_ok=True)
    if rank > 0:
        prev = worker_dir / f"worker{rank - 1}"
        while not prev.exists():
            time.sleep(5)
    from arc_solver import worker

    (worker_dir / f"worker{rank}").write_text("Ok", encoding="utf-8")
    print(f"[Rank {rank}] start device={devices[rank]}", flush=True)
    worker(rank, queue, end_time)
    print(f"[Rank {rank}] done!", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-2 NVARC portable runner")
    parser.add_argument("--input", required=True, help="Challenges JSON (no solutions)")
    parser.add_argument("--model", required=True, help="Local Qwen snapshot directory")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--task-manifest", default=None)
    parser.add_argument("--devices", required=True, help="Comma-separated GPU UUIDs")
    parser.add_argument("--seed", type=int, default=260618)
    parser.add_argument("--max-seconds", type=float, default=1800)
    parser.add_argument("--mode", choices=["smoke", "eval", "full"], default="smoke")
    parser.add_argument("--end-time", type=float, default=0.0, help="Absolute unix deadline; overrides max-seconds if >0")
    args = parser.parse_args()

    devices = parse_devices(args.devices)
    n_workers = len(devices)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    worker_dir = output_dir / "workers"
    worker_dir.mkdir(parents=True, exist_ok=True)

    os.environ["ARC2_MODEL_PATH"] = args.model
    os.environ["ARC2_INPUT_PATH"] = args.input
    os.environ["ARC2_OUTPUT_DIR"] = str(output_dir / "inference_outputs")
    os.environ.setdefault("PYTHONHASHSEED", str(args.seed))
    os.environ.setdefault("ARC_AUG_SEED_OFFSET", str(args.seed))
    os.environ.setdefault("UNSLOTH_DISABLE_STATISTICS", "1")
    os.makedirs(os.environ["ARC2_OUTPUT_DIR"], exist_ok=True)

    with open(args.input, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    task_ids = load_task_ids(args.task_manifest, args.mode, list(data.keys()))
    (output_dir / "queued_tasks.json").write_text(
        json.dumps({"mode": args.mode, "task_ids": task_ids, "n_workers": n_workers}, indent=2) + "\n",
        encoding="utf-8",
    )

    queue = mp.Manager().Queue()
    for key in task_ids:
        queue.put(key)
    for _ in range(n_workers):
        queue.put(None)

    deadline = args.end_time if args.end_time > 0 else time.time() + args.max_seconds
    mp.spawn(
        local_worker,
        args=(queue, deadline, devices, str(worker_dir)),
        nprocs=n_workers,
        join=True,
    )


if __name__ == "__main__":
    main()
