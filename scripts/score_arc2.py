#!/usr/bin/env python3
"""CPU scorer: solutions are read only here, never by the solver."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schema_utils import micro_macro, validate_submission_schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--solutions", required=True)
    parser.add_argument("--candidates", help="inference_outputs directory")
    parser.add_argument("--submission", help="submission.json")
    parser.add_argument(
        "--selector",
        default="score_kgmon",
        choices=["score_kgmon", "score_full_probmul_3", "score_kgmon_diversity_a2"],
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    challenges = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = {"selector": args.selector}
    if args.candidates:
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "src" / "arc2"))
        from arc_decoder import (  # noqa: WPS433
            ArcDecoder,
            score_full_probmul_3,
            score_kgmon,
            score_kgmon_diversity_a2,
        )
        from arc_loader import ArcDataset  # noqa: WPS433

        data = ArcDataset.from_file(args.input)
        data = data.load_replies(args.solutions)
        decoder = ArcDecoder(data.split_multi_replies(), n_guesses=2)
        decoder.load_decoded_results(args.candidates)
        algo = {
            "score_kgmon": score_kgmon,
            "score_full_probmul_3": score_full_probmul_3,
            "score_kgmon_diversity_a2": score_kgmon_diversity_a2,
        }[args.selector]
        selected = decoder.run_selection_algo(algo)
        submission = data.get_submission(selected)
        report["candidate_basekeys"] = sorted(decoder.decoded_results)
        report["n_candidate_basekeys"] = len(decoder.decoded_results)
    elif args.submission:
        submission = json.loads(Path(args.submission).read_text(encoding="utf-8"))
    else:
        raise SystemExit("Need --candidates or --submission")

    schema = validate_submission_schema(challenges, submission)
    solutions = json.loads(Path(args.solutions).read_text(encoding="utf-8"))
    metrics = micro_macro(challenges, solutions, submission)
    n_real = 0
    n_fallback = 0
    for rows in submission.values():
        for item in rows:
            for key in ("attempt_1", "attempt_2"):
                if item.get(key) == [[0]]:
                    n_fallback += 1
                else:
                    n_real += 1
    report.update(schema=schema, metrics=metrics, n_real_attempts=n_real, n_placeholder_attempts=n_fallback)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("selector", "schema", "metrics") if k in report}, indent=2))


if __name__ == "__main__":
    main()
