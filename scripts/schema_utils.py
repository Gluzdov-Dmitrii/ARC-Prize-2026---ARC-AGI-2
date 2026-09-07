"""Submission schema helpers with no ML imports."""
from __future__ import annotations

import numpy as np


def grid_ok(grid) -> bool:
    if not isinstance(grid, list) or not grid:
        return False
    width = None
    for row in grid:
        if not isinstance(row, list) or not row:
            return False
        if width is None:
            width = len(row)
        if len(row) != width:
            return False
        for cell in row:
            if not isinstance(cell, int) or cell < 0 or cell > 9:
                return False
    return True


def validate_submission_schema(challenges: dict, submission: dict) -> dict:
    errors = []
    for task_id, task in challenges.items():
        tests = task.get("test") or []
        if task_id not in submission:
            errors.append(f"missing task {task_id}")
            continue
        rows = submission[task_id]
        if not isinstance(rows, list) or len(rows) != len(tests):
            errors.append(f"{task_id} test count mismatch")
            continue
        for i, item in enumerate(rows):
            for key in ("attempt_1", "attempt_2"):
                if key not in item or not grid_ok(item[key]):
                    errors.append(f"{task_id}[{i}].{key} invalid")
    extra = sorted(set(submission) - set(challenges))
    return {"ok": not errors and not extra, "n_errors": len(errors), "errors": errors[:20], "n_extra": len(extra)}


def micro_macro(challenges: dict, solutions: dict, submission: dict) -> dict:
    correct = 0
    total = 0
    task_scores = []
    gained = []
    for task_id, tests in solutions.items():
        if task_id not in challenges:
            continue
        n = len(tests)
        task_correct = 0
        for i, truth in enumerate(tests):
            total += 1
            attempts = submission.get(task_id, [{}] * n)
            item = attempts[i] if i < len(attempts) else {}
            hit = False
            for key in ("attempt_1", "attempt_2"):
                guess = item.get(key)
                if guess is not None and np.array_equal(np.asarray(guess), np.asarray(truth)):
                    hit = True
                    break
            if hit:
                correct += 1
                task_correct += 1
                gained.append(f"{task_id}_{i}")
        task_scores.append(task_correct / n if n else 0.0)
    return {
        "micro_pass_at_2": (correct / total) if total else 0.0,
        "correct_test_outputs": correct,
        "all_test_outputs": total,
        "legacy_task_macro": float(np.mean(task_scores)) if task_scores else 0.0,
        "n_tasks": len(task_scores),
        "hit_keys": gained,
    }
