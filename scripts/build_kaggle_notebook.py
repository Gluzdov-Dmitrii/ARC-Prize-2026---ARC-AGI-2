#!/usr/bin/env python3
"""Assemble a private Kaggle notebook from portable sources + the S2 4xL4 starter."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S2_NOTEBOOK = ROOT / "kernels" / "arc2-s2-nvarc-seed-fork" / "arc-agi2-lb33-89-minimal-perfpatch.ipynb"
SRC = ROOT / "src" / "arc2"
WRITEFILES = {
    "arc_loader.py": SRC / "arc_loader.py",
    "arc_decoder.py": SRC / "arc_decoder.py",
    "arc_solver.py": SRC / "arc_solver.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cell_text(cell: dict) -> str:
    src = cell.get("source", [])
    if isinstance(src, str):
        return src
    return "".join(src)


def make_writefile_cell(filename: str, body: str) -> dict:
    source = f"%%writefile {filename}\n{body}"
    if not source.endswith("\n"):
        source += "\n"
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [source],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", default="arc2-m1-sft-adapter-fork")
    parser.add_argument("--slug", default="dmitriigluzdov/arc2-m1-sft-adapter-fork")
    parser.add_argument("--adapter-dataset", default="")
    args = parser.parse_args()

    nb = json.loads(S2_NOTEBOOK.read_text(encoding="utf-8"))
    replaced = set()
    new_cells = []
    for cell in nb["cells"]:
        text = cell_text(cell)
        matched = None
        for name in WRITEFILES:
            if text.startswith(f"%%writefile {name}"):
                matched = name
                break
        if matched:
            body = WRITEFILES[matched].read_text(encoding="utf-8")
            new_cells.append(make_writefile_cell(matched, body))
            replaced.add(matched)
        else:
            new_cells.append(cell)
    missing = set(WRITEFILES) - replaced
    if missing:
        raise SystemExit(f"S2 notebook missing writefile cells: {sorted(missing)}")
    nb["cells"] = new_cells

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "arc-agi2-lb33-89-minimal-perfpatch.ipynb"
    notebook_text = json.dumps(nb, indent=1, ensure_ascii=False) + "\n"
    notebook_path.write_text(notebook_text, encoding="utf-8")

    dataset_sources = []
    if args.adapter_dataset:
        dataset_sources.append(args.adapter_dataset)
    metadata = {
        "id": args.slug,
        "title": args.title,
        "code_file": notebook_path.name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": False,
        "keywords": ["gpu"],
        "dataset_sources": dataset_sources,
        "kernel_sources": ["sorokin/pip-install-unsloth-flash-patch"],
        "competition_sources": ["arc-prize-2026-arc-agi-2"],
        "model_sources": ["sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1"],
        "docker_image": "gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868",
        "machine_shape": "NvidiaL4",
    }
    meta_path = out / "kernel-metadata.json"
    meta_text = json.dumps(metadata, indent=2) + "\n"
    meta_path.write_text(meta_text, encoding="utf-8")
    report = {
        "notebook_sha256": sha256_file(notebook_path),
        "metadata_sha256": sha256_file(meta_path),
        "replaced_writefiles": sorted(replaced),
        "base_s2_sha256": sha256_file(S2_NOTEBOOK),
        "internet": False,
        "competition_submit": False,
        "notes": "Kernel push is not a competition submit. Attach adapter dataset only after hashed SFT receipt.",
    }
    (out / "build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_dir": str(out), **report}))


if __name__ == "__main__":
    main()
