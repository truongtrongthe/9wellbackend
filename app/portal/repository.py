from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from supabase import Client

DEFAULT_PORTAL_CONFIG: dict[str, Any] = {
    "zaloLink": "",
    "trainerUrl": "/trainer",
    "gameUrl": "/game",
    "hubUrl": "/blog",
    "courseUrl": "/learn",
    "accessCodes": ["9WELLHIM"],
    "introYtid": "aqz-KE-bpKQ",
    "demoVideoYtid": "aqz-KE-bpKQ",
    "sepay": {"bank": "MB Bank", "account": "", "holder": "", "qrImg": ""},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_client_code() -> str:
    return f"9W{secrets.token_hex(3).upper()}"


def get_portal_config(client: Client) -> dict[str, Any]:
    res = client.table("site_settings").select("value").eq("key", "portal_config").maybe_single().execute()
    val = (res.data or {}).get("value") if res.data else None
    out = dict(DEFAULT_PORTAL_CONFIG)
    if isinstance(val, dict):
        out.update(val)
        if isinstance(val.get("sepay"), dict):
            out["sepay"] = {**out["sepay"], **val["sepay"]}
    # merge zalo from main site settings
    settings = client.table("site_settings").select("value").eq("key", "site").maybe_single().execute()
    site_val = (settings.data or {}).get("value") if settings.data else {}
    if isinstance(site_val, dict) and site_val.get("zalo_link") and not out.get("zaloLink"):
        out["zaloLink"] = site_val["zalo_link"]
    return out


def upsert_portal_config(client: Client, patch: dict[str, Any]) -> dict[str, Any]:
    current = get_portal_config(client)
    current.update({k: v for k, v in patch.items() if v is not None})
    if patch.get("sepay"):
        current["sepay"] = {**current.get("sepay", {}), **patch["sepay"]}
    client.table("site_settings").upsert(
        {"key": "portal_config", "value": current, "updated_at": _now_iso()},
        on_conflict="key",
    ).execute()
    return get_portal_config(client)


def get_profile(client: Client, user_id: str) -> dict[str, Any] | None:
    res = client.table("portal_profiles").select("*").eq("user_id", user_id).maybe_single().execute()
    return res.data


def create_profile(
    client: Client,
    *,
    user_id: str,
    nickname: str,
    pin_hash: str | None = None,
) -> dict[str, Any]:
    row = {
        "user_id": user_id,
        "nickname": nickname,
        "pin_hash": pin_hash,
        "plan_code": "none",
        "current_week": 1,
        "week_done": {},
        "privacy": {"panicUrl": "https://www.google.com", "disguise": False},
        "client_code": _gen_client_code(),
        "trainer_stats": {},
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    res = client.table("portal_profiles").insert(row).execute()
    return res.data[0]


def update_profile(client: Client, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    patch["updated_at"] = _now_iso()
    res = client.table("portal_profiles").update(patch).eq("user_id", user_id).execute()
    if not res.data:
        raise ValueError("Profile not found")
    return res.data[0]


def list_checkins(client: Client, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    res = (
        client.table("portal_checkins")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(res.data or [])


def create_checkin(client: Client, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = {**row, "user_id": user_id, "created_at": _now_iso()}
    res = client.table("portal_checkins").insert(payload).execute()
    return res.data[0]


def save_quiz_result(client: Client, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = {**row, "user_id": user_id, "created_at": _now_iso()}
    res = client.table("portal_quiz_results").insert(payload).execute()
    return res.data[0]


def latest_quiz(client: Client, user_id: str) -> dict[str, Any] | None:
    res = (
        client.table("portal_quiz_results")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return res.data


def list_all_checkins(client: Client, limit: int = 100) -> list[dict[str, Any]]:
    res = client.table("portal_checkins").select("*").order("created_at", desc=True).limit(limit).execute()
    return list(res.data or [])
