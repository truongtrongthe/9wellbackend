from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import JSONResponse
from supabase import Client

from app.admin.content.repository import (
    get_lesson,
    get_settings,
    list_blog_posts,
    list_faqs,
    list_lessons,
    list_pricing_plans,
    list_timeline,
    list_weeks,
)
from app.content.deps import get_optional_user, user_has_active_subscription
from app.content.models import (
    TYPE_META,
    PublicBlogListItem,
    PublicBlogPost,
    PublicCourseResponse,
    PublicFaq,
    PublicLessonFull,
    PublicLessonLocked,
    PublicLessonMeta,
    PublicPricingPlan,
    PublicPricingResponse,
    PublicSettings,
    PublicTimelineBlock,
    PublicWeek,
    RevalidateRequest,
    RevalidateResponse,
)
from app.content.revalidate import trigger_revalidate
from app.db.supabase_client import get_supabase

router = APIRouter()


def _public_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=300"


def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


def _published_lessons(client: Client) -> list[dict[str, Any]]:
    return [
        l
        for l in list_lessons(client, published_only=True)
        if l.get("compliance_approved", False)
    ]


def _get_blog_by_slug(client: Client, slug: str) -> dict[str, Any] | None:
    rows = [p for p in list_blog_posts(client, published_only=True) if p.get("slug") == slug]
    return rows[0] if rows else None


@router.get("/course", response_model=PublicCourseResponse)
def public_course(
    response: Response,
    client: Client = Depends(get_supabase),
) -> PublicCourseResponse:
    _public_cache(response)
    weeks = list_weeks(client)
    lessons = _published_lessons(client)
    by_week: dict[int, list[dict[str, Any]]] = {}
    for lesson in lessons:
        by_week.setdefault(lesson["week_number"], []).append(lesson)

    out_weeks: list[PublicWeek] = []
    for w in weeks:
        week_lessons = sorted(by_week.get(w["week_number"], []), key=lambda x: x.get("sort_order", 0))
        out_weeks.append(
            PublicWeek(
                week=w["week_number"],
                phase=w["phase"],
                title=w["title"],
                goal=w["goal"],
                lessons=[
                    PublicLessonMeta(
                        id=l["id"],
                        title=l["title"],
                        type=l["lesson_type"],
                        duration=l.get("duration") or "",
                        free_trial=bool(l.get("free_trial")),
                        locked=not bool(l.get("free_trial")),
                    )
                    for l in week_lessons
                ],
            )
        )
    return PublicCourseResponse(weeks=out_weeks, type_meta=TYPE_META)


@router.get("/lessons/{lesson_id}", response_model=PublicLessonFull | PublicLessonLocked)
def public_lesson(
    lesson_id: str,
    response: Response,
    client: Client = Depends(get_supabase),
    user: dict | None = Depends(get_optional_user),
) -> PublicLessonFull | PublicLessonLocked:
    row = get_lesson(client, lesson_id)
    if not row or not row.get("published") or not row.get("compliance_approved"):
        raise HTTPException(status_code=404, detail="Lesson not found")

    weeks = {w["week_number"]: w for w in list_weeks(client)}
    week = weeks.get(row["week_number"], {})
    free = bool(row.get("free_trial"))
    has_sub = user_has_active_subscription(client, user)

    if not free and not has_sub:
        _private_no_store(response)
        payload = PublicLessonLocked(
            id=row["id"],
            title=row["title"],
            week_number=row["week_number"],
            week_goal=week.get("goal"),
            lesson_type=row["lesson_type"],
            duration=row.get("duration") or "",
        )
        return JSONResponse(
            status_code=403,
            content=payload.model_dump(),
            headers={"Cache-Control": "private, no-store"},
        )

    _public_cache(response)
    return PublicLessonFull(
        id=row["id"],
        week_number=row["week_number"],
        title=row["title"],
        lesson_type=row["lesson_type"],
        duration=row.get("duration") or "",
        body_html=row.get("body_html") or "",
        video_youtube=row.get("video_youtube"),
        video_url=row.get("video_url"),
        video_poster=row.get("video_poster"),
        free_trial=free,
        week_phase=week.get("phase"),
        week_goal=week.get("goal"),
    )


@router.get("/blog", response_model=list[PublicBlogListItem])
def public_blog_list(
    response: Response,
    client: Client = Depends(get_supabase),
) -> list[PublicBlogListItem]:
    _public_cache(response)
    posts = list_blog_posts(client, published_only=True)
    return [
        PublicBlogListItem(
            slug=p["slug"],
            title=p["title"],
            category=p.get("category") or "",
            emoji=p.get("emoji") or "",
            excerpt=p.get("excerpt") or "",
            read_time=p.get("read_time") or "",
            sort_order=int(p.get("sort_order") or 0),
        )
        for p in posts
    ]


@router.get("/blog/{slug}", response_model=PublicBlogPost)
def public_blog_detail(
    slug: str,
    response: Response,
    client: Client = Depends(get_supabase),
) -> PublicBlogPost:
    _public_cache(response)
    row = _get_blog_by_slug(client, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return PublicBlogPost(
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
    )


@router.get("/pricing", response_model=PublicPricingResponse)
def public_pricing(
    response: Response,
    client: Client = Depends(get_supabase),
) -> PublicPricingResponse:
    _public_cache(response)
    settings = get_settings(client)
    plans = [p for p in list_pricing_plans(client) if p.get("published", True)]
    faqs = [f for f in list_faqs(client) if f.get("published", True)]
    timeline = [t for t in list_timeline(client) if t.get("published", True)]
    return PublicPricingResponse(
        plans=[
            PublicPricingPlan(
                code=p["code"],
                name=p["name"],
                price_vnd=p["price_vnd"],
                price_label=p.get("price_label") or "/ một lần",
                role_description=p.get("role_description") or "",
                features=list(p.get("features") or []),
                featured=bool(p.get("featured")),
                tag=p.get("tag"),
                cta_text=p.get("cta_text") or "Tư vấn qua Zalo",
            )
            for p in plans
        ],
        faqs=[PublicFaq(question=f["question"], answer=f["answer"]) for f in faqs],
        timeline=[
            PublicTimelineBlock(
                week_range=t["week_range"],
                title=t["title"],
                description=t["description"],
            )
            for t in timeline
        ],
        settings=PublicSettings(
            zalo_link=settings.get("zalo_link", ""),
            messenger_link=settings.get("messenger_link", ""),
        ),
    )


@router.get("/settings", response_model=PublicSettings)
def public_settings(
    response: Response,
    client: Client = Depends(get_supabase),
) -> PublicSettings:
    _public_cache(response)
    s = get_settings(client)
    return PublicSettings(
        zalo_link=s.get("zalo_link", ""),
        messenger_link=s.get("messenger_link", ""),
    )


@router.post("/revalidate", response_model=RevalidateResponse)
def public_revalidate(
    body: RevalidateRequest,
    x_revalidate_secret: str | None = Header(default=None, alias="X-Revalidate-Secret"),
) -> RevalidateResponse:
    expected = os.environ.get("REVALIDATE_SECRET", "")
    if not expected or x_revalidate_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid revalidate secret")
    result = trigger_revalidate(body.paths)
    return RevalidateResponse(
        ok=bool(result["ok"]),
        revalidated=list(result["revalidated"]),
        message=str(result["message"]),
    )
