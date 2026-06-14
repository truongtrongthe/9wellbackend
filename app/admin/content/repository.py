from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_weeks(client: Client) -> list[dict[str, Any]]:
    res = client.table("course_weeks").select("*").order("week_number").execute()
    return list(res.data or [])


def upsert_week(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    row = {**row, "updated_at": _now_iso()}
    res = client.table("course_weeks").upsert(row, on_conflict="week_number").execute()
    return res.data[0]


def list_lessons(client: Client, published_only: bool = False) -> list[dict[str, Any]]:
    q = client.table("cms_lessons").select("*").order("week_number").order("sort_order")
    if published_only:
        q = q.eq("published", True)
    res = q.execute()
    return list(res.data or [])


def get_lesson(client: Client, lesson_id: str) -> dict[str, Any] | None:
    res = client.table("cms_lessons").select("*").eq("id", lesson_id).maybe_single().execute()
    return res.data


def create_lesson(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    res = client.table("cms_lessons").insert(row).execute()
    return res.data[0]


def update_lesson(client: Client, lesson_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return get_lesson(client, lesson_id)
    patch["updated_at"] = _now_iso()
    res = client.table("cms_lessons").update(patch).eq("id", lesson_id).execute()
    return res.data[0] if res.data else None


def delete_lesson(client: Client, lesson_id: str) -> None:
    client.table("cms_lessons").delete().eq("id", lesson_id).execute()


def list_blog_posts(client: Client, published_only: bool = False) -> list[dict[str, Any]]:
    q = client.table("blog_posts").select("*").order("sort_order")
    if published_only:
        q = q.eq("published", True)
    res = q.execute()
    return list(res.data or [])


def get_blog_post(client: Client, post_id: str) -> dict[str, Any] | None:
    res = client.table("blog_posts").select("*").eq("id", post_id).maybe_single().execute()
    return res.data


def create_blog_post(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    res = client.table("blog_posts").insert(row).execute()
    return res.data[0]


def update_blog_post(client: Client, post_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return get_blog_post(client, post_id)
    patch["updated_at"] = _now_iso()
    res = client.table("blog_posts").update(patch).eq("id", post_id).execute()
    return res.data[0] if res.data else None


def delete_blog_post(client: Client, post_id: str) -> None:
    client.table("blog_posts").delete().eq("id", post_id).execute()


def list_pricing_plans(client: Client) -> list[dict[str, Any]]:
    res = client.table("pricing_plans").select("*").order("sort_order").execute()
    return list(res.data or [])


def upsert_pricing_plan(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    row = {**row, "updated_at": _now_iso()}
    res = client.table("pricing_plans").upsert(row, on_conflict="code").execute()
    return res.data[0]


def list_faqs(client: Client) -> list[dict[str, Any]]:
    res = client.table("cms_faqs").select("*").order("sort_order").execute()
    return list(res.data or [])


def create_faq(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    res = client.table("cms_faqs").insert(row).execute()
    return res.data[0]


def update_faq(client: Client, faq_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return None
    patch["updated_at"] = _now_iso()
    res = client.table("cms_faqs").update(patch).eq("id", faq_id).execute()
    return res.data[0] if res.data else None


def delete_faq(client: Client, faq_id: str) -> None:
    client.table("cms_faqs").delete().eq("id", faq_id).execute()


def list_timeline(client: Client) -> list[dict[str, Any]]:
    res = client.table("cms_timeline_blocks").select("*").order("sort_order").execute()
    return list(res.data or [])


def create_timeline(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    res = client.table("cms_timeline_blocks").insert(row).execute()
    return res.data[0]


def update_timeline(client: Client, block_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        return None
    patch["updated_at"] = _now_iso()
    res = client.table("cms_timeline_blocks").update(patch).eq("id", block_id).execute()
    return res.data[0] if res.data else None


def delete_timeline(client: Client, block_id: str) -> None:
    client.table("cms_timeline_blocks").delete().eq("id", block_id).execute()


def get_settings(client: Client) -> dict[str, Any]:
    res = client.table("site_settings").select("*").execute()
    out: dict[str, Any] = {
        "zalo_link": "https://zalo.me/0900000000",
        "messenger_link": "https://m.me/9wellvn",
        "cache_version": datetime.now(timezone.utc).strftime("%Y%m%d"),
    }
    for row in res.data or []:
        val = row.get("value") or {}
        if isinstance(val, dict):
            out.update(val)
    return out


def upsert_settings(client: Client, values: dict[str, Any]) -> dict[str, Any]:
    for key in ("site", "links", "cache"):
        payload = {"key": "site", "value": values, "updated_at": _now_iso()}
        client.table("site_settings").upsert(payload, on_conflict="key").execute()
        break
    return get_settings(client)


def export_all_content(client: Client) -> dict[str, Any]:
    return {
        "weeks": list_weeks(client),
        "lessons": list_lessons(client, published_only=True),
        "blog_posts": list_blog_posts(client, published_only=True),
        "pricing_plans": [p for p in list_pricing_plans(client) if p.get("published", True)],
        "faqs": [f for f in list_faqs(client) if f.get("published", True)],
        "timeline_blocks": [t for t in list_timeline(client) if t.get("published", True)],
        "settings": get_settings(client),
    }


def create_publish_log(client: Client, user_id: str | None, status: str, message: str | None) -> dict[str, Any]:
    res = (
        client.table("publish_logs")
        .insert({"triggered_by": user_id, "status": status, "message": message})
        .execute()
    )
    return res.data[0]
