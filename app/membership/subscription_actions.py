from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from supabase import Client

SubscriptionStatus = Literal["active", "trial"]


def activate_or_extend_subscription(
    client: Client,
    *,
    user_id: str,
    package_id: str,
    duration_days: int,
    status: SubscriptionStatus = "active",
) -> dict[str, Any]:
    """
    Create or update the user's current trial/active subscription (same rules as paid MoMo success).
    """
    if duration_days <= 0:
        raise ValueError("duration_days must be positive")

    sub_resp = (
        client.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .in_("status", ["trial", "active"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    if sub_resp.data:
        sub = sub_resp.data[0]
        end_raw = sub.get("current_period_end")
        try:
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00")) if isinstance(end_raw, str) else None
        except Exception:
            end_dt = None
        base = end_dt if end_dt and end_dt > now else now
        new_end = base + timedelta(days=duration_days)
        client.table("subscriptions").update(
            {
                "package_id": package_id,
                "status": status,
                "current_period_end": new_end.isoformat(),
                "updated_at": now_iso,
            }
        ).eq("id", sub["id"]).execute()
        out = (
            client.table("subscriptions")
            .select("*")
            .eq("id", sub["id"])
            .limit(1)
            .execute()
        )
        if not out.data:
            raise RuntimeError("Subscription update not found")
        return out.data[0]

    client.table("subscriptions").insert(
        {
            "user_id": user_id,
            "package_id": package_id,
            "status": status,
            "current_period_start": now_iso,
            "current_period_end": (now + timedelta(days=duration_days)).isoformat(),
            "auto_renew": False,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    ).execute()
    out = (
        client.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not out.data:
        raise RuntimeError("Subscription insert not found")
    return out.data[0]
