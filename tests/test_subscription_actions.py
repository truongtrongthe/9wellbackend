from __future__ import annotations

import pytest

from app.membership.subscription_actions import activate_or_extend_subscription


def test_activate_rejects_non_positive_duration() -> None:
    class Dummy:
        pass

    with pytest.raises(ValueError, match="duration_days"):
        activate_or_extend_subscription(Dummy(), user_id="u", package_id="p", duration_days=0)
