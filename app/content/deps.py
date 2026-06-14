from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.auth.repository import get_user_by_id
from app.auth.security import verify_token
from app.config import get_settings
from app.db.supabase_client import get_supabase
from app.membership.repository import get_current_subscription_for_user

optional_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    client: Client = Depends(get_supabase),
) -> dict[str, Any] | None:
    if not credentials:
        return None
    try:
        settings = get_settings()
        payload = verify_token(credentials.credentials, secret=settings.jwt_access_secret)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("user_id")
        if not user_id:
            return None
        return get_user_by_id(client, str(user_id))
    except HTTPException:
        return None


def user_has_active_subscription(client: Client, user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    sub = get_current_subscription_for_user(client, str(user["id"]))
    if not sub:
        return False
    status = str(sub.get("status") or "")
    if status not in ("active", "trial"):
        return False
    end_raw = sub.get("current_period_end")
    if not end_raw:
        return status == "active"
    try:
        end_dt = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
        return end_dt > datetime.now(UTC)
    except Exception:
        return status in ("active", "trial")
