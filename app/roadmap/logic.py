from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModuleStatus = Literal["locked", "in_progress", "completed"]


@dataclass(frozen=True)
class ModuleRow:
    id: str
    sequence_order: int


def compute_effective_statuses(
    modules_sorted: list[ModuleRow],
    stored_by_module_id: dict[str, ModuleStatus],
) -> dict[str, ModuleStatus]:
    """
    Linear track: first module with all predecessors completed and not itself
    completed displays as in_progress; later incomplete modules as locked.
    """
    effective: dict[str, ModuleStatus] = {}
    assigned_in_progress = False
    for i, m in enumerate(modules_sorted):
        prev_ok = i == 0 or all(
            effective[modules_sorted[j].id] == "completed" for j in range(i)
        )
        st = stored_by_module_id.get(m.id, "locked")
        if not prev_ok:
            effective[m.id] = "locked"
        elif st == "completed":
            effective[m.id] = "completed"
        elif not assigned_in_progress:
            effective[m.id] = "in_progress"
            assigned_in_progress = True
        else:
            effective[m.id] = "locked"
    return effective


def validate_progress_patch(
    *,
    target_module_id: str,
    new_status: ModuleStatus,
    modules_sorted: list[ModuleRow],
    stored_by_module_id: dict[str, ModuleStatus],
) -> str | None:
    """Return error message if invalid; None if OK."""
    by_id = {m.id: m for m in modules_sorted}
    if target_module_id not in by_id:
        return "Unknown module"
    target = by_id[target_module_id]
    lower = [m for m in modules_sorted if m.sequence_order < target.sequence_order]
    lowers_done = all(stored_by_module_id.get(m.id) == "completed" for m in lower)
    current = stored_by_module_id.get(target_module_id, "locked")

    if new_status == "completed":
        if current == "completed":
            return None
        if not lowers_done:
            return "Complete prior modules first"
        if current not in ("in_progress", "completed"):
            return "Module must be in progress before completion"
        return None

    if new_status == "in_progress":
        if current == "in_progress":
            return None
        if not lowers_done:
            return "Prior modules must be completed first"
        if current == "completed":
            return "Cannot move a completed module back to in progress"
        return None

    return "Invalid status"
