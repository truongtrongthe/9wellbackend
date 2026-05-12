from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.auth.repository import get_user_by_id
from app.auth.security import verify_token
from app.config import get_settings
from app.db.supabase_client import get_supabase

security_optional = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AdminContext:
    source: str  # "api_key" | "jwt"
    actor_user_id: str | None


def require_admin(
    client: Annotated[Client, Depends(get_supabase)],
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)] = None,
) -> AdminContext:
    """
    Admin via either:
    - `X-Admin-Key` matching `ADMIN_API_KEY` in settings (when set), or
    - Bearer JWT for a user with `users.role = 'admin'`.
    """
    settings = get_settings()
    if settings.admin_api_key and x_admin_key:
        ak = settings.admin_api_key
        if len(x_admin_key) == len(ak) and secrets.compare_digest(x_admin_key, ak):
            return AdminContext(source="api_key", actor_user_id=None)

    if credentials:
        payload = verify_token(credentials.credentials, secret=settings.jwt_access_secret)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        uid = payload.get("user_id")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = get_user_by_id(client, str(uid))
        if user and user.get("role") == "admin":
            return AdminContext(source="jwt", actor_user_id=str(user["id"]))

    raise HTTPException(
        status_code=403,
        detail="Admin authentication required (X-Admin-Key or Bearer token for role=admin)",
    )
