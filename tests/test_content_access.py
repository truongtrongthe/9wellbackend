from app.content.deps import user_can_access_lesson_row


def test_anonymous_only_free_trial():
    lesson_free = {"id": "w1l1", "free_trial": True}
    lesson_paid = {"id": "w2l1", "free_trial": False}

    class _Dummy:
        pass

    # client unused when free_trial / no user
    assert user_can_access_lesson_row(_Dummy(), None, lesson_free) is True
    assert user_can_access_lesson_row(_Dummy(), None, lesson_paid) is False


def test_portal_plan_no_longer_unlocks_content(monkeypatch):
    """Registered but unpaid user must not unlock via portal plan_code."""
    lesson = {"id": "w1l1", "free_trial": False}
    user = {"id": "u1"}

    monkeypatch.setattr(
        "app.content.deps.user_has_active_subscription",
        lambda client, u: False,
    )
    class _Dummy:
        pass

    assert user_can_access_lesson_row(_Dummy(), user, lesson) is False
