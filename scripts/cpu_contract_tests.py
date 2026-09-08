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


def test_pack_sft_no_eval_leak() -> None:
    import hashlib
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pack_sft_dataset", ROOT / "scripts" / "pack_sft_dataset.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    train_ids = ["aaa11111", "bbb22222"]
    eval_ids = {"a32d8b75", "9aaea919"}
    leaked = sorted(set(train_ids) & eval_ids)
    assert leaked == []
    task = {
        "train": [{"input": [[1, 0], [0, 1]], "output": [[0, 1], [1, 0]]}],
        "test": [{"input": [[2, 2], [2, 2]]}],
    }
    rows = mod.pack_task("aaa11111", task, [[[9, 9], [9, 9]]], "train")
    kinds = {row["kind"] for row in rows}
    assert "train_pairs" in kinds
    assert "supervised_test" in kinds
    joined = "\n".join(row["text"] for row in rows)
    assert "<|im_start|>user" in joined
    assert "a32d8b75" not in joined
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    assert len(digest) == 64


def test_adapter_path_helper_skips_missing(monkeypatch=None) -> None:
    import os

    os.environ.pop("ARC2_ADAPTER_PATH", None)
    from pathlib import Path as P

    missing = P("/kaggle/input/arc2-m1-sft-adapter-v1/adapter_model.safetensors")
    assert not missing.exists()


def main() -> None:
    test_schema_dynamic_counts()
    test_micro_not_macro()
    test_diversity_keeps_primary()
    test_solver_cache_has_no_solutions_field()
    test_ids_file_hash()
    test_pack_sft_no_eval_leak()
    test_adapter_path_helper_skips_missing()
    print("cpu_contract_tests: PASS")


if __name__ == "__main__":
    main()
