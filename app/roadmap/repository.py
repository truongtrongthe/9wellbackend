from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from supabase import Client

DEFAULT_GUIDANCE_VI = (
    "Tuần này, ưu tiên của bạn là củng cố kỹ năng lắng nghe chủ động "
    "trước khi chuyển sang các kỹ thuật chạm."
)


def list_active_modules(client: Client) -> list[dict[str, Any]]:
    resp = (
        client.table("learning_modules")
        .select("*")
        .eq("status", "active")
        .order("sequence_order", desc=False)
        .execute()
    )
    return list(resp.data or [])


def list_progress_for_user(client: Client, user_id: str) -> list[dict[str, Any]]:
    resp = client.table("user_module_progress").select("*").eq("user_id", user_id).execute()
    return list(resp.data or [])


def bootstrap_user_progress(
    client: Client,
    user_id: str,
    modules_ordered: list[dict[str, Any]],
) -> None:
    """Insert missing progress rows; first unlockable gap becomes in_progress, else locked."""
    if not modules_ordered:
        return
    existing = list_progress_for_user(client, user_id)
    stored_by_mid: dict[str, str] = {str(r["module_id"]): str(r["status"]) for r in existing}
    now = datetime.now(UTC).isoformat()
    to_insert: list[dict[str, Any]] = []
    for i, m in enumerate(modules_ordered):
        mid = str(m["id"])
        if mid in stored_by_mid:
            continue
        prior_ok = all(
            stored_by_mid.get(str(modules_ordered[j]["id"])) == "completed"
            for j in range(i)
        )
        status: Literal["locked", "in_progress"] = "in_progress" if prior_ok else "locked"
        to_insert.append(
            {
                "user_id": user_id,
                "module_id": mid,
                "status": status,
                "updated_at": now,
            }
        )
        stored_by_mid[mid] = status
    if to_insert:
        client.table("user_module_progress").insert(to_insert).execute()


def ensure_default_ai_guidance(client: Client, user_id: str) -> None:
    resp = (
        client.table("user_ai_guidance")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if resp.data:
        return
    client.table("user_ai_guidance").insert(
        {
            "user_id": user_id,
            "message": DEFAULT_GUIDANCE_VI,
            "source": "system",
        }
    ).execute()


def update_progress_status(client: Client, user_id: str, module_id: str, status: str) -> None:
    now = datetime.now(UTC).isoformat()
    client.table("user_module_progress").update({"status": status, "updated_at": now}).eq(
        "user_id", user_id
    ).eq("module_id", module_id).execute()


def latest_ai_guidance(client: Client, user_id: str) -> dict[str, Any] | None:
    resp = (
        client.table("user_ai_guidance")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def list_notes(client: Client, user_id: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
    resp = (
        client.table("user_learning_notes")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return list(resp.data or [])


def create_note(client: Client, user_id: str, content: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    resp = (
        client.table("user_learning_notes")
        .insert({"user_id": user_id, "content": content, "created_at": now, "updated_at": now})
        .execute()
    )
    if not resp.data:
        raise RuntimeError("Failed to create note")
    return resp.data[0]
