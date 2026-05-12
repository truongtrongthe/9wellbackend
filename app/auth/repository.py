from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from supabase import Client


def list_users(
    client: Client, *, limit: int = 50, offset: int = 0
) -> list[dict[str, Any]]:
    resp = (
        client.table("users")
        .select("id, email, name, role, created_at")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


def get_user_by_email(client: Client, email: str) -> dict[str, Any] | None:
    resp = client.table("users").select("*").eq("email", email).limit(1).execute()
    return resp.data[0] if resp.data else None


def get_user_by_id(client: Client, user_id: str) -> dict[str, Any] | None:
    resp = client.table("users").select("*").eq("id", user_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def create_user_row(
    client: Client,
    *,
    email: str,
    name: str,
    password_hash: str,
    phone: str | None,
    provider: str = "email",
    email_verified: bool = False,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "email": email,
        "name": name,
        "phone": phone,
        "password_hash": password_hash,
        "provider": provider,
        "email_verified": email_verified,
        "created_at": now,
        "updated_at": now,
    }
    resp = client.table("users").insert(payload).execute()
    if not resp.data:
        raise RuntimeError("Failed to create user")
    return resp.data[0]


def store_refresh_token(client: Client, user_id: str, token: str, expires_at_iso: str) -> bool:
    token_id = f"rt_{secrets.token_urlsafe(16)}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    token_data = {
        "id": token_id,
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at_iso,
        "created_at": datetime.now(UTC).isoformat(),
    }
    resp = client.table("refresh_tokens").insert(token_data).execute()
    return bool(resp.data)


def refresh_token_row_exists(client: Client, user_id: str, refresh_token: str) -> bool:
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    resp = (
        client.table("refresh_tokens")
        .select("id")
        .eq("user_id", user_id)
        .eq("token_hash", token_hash)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def invalidate_refresh_token(client: Client, refresh_token: str) -> None:
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    client.table("refresh_tokens").delete().eq("token_hash", token_hash).execute()


def invalidate_user_refresh_tokens(client: Client, user_id: str) -> None:
    client.table("refresh_tokens").delete().eq("user_id", user_id).execute()

