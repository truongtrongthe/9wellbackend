from app.portal.logic import lesson_week_from_id, plan_unlocks_week, user_can_access_lesson


def test_plan_unlocks_week():
    assert plan_unlocks_week("none", 1)
    assert not plan_unlocks_week("none", 2)
    assert plan_unlocks_week("start", 4)
    assert not plan_unlocks_week("start", 5)
    assert plan_unlocks_week("core", 8)
    assert plan_unlocks_week("deep", 8)


def test_lesson_week_from_id():
    assert lesson_week_from_id("w2l1") == 2
    assert lesson_week_from_id("w8l3") == 8
    assert lesson_week_from_id("bad") is None


def test_user_can_access_lesson():
    assert user_can_access_lesson("none", "w1l1", free_trial=False)
    assert not user_can_access_lesson("none", "w3l1", free_trial=False)
    assert user_can_access_lesson("none", "w9l1", free_trial=True)
