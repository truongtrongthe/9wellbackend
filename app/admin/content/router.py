from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.admin.content import models as m
from app.admin.content.repository import (
    create_blog_post,
    create_faq,
    create_lesson,
    create_publish_log,
    create_timeline,
    delete_blog_post,
    delete_faq,
    delete_lesson,
    delete_timeline,
    export_all_content,
    get_blog_post,
    get_lesson,
    get_settings,
    list_blog_posts,
    list_faqs,
    list_lessons,
    list_pricing_plans,
    list_timeline,
    list_weeks,
    update_blog_post,
    update_faq,
    update_lesson,
    update_timeline,
    upsert_pricing_plan,
    upsert_settings,
    upsert_week,
)
from app.admin.content.media import router as media_router
from app.admin.deps import AdminContext, require_admin
from app.content.revalidate import trigger_revalidate
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/content", tags=["admin-content"])
router.include_router(media_router)


def _revalidate_after_content_change(*paths: str) -> None:
    """Fire-and-forget cache purge; failures are logged only."""
    try:
        trigger_revalidate(list(paths))
    except Exception:
        pass


def _lesson_resp(row: dict) -> m.LessonResponse:
    return m.LessonResponse(
        id=row["id"],
        week_number=row["week_number"],
        title=row["title"],
        lesson_type=row["lesson_type"],
        duration=row.get("duration") or "",
        body_html=row.get("body_html") or "",
        video_youtube=row.get("video_youtube"),
        video_url=row.get("video_url"),
        video_poster=row.get("video_poster"),
        free_trial=bool(row.get("free_trial")),
        published=bool(row.get("published", True)),
        compliance_approved=bool(row.get("compliance_approved")),
        sort_order=int(row.get("sort_order") or 0),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


def _blog_resp(row: dict) -> m.BlogPostResponse:
    return m.BlogPostResponse(
        id=str(row["id"]),
        slug=row["slug"],
        title=row["title"],
        category=row.get("category") or "",
        emoji=row.get("emoji") or "",
        excerpt=row.get("excerpt") or "",
        read_time=row.get("read_time") or "",
        author=row.get("author") or "",
        body_html=row.get("body_html") or "",
        seo_description=row.get("seo_description") or "",
        og_title=row.get("og_title"),
        published=bool(row.get("published", True)),
        published_at=str(row["published_at"]) if row.get("published_at") else None,
        sort_order=int(row.get("sort_order") or 0),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


@router.get("/export", response_model=m.ContentExportResponse)
def content_export(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.ContentExportResponse:
    data = export_all_content(client)
    return m.ContentExportResponse(**data)


@router.get("/weeks", response_model=list[m.WeekResponse])
def weeks_list(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[m.WeekResponse]:
    rows = list_weeks(client)
    return [
        m.WeekResponse(
            id=str(r["id"]),
            week_number=r["week_number"],
            phase=r["phase"],
            title=r["title"],
            goal=r["goal"],
            sort_order=r.get("sort_order") or 0,
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]) if r.get("updated_at") else None,
        )
        for r in rows
    ]


@router.put("/weeks/{week_number}", response_model=m.WeekResponse)
def weeks_upsert(
    week_number: int,
    body: m.WeekUpdate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.WeekResponse:
    existing = next((w for w in list_weeks(client) if w["week_number"] == week_number), None)
    row = {
        "week_number": week_number,
        "phase": body.phase or (existing or {}).get("phase", ""),
        "title": body.title or (existing or {}).get("title", ""),
        "goal": body.goal or (existing or {}).get("goal", ""),
        "sort_order": body.sort_order if body.sort_order is not None else (existing or {}).get("sort_order", week_number),
    }
    if not row["phase"] or not row["title"]:
        raise HTTPException(status_code=400, detail="phase and title required for new week")
    saved = upsert_week(client, row)
    return m.WeekResponse(
        id=str(saved["id"]),
        week_number=saved["week_number"],
        phase=saved["phase"],
        title=saved["title"],
        goal=saved["goal"],
        sort_order=saved.get("sort_order") or 0,
        created_at=str(saved["created_at"]),
        updated_at=str(saved["updated_at"]) if saved.get("updated_at") else None,
    )


@router.get("/lessons", response_model=list[m.LessonResponse])
def lessons_list(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[m.LessonResponse]:
    return [_lesson_resp(r) for r in list_lessons(client)]


@router.post("/lessons", response_model=m.LessonResponse)
def lessons_create(
    body: m.LessonCreate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.LessonResponse:
    if get_lesson(client, body.id):
        raise HTTPException(status_code=409, detail="Lesson id already exists")
    row = create_lesson(client, body.model_dump())
    return _lesson_resp(row)


@router.patch("/lessons/{lesson_id}", response_model=m.LessonResponse)
def lessons_update(
    lesson_id: str,
    body: m.LessonUpdate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.LessonResponse:
    updated = update_lesson(client, lesson_id, body.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _revalidate_after_content_change("/", "/khoa-hoc", f"/bai-hoc/{lesson_id}")
    return _lesson_resp(updated)


@router.delete("/lessons/{lesson_id}")
def lessons_delete(
    lesson_id: str,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> dict[str, str]:
    if not get_lesson(client, lesson_id):
        raise HTTPException(status_code=404, detail="Lesson not found")
    delete_lesson(client, lesson_id)
    return {"message": "Deleted"}


@router.get("/blog", response_model=list[m.BlogPostResponse])
def blog_list(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[m.BlogPostResponse]:
    return [_blog_resp(r) for r in list_blog_posts(client)]


@router.post("/blog", response_model=m.BlogPostResponse)
def blog_create(
    body: m.BlogPostCreate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.BlogPostResponse:
    row = create_blog_post(client, body.model_dump(mode="json"))
    return _blog_resp(row)


@router.patch("/blog/{post_id}", response_model=m.BlogPostResponse)
def blog_update(
    post_id: str,
    body: m.BlogPostUpdate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.BlogPostResponse:
    updated = update_blog_post(client, post_id, body.model_dump(exclude_unset=True, mode="json"))
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    slug = updated.get("slug") or post_id
    _revalidate_after_content_change("/", "/blog", f"/blog/{slug}")
    return _blog_resp(updated)


@router.delete("/blog/{post_id}")
def blog_delete(
    post_id: str,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> dict[str, str]:
    if not get_blog_post(client, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    delete_blog_post(client, post_id)
    return {"message": "Deleted"}


@router.get("/pricing", response_model=list[m.PricingPlanResponse])
def pricing_list(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[m.PricingPlanResponse]:
    rows = list_pricing_plans(client)
    return [
        m.PricingPlanResponse(
            id=str(r["id"]),
            code=r["code"],
            name=r["name"],
            price_vnd=r["price_vnd"],
            price_label=r.get("price_label") or "/ một lần",
            role_description=r.get("role_description") or "",
            features=list(r.get("features") or []),
            featured=bool(r.get("featured")),
            tag=r.get("tag"),
            cta_text=r.get("cta_text") or "Tư vấn qua Zalo",
            sort_order=int(r.get("sort_order") or 0),
            published=bool(r.get("published", True)),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]) if r.get("updated_at") else None,
        )
        for r in rows
    ]


@router.put("/pricing/{code}", response_model=m.PricingPlanResponse)
def pricing_upsert(
    code: str,
    body: m.PricingPlanUpdate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.PricingPlanResponse:
    existing = next((p for p in list_pricing_plans(client) if p["code"] == code), None)
    if not existing and not body.name:
        raise HTTPException(status_code=400, detail="name required for new plan")
    row = {
        "code": code,
        "name": body.name or existing["name"],
        "price_vnd": body.price_vnd if body.price_vnd is not None else existing["price_vnd"],
        "price_label": body.price_label or existing.get("price_label", "/ một lần"),
        "role_description": body.role_description or existing.get("role_description", ""),
        "features": body.features if body.features is not None else existing.get("features", []),
        "featured": body.featured if body.featured is not None else existing.get("featured", False),
        "tag": body.tag if body.tag is not None else existing.get("tag"),
        "cta_text": body.cta_text or existing.get("cta_text", "Tư vấn qua Zalo"),
        "sort_order": body.sort_order if body.sort_order is not None else existing.get("sort_order", 0),
        "published": body.published if body.published is not None else existing.get("published", True),
    }
    saved = upsert_pricing_plan(client, row)
    return m.PricingPlanResponse(
        id=str(saved["id"]),
        code=saved["code"],
        name=saved["name"],
        price_vnd=saved["price_vnd"],
        price_label=saved.get("price_label") or "/ một lần",
        role_description=saved.get("role_description") or "",
        features=list(saved.get("features") or []),
        featured=bool(saved.get("featured")),
        tag=saved.get("tag"),
        cta_text=saved.get("cta_text") or "Tư vấn qua Zalo",
        sort_order=int(saved.get("sort_order") or 0),
        published=bool(saved.get("published", True)),
        created_at=str(saved["created_at"]),
        updated_at=str(saved["updated_at"]) if saved.get("updated_at") else None,
    )


@router.get("/faqs", response_model=list[m.FaqResponse])
def faqs_list(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[m.FaqResponse]:
    return [
        m.FaqResponse(
            id=str(r["id"]),
            question=r["question"],
            answer=r["answer"],
            sort_order=int(r.get("sort_order") or 0),
            published=bool(r.get("published", True)),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]) if r.get("updated_at") else None,
        )
        for r in list_faqs(client)
    ]


@router.post("/faqs", response_model=m.FaqResponse)
def faqs_create(
    body: m.FaqCreate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.FaqResponse:
    row = create_faq(client, body.model_dump())
    return m.FaqResponse(
        id=str(row["id"]),
        question=row["question"],
        answer=row["answer"],
        sort_order=int(row.get("sort_order") or 0),
        published=bool(row.get("published", True)),
        created_at=str(row["created_at"]),
        updated_at=None,
    )


@router.get("/settings", response_model=m.SiteSettingsResponse)
def settings_get(
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.SiteSettingsResponse:
    s = get_settings(client)
    return m.SiteSettingsResponse(
        zalo_link=s.get("zalo_link", ""),
        messenger_link=s.get("messenger_link", ""),
        cache_version=s.get("cache_version", ""),
    )


@router.put("/settings", response_model=m.SiteSettingsResponse)
def settings_put(
    body: m.SiteSettingsUpdate,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.SiteSettingsResponse:
    current = get_settings(client)
    merged = {
        **current,
        **{k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None},
    }
    upsert_settings(client, merged)
    return m.SiteSettingsResponse(
        zalo_link=merged.get("zalo_link", ""),
        messenger_link=merged.get("messenger_link", ""),
        cache_version=merged.get("cache_version", ""),
    )


@router.post("/publish", response_model=m.PublishResponse)
def content_publish(
    admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> m.PublishResponse:
    user_id = admin.actor_user_id
    try:
        blog_slugs = [p["slug"] for p in list_blog_posts(client, published_only=True)]
        paths = ["/", "/blog", "/lieu-trinh", "/khoa-hoc", "/chuyen-gia", "/quiz"]
        paths.extend(f"/blog/{s}" for s in blog_slugs)
        result = trigger_revalidate(paths)
        msg = result["message"] if result["ok"] else f"Cache refresh: {result['message']}"
        log = create_publish_log(client, user_id, "success" if result["ok"] else "failed", msg)
        return m.PublishResponse(
            status="success" if result["ok"] else "failed",
            message=msg,
            log_id=str(log["id"]),
        )
    except Exception as e:
        log = create_publish_log(client, user_id, "failed", str(e))
        return m.PublishResponse(status="failed", message=str(e), log_id=str(log["id"]))
