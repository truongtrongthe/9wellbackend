from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client


def list_active_packages(client: Client) -> list[dict[str, Any]]:
    resp = (
        client.table("membership_packages")
        .select("*")
        .eq("status", "active")
        .order("sort_order", desc=False)
        .order("created_at", desc=True)
        .execute()
    )
    return list(resp.data or [])


def get_current_subscription_for_user(client: Client, user_id: str) -> dict[str, Any] | None:
    # Status is authoritative, but we also treat end date < now as expired.
    resp = (
        client.table("subscriptions")
        .select("*, membership_packages(*)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    row = resp.data[0] if resp.data else None
    if not row:
        return None

    end_raw = row.get("current_period_end")
    try:
        end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00")) if isinstance(end_raw, str) else None
    except Exception:
        end_dt = None

    if end_dt and end_dt < datetime.now(UTC) and row.get("status") in ("trial", "active"):
        row = dict(row)
        row["status"] = "expired"
    return row

