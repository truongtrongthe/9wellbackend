from __future__ import annotations

PLAN_WEEKS: dict[str, int] = {
    "none": 1,
    "start": 4,
    "core": 8,
    "deep": 8,
}


def plan_unlocks_week(plan_code: str, week_number: int) -> bool:
    """Week 1 always unlocked; paid plans unlock up to PLAN_WEEKS[plan]."""
    if week_number <= 1:
        return True
    weeks = PLAN_WEEKS.get(plan_code or "none", 1)
    return week_number <= weeks


def lesson_week_from_id(lesson_id: str) -> int | None:
    """Parse w2l1 → week 2."""
    if not lesson_id or not lesson_id.startswith("w"):
        return None
    try:
        part = lesson_id[1:].split("l", 1)[0]
        return int(part)
    except (ValueError, IndexError):
        return None


def user_can_access_lesson(plan_code: str, lesson_id: str, *, free_trial: bool) -> bool:
    if free_trial:
        return True
    week = lesson_week_from_id(lesson_id)
    if week is None:
        return False
    return plan_unlocks_week(plan_code, week)
