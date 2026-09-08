#!/usr/bin/env python3
"""Validate a submission.json against challenges: dynamic IDs, 2 attempts, colors 0-9."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from schema_utils import validate_submission_schema  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--challenges", required=True, type=Path)
    parser.add_argument("--submission", required=True, type=Path)
    args = parser.parse_args()
    challenges = json.loads(args.challenges.read_text(encoding="utf-8"))
    submission = json.loads(args.submission.read_text(encoding="utf-8"))
    result = validate_submission_schema(challenges, submission)
    result["n_tasks"] = len(challenges)
    result["n_submission_keys"] = len(submission)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
