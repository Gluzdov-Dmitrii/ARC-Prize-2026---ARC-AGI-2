#!/usr/bin/env python3
"""Create project venv without mutating system Python or the stdlib baseline."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path("/home/scientists/gluz_d_s/kaggle/projects/arc-prize-2026-arc-agi-2")
ENV = PROJECT / "envs" / "ngpu01" / "py3.11-cu124-unsloth-wip"
GET_PIP = PROJECT / "cache" / "get-pip.py"
BASELINE = PROJECT / "envs" / "ngpu01" / "py3.11-stdlib-v1"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def main() -> None:
    if BASELINE.exists() and ENV.resolve() == BASELINE.resolve():
        raise SystemExit("refusing to mutate stdlib baseline")
    ENV.parent.mkdir(parents=True, exist_ok=True)
    if not ENV.exists():
        run([sys.executable, "-m", "venv", "--without-pip", str(ENV)])
    py = str(ENV / "bin" / "python")
    if not GET_PIP.exists():
        raise SystemExit(f"missing {GET_PIP}")
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(PROJECT / "cache" / "pip")
    env["TMPDIR"] = str(PROJECT / "cache" / "tmp")
    Path(env["PIP_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    run([py, str(GET_PIP), "--cache-dir", env["PIP_CACHE_DIR"]])
    run([py, "-m", "pip", "--version"])
    print("venv", ENV)


if __name__ == "__main__":
    main()
