from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.config import get_settings
from app.db.supabase_client import get_supabase

JWT_ALGORITHM = "HS256"
security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(*, user_id: str, token_type: str, ttl_seconds: int, secret: str) -> tuple[str, datetime]:
    expire = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    payload = {"user_id": user_id, "type": token_type, "exp": expire}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM), expire


def create_access_token(*, user_id: str) -> str:
    settings = get_settings()
    token, _ = _create_token(
        user_id=user_id,
        token_type="access",
        ttl_seconds=settings.jwt_access_ttl_seconds,
        secret=settings.jwt_access_secret,
    )
    return token


def create_refresh_token(*, user_id: str) -> tuple[str, datetime]:
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        ttl_seconds=settings.jwt_refresh_ttl_seconds,
        secret=settings.jwt_refresh_secret,
    )


def verify_token(token: str, *, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Expired": "true"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    client: Client = Depends(get_supabase),
) -> dict:
    from app.auth.repository import get_user_by_id

    token = credentials.credentials
    settings = get_settings()
    payload = verify_token(token, secret=settings.jwt_access_secret)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(client, str(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

