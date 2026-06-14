from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WeekCreate(BaseModel):
    week_number: int = Field(ge=1, le=52)
    phase: str
    title: str
    goal: str
    sort_order: int = 0


class WeekUpdate(BaseModel):
    phase: str | None = None
    title: str | None = None
    goal: str | None = None
    sort_order: int | None = None


class WeekResponse(BaseModel):
    id: str
    week_number: int
    phase: str
    title: str
    goal: str
    sort_order: int
    created_at: str
    updated_at: str | None = None


class LessonCreate(BaseModel):
    id: str
    week_number: int
    title: str
    lesson_type: str = Field(pattern="^(video|baitap|checkin|doc)$")
    duration: str = ""
    body_html: str = ""
    video_youtube: str | None = None
    video_url: str | None = None
    video_poster: str | None = None
    free_trial: bool = False
    published: bool = True
    compliance_approved: bool = False
    sort_order: int = 0


class LessonUpdate(BaseModel):
    week_number: int | None = None
    title: str | None = None
    lesson_type: str | None = Field(default=None, pattern="^(video|baitap|checkin|doc)$")
    duration: str | None = None
    body_html: str | None = None
    video_youtube: str | None = None
    video_url: str | None = None
    video_poster: str | None = None
    free_trial: bool | None = None
    published: bool | None = None
    compliance_approved: bool | None = None
    sort_order: int | None = None


class LessonResponse(BaseModel):
    id: str
    week_number: int
    title: str
    lesson_type: str
    duration: str
    body_html: str
    video_youtube: str | None = None
    video_url: str | None = None
    video_poster: str | None = None
    free_trial: bool
    published: bool
    compliance_approved: bool
    sort_order: int
    created_at: str
    updated_at: str | None = None


class BlogPostCreate(BaseModel):
    slug: str
    title: str
    category: str = ""
    emoji: str = ""
    excerpt: str = ""
    read_time: str = ""
    author: str = ""
    body_html: str = ""
    seo_description: str = ""
    og_title: str | None = None
    published: bool = True
    published_at: datetime | None = None
    sort_order: int = 0


class BlogPostUpdate(BaseModel):
    slug: str | None = None
    title: str | None = None
    category: str | None = None
    emoji: str | None = None
    excerpt: str | None = None
    read_time: str | None = None
    author: str | None = None
    body_html: str | None = None
    seo_description: str | None = None
    og_title: str | None = None
    published: bool | None = None
    published_at: datetime | None = None
    sort_order: int | None = None


class BlogPostResponse(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    emoji: str
    excerpt: str
    read_time: str
    author: str
    body_html: str
    seo_description: str
    og_title: str | None = None
    published: bool
    published_at: str | None = None
    sort_order: int
    created_at: str
    updated_at: str | None = None


class PricingPlanCreate(BaseModel):
    code: str
    name: str
    price_vnd: int
    price_label: str = "/ một lần"
    role_description: str = ""
    features: list[str] = Field(default_factory=list)
    featured: bool = False
    tag: str | None = None
    cta_text: str = "Tư vấn qua Zalo"
    sort_order: int = 0
    published: bool = True


class PricingPlanUpdate(BaseModel):
    name: str | None = None
    price_vnd: int | None = None
    price_label: str | None = None
    role_description: str | None = None
    features: list[str] | None = None
    featured: bool | None = None
    tag: str | None = None
    cta_text: str | None = None
    sort_order: int | None = None
    published: bool | None = None


class PricingPlanResponse(BaseModel):
    id: str
    code: str
    name: str
    price_vnd: int
    price_label: str
    role_description: str
    features: list[str]
    featured: bool
    tag: str | None = None
    cta_text: str
    sort_order: int
    published: bool
    created_at: str
    updated_at: str | None = None


class FaqCreate(BaseModel):
    question: str
    answer: str
    sort_order: int = 0
    published: bool = True


class FaqUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    sort_order: int | None = None
    published: bool | None = None


class FaqResponse(BaseModel):
    id: str
    question: str
    answer: str
    sort_order: int
    published: bool
    created_at: str
    updated_at: str | None = None


class TimelineBlockCreate(BaseModel):
    week_range: str
    title: str
    description: str
    sort_order: int = 0
    published: bool = True


class TimelineBlockUpdate(BaseModel):
    week_range: str | None = None
    title: str | None = None
    description: str | None = None
    sort_order: int | None = None
    published: bool | None = None


class TimelineBlockResponse(BaseModel):
    id: str
    week_range: str
    title: str
    description: str
    sort_order: int
    published: bool
    created_at: str
    updated_at: str | None = None


class SiteSettingsUpdate(BaseModel):
    zalo_link: str | None = None
    messenger_link: str | None = None
    cache_version: str | None = None


class SiteSettingsResponse(BaseModel):
    zalo_link: str
    messenger_link: str
    cache_version: str


class PublishResponse(BaseModel):
    status: str
    message: str
    log_id: str | None = None


class ContentExportResponse(BaseModel):
    weeks: list[dict[str, Any]]
    lessons: list[dict[str, Any]]
    blog_posts: list[dict[str, Any]]
    pricing_plans: list[dict[str, Any]]
    faqs: list[dict[str, Any]]
    timeline_blocks: list[dict[str, Any]]
    settings: dict[str, Any]
