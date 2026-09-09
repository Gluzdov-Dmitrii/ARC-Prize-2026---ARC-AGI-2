#!/usr/bin/env python3
"""Assemble a Kaggle notebook from portable sources + the S2 4xL4 starter."""
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

MARKDOWN = """# ARC-AGI-2 public-train LoRA

Internet off, 4×L4. This notebook is written to be publishable: short original notes, no copied commentary.

**Method**
- Base model: `sorokin/qwen3_4b_grids15_sft139` (Qwen3-4B, already trained on ARC-style grids).
- Extra LoRA trained only on official **public-train** tasks. Evaluation and hidden solutions are not used.
- At test time the same per-task LoRA update and grid decoder still run.

**Outputs**
- `submission.json` with two attempts per test grid.

**Attached adapter**
- Dataset `arc2-m2-sft-adapter-v1` (`adapter_ttt.safetensors` preferred). Hashes are in that dataset README.
"""


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


def make_source(text: str) -> list[str]:
    if not text.endswith("\n"):
        text += "\n"
    return [text]


def make_markdown_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": make_source(text)}


def make_code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": make_source(text),
    }


def make_writefile_cell(filename: str, body: str) -> dict:
    source = f"%%writefile {filename}\n{body}"
    return make_code_cell(source)


def rewrite_short_cell(text: str, adapter_dataset: str) -> str | None:
    stripped = text.strip()
    if stripped.startswith("#") and "global_end_time" in stripped:
        return (
            "# 12h runtime minus 10 minutes to write submission.json.\n"
            "import time\n"
            "global_end_time = time.time() + 12 * 3600 - 600"
        )
    if "pip uninstall -y tensorflow" in stripped:
        return (
            "# TensorFlow collides with this Unsloth stack on Kaggle.\n"
            "!pip uninstall -y tensorflow"
        )
    if stripped.startswith("!PYTHONHASHSEED"):
        adapter_slug = adapter_dataset.split("/")[-1] if adapter_dataset else "arc2-m2-sft-adapter-v1"
        return (
            "!PYTHONHASHSEED=260618 ARC_AUG_SEED_OFFSET=260618 "
            "UNSLOTH_DISABLE_STATISTICS=1 TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas "
            f"OMP_NUM_THREADS=12 ARC2_ADAPTER_PATH=/kaggle/input/{adapter_slug} "
            "python starter.py --end-time {global_end_time}"
        )
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", default="ARC-AGI-2 public-train LoRA")
    parser.add_argument("--slug", default="dmitriigluzdov/arc2-m2-sft-adapter")
    parser.add_argument("--adapter-dataset", default="dmitriigluzdov/arc2-m2-sft-adapter-v1")
    parser.add_argument("--private", action="store_true", default=True)
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()

    nb = json.loads(S2_NOTEBOOK.read_text(encoding="utf-8"))
    replaced = set()
    markdown_done = False
    new_cells = []
    for cell in nb["cells"]:
        text = cell_text(cell)
        if cell.get("cell_type") == "markdown":
            if markdown_done:
                continue
            new_cells.append(make_markdown_cell(MARKDOWN.strip() + "\n"))
            markdown_done = True
            continue
        matched = None
        for name in WRITEFILES:
            if text.startswith(f"%%writefile {name}"):
                matched = name
                break
        if matched:
            body = WRITEFILES[matched].read_text(encoding="utf-8")
            new_cells.append(make_writefile_cell(matched, body))
            replaced.add(matched)
            continue
        rewritten = rewrite_short_cell(text, args.adapter_dataset)
        if rewritten is not None:
            new_cells.append(make_code_cell(rewritten))
            continue
        new_cells.append(cell)
    if not markdown_done:
        new_cells.insert(0, make_markdown_cell(MARKDOWN.strip() + "\n"))
    missing = set(WRITEFILES) - replaced
    if missing:
        raise SystemExit(f"S2 notebook missing writefile cells: {sorted(missing)}")
    nb["cells"] = new_cells
    nb.pop("metadata", None)
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "arc2-sft-adapter.ipynb"
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
        "is_private": not args.public,
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
        "notes": "Kernel push is not a competition submit. Markdown is original; adapter dataset is attached after the hashed SFT receipt.",
    }
    (out / "build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_dir": str(out), **report}))


if __name__ == "__main__":
    main()
