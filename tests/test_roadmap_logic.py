from __future__ import annotations

from app.roadmap.logic import ModuleRow, compute_effective_statuses, validate_progress_patch


def test_effective_statuses_linear_track() -> None:
    m1 = ModuleRow(id="a", sequence_order=1)
    m2 = ModuleRow(id="b", sequence_order=2)
    m3 = ModuleRow(id="c", sequence_order=3)
    stored = {"a": "completed", "b": "in_progress", "c": "locked"}
    eff = compute_effective_statuses([m1, m2, m3], stored)
    assert eff["a"] == "completed"
    assert eff["b"] == "in_progress"
    assert eff["c"] == "locked"


def test_effective_first_incomplete_becomes_in_progress_even_if_stored_locked() -> None:
    m1 = ModuleRow(id="a", sequence_order=1)
    m2 = ModuleRow(id="b", sequence_order=2)
    stored = {"a": "locked", "b": "locked"}
    eff = compute_effective_statuses([m1, m2], stored)
    assert eff["a"] == "in_progress"
    assert eff["b"] == "locked"


def test_validate_complete_requires_prior_done() -> None:
    rows = [ModuleRow(id="a", sequence_order=1), ModuleRow(id="b", sequence_order=2)]
    stored = {"a": "in_progress", "b": "locked"}
    err = validate_progress_patch(
        target_module_id="b",
        new_status="completed",
        modules_sorted=rows,
        stored_by_module_id=stored,
    )
    assert err is not None


def test_validate_complete_ok_when_prior_completed() -> None:
    rows = [ModuleRow(id="a", sequence_order=1), ModuleRow(id="b", sequence_order=2)]
    stored = {"a": "completed", "b": "in_progress"}
    err = validate_progress_patch(
        target_module_id="b",
        new_status="completed",
        modules_sorted=rows,
        stored_by_module_id=stored,
    )
    assert err is None


def test_validate_complete_idempotent() -> None:
    rows = [ModuleRow(id="a", sequence_order=1)]
    stored = {"a": "completed"}
    err = validate_progress_patch(
        target_module_id="a",
        new_status="completed",
        modules_sorted=rows,
        stored_by_module_id=stored,
    )
    assert err is None
