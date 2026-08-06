from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client


def get_package_by_code(client: Client, code: str) -> dict[str, Any] | None:
    resp = client.table("membership_packages").select("*").eq("code", code).limit(1).execute()
    return resp.data[0] if resp.data else None


def create_order(
    client: Client,
    *,
    user_id: str,
    package_id: str,
    amount_vnd: int,
    idempotency_key: str | None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "user_id": user_id,
        "package_id": package_id,
        "amount_vnd": amount_vnd,
        "currency": "VND",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    resp = client.table("orders").insert(payload).execute()
    if not resp.data:
        raise RuntimeError("Failed to create order")
    return resp.data[0]


def get_order_by_idempotency_key(client: Client, idempotency_key: str) -> dict[str, Any] | None:
    resp = client.table("orders").select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
    return resp.data[0] if resp.data else None


def create_payment(
    client: Client,
    *,
    order_id: str,
    provider: str,
    status: str,
    pay_url: str | None,
    deeplink: str | None,
    qr_code_url: str | None,
    provider_payment_id: str | None,
    raw_create_response: dict[str, Any] | None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "order_id": order_id,
        "provider": provider,
        "status": status,
        "pay_url": pay_url,
        "deeplink": deeplink,
        "qr_code_url": qr_code_url,
        "provider_payment_id": provider_payment_id,
        "raw_create_response": raw_create_response,
        "created_at": now,
        "updated_at": now,
    }
    resp = client.table("payments").insert(payload).execute()
    if not resp.data:
        raise RuntimeError("Failed to create payment")
    return resp.data[0]


def get_latest_order_for_user(client: Client, user_id: str) -> dict[str, Any] | None:
    resp = (
        client.table("orders")
        .select("*, membership_packages(code, name)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def get_pending_order_for_user_package(
    client: Client, user_id: str, package_id: str
) -> dict[str, Any] | None:
    resp = (
        client.table("orders")
        .select("*")
        .eq("user_id", user_id)
        .eq("package_id", package_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def mark_order_paid(client: Client, order_id: str) -> dict[str, Any] | None:
    now = datetime.now(UTC).isoformat()
    resp = (
        client.table("orders")
        .update({"status": "paid", "updated_at": now})
        .eq("id", order_id)
        .execute()
    )
    if resp.data:
        client.table("payments").update(
            {"status": "succeeded", "updated_at": now}
        ).eq("order_id", order_id).eq("status", "processing").execute()
        return resp.data[0]
    return None


def mark_latest_pending_order_paid(client: Client, user_id: str) -> dict[str, Any] | None:
    resp = (
        client.table("orders")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return mark_order_paid(client, str(resp.data[0]["id"]))


def list_latest_orders_for_users(
    client: Client, user_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not user_ids:
        return {}
    resp = (
        client.table("orders")
        .select("*, membership_packages(code, name)")
        .in_("user_id", user_ids)
        .order("created_at", desc=True)
        .execute()
    )
    out: dict[str, dict[str, Any]] = {}
    for row in resp.data or []:
        uid = str(row["user_id"])
        if uid not in out:
            out[uid] = row
    return out


def list_subscriptions_for_users(
    client: Client, user_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not user_ids:
        return {}
    resp = (
        client.table("subscriptions")
        .select("*, membership_packages(code, name)")
        .in_("user_id", user_ids)
        .order("created_at", desc=True)
        .execute()
    )
    out: dict[str, dict[str, Any]] = {}
    for row in resp.data or []:
        uid = str(row["user_id"])
        if uid not in out:
            out[uid] = row
    return out


