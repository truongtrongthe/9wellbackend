from __future__ import annotations

from pydantic import BaseModel


TYPE_META = {
    "video": {"icon": "▶", "label": "Video"},
    "baitap": {"icon": "✦", "label": "Bài tập"},
    "checkin": {"icon": "✓", "label": "Check-in"},
    "doc": {"icon": "📄", "label": "Bài đọc"},
}


class PublicLessonMeta(BaseModel):
    id: str
    title: str
    type: str
    duration: str
    free_trial: bool
    locked: bool


class PublicWeek(BaseModel):
    week: int
    phase: str
    title: str
    goal: str
    lessons: list[PublicLessonMeta]


class PublicCourseResponse(BaseModel):
    weeks: list[PublicWeek]
    type_meta: dict[str, dict[str, str]]


class PublicLessonFull(BaseModel):
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
    week_phase: str | None = None
    week_goal: str | None = None


class PublicLessonLocked(BaseModel):
    locked: bool = True
    id: str
    title: str
    week_number: int
    week_goal: str | None = None
    lesson_type: str
    duration: str


class PublicBlogListItem(BaseModel):
    slug: str
    title: str
    category: str
    emoji: str
    excerpt: str
    read_time: str
    sort_order: int


class PublicBlogPost(BaseModel):
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


class PublicPricingPlan(BaseModel):
    code: str
    name: str
    price_vnd: int
    price_label: str
    role_description: str
    features: list[str]
    featured: bool
    tag: str | None = None
    cta_text: str


class PublicFaq(BaseModel):
    question: str
    answer: str


class PublicTimelineBlock(BaseModel):
    week_range: str
    title: str
    description: str


class PublicSettings(BaseModel):
    zalo_link: str
    messenger_link: str


class PublicPricingResponse(BaseModel):
    plans: list[PublicPricingPlan]
    faqs: list[PublicFaq]
    timeline: list[PublicTimelineBlock]
    settings: PublicSettings


class RevalidateRequest(BaseModel):
    paths: list[str] | None = None


class RevalidateResponse(BaseModel):
    ok: bool
    revalidated: list[str]
    message: str
