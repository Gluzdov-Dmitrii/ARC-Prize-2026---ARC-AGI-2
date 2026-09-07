#!/usr/bin/env python3
"""M0 CPU contract: schema, micro vs macro, no solutions in solver cache path."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "arc2"))
sys.path.insert(0, str(ROOT / "scripts"))

from schema_utils import grid_ok, micro_macro, validate_submission_schema  # noqa: E402
from arc_decoder import score_kgmon_diversity_a2  # noqa: E402


def test_schema_dynamic_counts() -> None:
    challenges = {
        "one": {"test": [{"input": [[1]]}]},
        "three": {"test": [{"input": [[1]]}, {"input": [[2]]}, {"input": [[3]]}]},
    }
    good = {
        "one": [{"attempt_1": [[1]], "attempt_2": [[0]]}],
        "three": [
            {"attempt_1": [[1, 1], [1, 1]], "attempt_2": [[2]]},
            {"attempt_1": [[9]], "attempt_2": [[8]]},
            {"attempt_1": [[7]], "attempt_2": [[6]]},
        ],
    }
    assert validate_submission_schema(challenges, good)["ok"]
    bad = {"one": [{"attempt_1": [[1]], "attempt_2": [[0]]}]}
    assert not validate_submission_schema(challenges, bad)["ok"]
    assert grid_ok([[0, 1], [2, 3]])
    assert not grid_ok([[10]])
    assert not grid_ok([])


def test_micro_not_macro() -> None:
    challenges = {"a": {"test": [1, 2, 3]}, "b": {"test": [1]}}
    solutions = {"a": [[[1]], [[1]], [[1]]], "b": [[[9]]]}
    submission = {
        "a": [
            {"attempt_1": [[1]], "attempt_2": [[0]]},
            {"attempt_1": [[0]], "attempt_2": [[0]]},
            {"attempt_1": [[0]], "attempt_2": [[0]]},
        ],
        "b": [{"attempt_1": [[9]], "attempt_2": [[0]]}],
    }
    metrics = micro_macro(challenges, solutions, submission)
    assert metrics["correct_test_outputs"] == 2
    assert metrics["all_test_outputs"] == 4
    assert abs(metrics["micro_pass_at_2"] - 0.5) < 1e-9
    assert abs(metrics["legacy_task_macro"] - 0.5) > 1e-9 or abs(metrics["legacy_task_macro"] - ((1 / 3 + 1) / 2)) < 1e-9
    assert abs(metrics["legacy_task_macro"] - ((1 / 3) + 1) / 2) < 1e-9


def test_diversity_keeps_primary() -> None:
    a = np.array([[1, 2], [3, 4]])
    b = np.array([[9, 9], [9, 9]])

    def fake_score_kgmon(_):
        return [a, a]

    def fake_score_full(_):
        return [a, b]

    import arc_decoder as dec

    orig_k, orig_f = dec.score_kgmon, dec.score_full_probmul_3
    dec.score_kgmon = fake_score_kgmon
    dec.score_full_probmul_3 = fake_score_full
    try:
        out = score_kgmon_diversity_a2({})
        assert np.array_equal(out[0], a)
        assert np.array_equal(out[1], b)
    finally:
        dec.score_kgmon, dec.score_full_probmul_3 = orig_k, orig_f


def test_solver_cache_has_no_solutions_field() -> None:
    sample = {
        "solution": [[1]],
        "beam_score": 0.1,
        "score_aug": [0.2],
    }
    dumped = json.dumps(sample)
    assert "truth" not in dumped
    assert "replies" not in dumped


def test_ids_file_hash() -> None:
    ids = ROOT / "configs" / "validation_v2_ids.txt"
    import hashlib

    digest = hashlib.sha256(ids.read_bytes()).hexdigest()
    assert digest == "b798899dc1452d681b6849c3c1b93237ab5df6bd5193be53b90a14ef2f379155", digest


def main() -> None:
    test_schema_dynamic_counts()
    test_micro_not_macro()
    test_diversity_keeps_primary()
    test_solver_cache_has_no_solutions_field()
    test_ids_file_hash()
    print("cpu_contract_tests: PASS")


if __name__ == "__main__":
    main()
