from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from supabase import Client

from app.admin.content.repository import list_blog_posts
from app.content.geo import (
    build_blog_markdown,
    build_llms_full_txt,
    build_llms_txt,
    build_sitemap_xml,
)
from app.db.supabase_client import get_supabase

router = APIRouter(tags=["geo"])

_CACHE = "public, max-age=60, s-maxage=120, stale-while-revalidate=600"


def _site_url() -> str:
    env = os.environ.get("SITE_URL", "").strip()
    if env:
        return env.rstrip("/")
    try:
        from app.config import get_settings

        return str(getattr(get_settings(), "site_url", None) or "https://9well.com").rstrip("/")
    except Exception:
        return "https://9well.com"


def _posts(client: Client) -> list[dict]:
    return list_blog_posts(client, published_only=True)


def _text(body: str, media_type: str) -> PlainTextResponse:
    return PlainTextResponse(
        body,
        media_type=media_type,
        headers={"Cache-Control": _CACHE},
    )


@router.get("/llms.txt")
def geo_llms_txt(client: Client = Depends(get_supabase)) -> PlainTextResponse:
    return _text(build_llms_txt(_site_url(), _posts(client)), "text/plain; charset=utf-8")


@router.get("/llms-full.txt")
def geo_llms_full(client: Client = Depends(get_supabase)) -> PlainTextResponse:
    return _text(build_llms_full_txt(_site_url(), _posts(client)), "text/plain; charset=utf-8")


@router.get("/sitemap.xml")
def geo_sitemap(client: Client = Depends(get_supabase)) -> Response:
    xml = build_sitemap_xml(_site_url(), _posts(client))
    return Response(
        content=xml,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": _CACHE},
    )


@router.get("/blog/{slug}.md")
def geo_blog_markdown(slug: str, client: Client = Depends(get_supabase)) -> PlainTextResponse:
    row = next((p for p in _posts(client) if p.get("slug") == slug), None)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return _text(build_blog_markdown(row, _site_url()), "text/markdown; charset=utf-8")
