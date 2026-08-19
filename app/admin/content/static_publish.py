from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from supabase import Client


BUNDLE_KEYS = (
    "learn_curriculum",
    "shop_catalog",
    "hub_videos",
    "hub_categories",
    "trainer",
    "game",
    "portal_app",
    "landing_copy",
    "legal_pages",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_bundle(client: Client, key: str) -> dict[str, Any] | None:
    res = client.table("cms_content_bundles").select("*").eq("key", key).maybe_single().execute()
    return res.data


def list_bundles(client: Client) -> list[dict[str, Any]]:
    res = client.table("cms_content_bundles").select("key, updated_at").order("key").execute()
    return list(res.data or [])


def upsert_bundle(client: Client, key: str, payload: Any) -> dict[str, Any]:
    row = {"key": key, "payload": payload, "updated_at": _now_iso()}
    res = client.table("cms_content_bundles").upsert(row, on_conflict="key").execute()
    return res.data[0]


def get_static_root() -> Path:
    return get_static_roots()[0]


def get_static_roots() -> list[Path]:
    """Primary CMS_STATIC_ROOT + mirrors (sibling dist/v2, CMS_STATIC_MIRROR)."""
    roots: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key in seen:
            return
        seen.add(key)
        p.mkdir(parents=True, exist_ok=True)
        roots.append(p)

    env = os.environ.get("CMS_STATIC_ROOT", "").strip()
    if not env:
        try:
            from app.config import get_settings

            s = get_settings()
            if s.cms_static_root:
                env = s.cms_static_root
        except Exception:
            pass
    if env:
        add(Path(env))
    else:
        here = Path(__file__).resolve()
        backend_root = here.parents[3]
        candidates = [
            backend_root.parent / "9wellcms" / "apps" / "web" / "public" / "v2",
            Path.cwd() / "apps" / "web" / "public" / "v2",
            Path.cwd() / "public" / "v2",
        ]
        for c in candidates:
            if c.exists() or c == candidates[0]:
                add(c)
                break
        if not roots:
            fallback = Path.cwd() / "public" / "v2"
            add(fallback)

    primary = roots[0]
    # Nginx serves dist/ — mirror public/v2 ↔ dist/v2 when sibling exists
    if primary.name == "v2":
        parent = primary.parent
        if parent.name == "public":
            add(parent.parent / "dist" / "v2")
        elif parent.name == "dist":
            add(parent.parent / "public" / "v2")

    mirror = os.environ.get("CMS_STATIC_MIRROR", "").strip()
    if not mirror:
        try:
            from app.config import get_settings

            s = get_settings()
            mirror = getattr(s, "cms_static_mirror", None) or ""
        except Exception:
            mirror = ""
    for part in str(mirror).split(","):
        part = part.strip()
        if part:
            add(Path(part))

    return roots


def sync_hub_articles(client: Client) -> list[str]:
    """Rewrite articles.js on all static roots from published blog_posts."""
    posts = []
    try:
        from app.admin.content.repository import list_blog_posts

        posts = list_blog_posts(client, published_only=True)
    except Exception:
        return []
    cats_row = get_bundle(client, "hub_categories")
    payload = (cats_row or {}).get("payload") or {}
    cats = payload.get("cats") if isinstance(payload, dict) else payload
    if not isinstance(cats, dict):
        cats = {}
    written: list[str] = []
    for root in get_static_roots():
        rel = write_hub_articles(root, posts, cats)
        written.append(f"{root}/{rel}")
    try:
        written.extend(sync_geo_files(client, posts=posts))
    except Exception:
        pass
    return written


def get_web_dist_roots() -> list[Path]:
    """apps/web/dist (+ mirrors) for GEO fallback files served by nginx."""
    roots: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key in seen:
            return
        seen.add(key)
        p.mkdir(parents=True, exist_ok=True)
        roots.append(p)

    env = os.environ.get("CMS_WEB_DIST", "").strip()
    if not env:
        try:
            from app.config import get_settings

            s = get_settings()
            env = getattr(s, "cms_web_dist", None) or ""
        except Exception:
            env = ""
    if env:
        for part in str(env).split(","):
            part = part.strip()
            if part:
                add(Path(part))
    else:
        here = Path(__file__).resolve()
        backend_root = here.parents[3]
        candidates = [
            backend_root.parent / "9wellcms" / "apps" / "web" / "dist",
            Path.cwd().parent / "9wellcms" / "apps" / "web" / "dist",
            Path.cwd() / "apps" / "web" / "dist",
        ]
        for c in candidates:
            if c.exists() or c == candidates[0]:
                add(c)
                break
        if not roots:
            add(candidates[0])
    return roots


def _site_url() -> str:
    env = os.environ.get("SITE_URL", "").strip()
    if env:
        return env.rstrip("/")
    try:
        from app.config import get_settings

        return str(getattr(get_settings(), "site_url", None) or "https://9well.com").rstrip("/")
    except Exception:
        return "https://9well.com"


def sync_geo_files(client: Client, posts: list[dict] | None = None) -> list[str]:
    """Write dynamic GEO snapshots into web dist (fallback when API proxy is down)."""
    from app.content.geo import (
        build_blog_markdown,
        build_llms_full_txt,
        build_llms_txt,
        build_sitemap_xml,
    )

    if posts is None:
        try:
            from app.admin.content.repository import list_blog_posts

            posts = list_blog_posts(client, published_only=True)
        except Exception:
            posts = []
    site = _site_url()
    written: list[str] = []
    for root in get_web_dist_roots():
        blog_dir = root / "blog"
        blog_dir.mkdir(parents=True, exist_ok=True)
        # Remove stale markdown from previous publish
        for old in blog_dir.glob("*.md"):
            try:
                old.unlink()
            except OSError:
                pass
        (root / "llms.txt").write_text(build_llms_txt(site, posts), encoding="utf-8")
        (root / "llms-full.txt").write_text(build_llms_full_txt(site, posts), encoding="utf-8")
        (root / "sitemap.xml").write_text(build_sitemap_xml(site, posts), encoding="utf-8")
        written.extend(
            [
                str(root / "llms.txt"),
                str(root / "llms-full.txt"),
                str(root / "sitemap.xml"),
            ]
        )
        for post in posts:
            slug = post.get("slug") or ""
            if not slug:
                continue
            md_path = blog_dir / f"{slug}.md"
            md_path.write_text(build_blog_markdown(post, site), encoding="utf-8")
            written.append(str(md_path))
    return written


def sync_learn_curriculum(client: Client) -> list[str]:
    """Rewrite curriculum.js on all static roots from learn_curriculum bundle."""
    row = get_bundle(client, "learn_curriculum")
    payload = (row or {}).get("payload") or {}
    if not isinstance(payload, dict):
        return []
    written: list[str] = []
    for root in get_static_roots():
        rel = write_learn(root, payload)
        written.append(f"{root}/{rel}")
    return written


def sync_bundle_static(client: Client, key: str) -> list[str]:
    """Sync one CMS bundle to static v2 files after admin save."""
    if key == "learn_curriculum":
        return sync_learn_curriculum(client)
    if key in ("hub_categories",):
        return sync_hub_articles(client)
    if key == "hub_videos":
        row = get_bundle(client, "hub_videos")
        payload = (row or {}).get("payload") or {}
        written: list[str] = []
        for root in get_static_roots():
            written.append(f"{root}/{write_hub_videos(root, payload)}")
        return written
    if key == "shop_catalog":
        row = get_bundle(client, "shop_catalog")
        payload = (row or {}).get("payload") or {}
        written = []
        for root in get_static_roots():
            written.append(f"{root}/{write_shop(root, payload)}")
        return written
    if key == "portal_app":
        row = get_bundle(client, "portal_app")
        payload = (row or {}).get("payload") or {}
        written = []
        for root in get_static_roots():
            written.append(f"{root}/{write_portal(root, payload)}")
        return written
    if key == "trainer":
        row = get_bundle(client, "trainer")
        payload = (row or {}).get("payload") or {}
        written = []
        for root in get_static_roots():
            written.append(f"{root}/{write_trainer(root, payload)}")
        return written
    if key == "game":
        row = get_bundle(client, "game")
        payload = (row or {}).get("payload") or {}
        written = []
        for root in get_static_roots():
            written.append(f"{root}/{write_game(root, payload)}")
        return written
    return []


def get_seeds_dir() -> Path | None:
    env = os.environ.get("CMS_SEEDS_DIR", "").strip()
    if not env:
        try:
            from app.config import get_settings

            s = get_settings()
            if s.cms_seeds_dir:
                env = s.cms_seeds_dir
        except Exception:
            pass
    if env and Path(env).exists():
        return Path(env)
    here = Path(__file__).resolve()
    backend_root = here.parents[3]  # .../9wellbackend
    candidates = [
        backend_root / "content" / "cms-seeds",
        backend_root.parent / "9wellcms" / "content" / "cms-seeds",
        Path.cwd() / "content" / "cms-seeds",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def seed_bundles_from_files(client: Client, overwrite: bool = True) -> list[str]:
    seeds = get_seeds_dir()
    if not seeds:
        raise FileNotFoundError("CMS seeds directory not found (set CMS_SEEDS_DIR)")
    written: list[str] = []
    for key in BUNDLE_KEYS:
        path = seeds / f"{key}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not overwrite:
            existing = get_bundle(client, key)
            if existing and existing.get("payload") and existing["payload"] != {}:
                continue
        upsert_bundle(client, key, payload)
        written.append(key)
    return written


def _js_assign(name: str, value: Any) -> str:
    return f"window.{name} = {json.dumps(value, ensure_ascii=False, indent=2)};\n"


def write_learn(root: Path, payload: dict) -> str:
    parts = [
        "// Generated by 9well CMS — do not edit by hand\n",
        _js_assign("NW_TIERS", payload.get("NW_TIERS") or {}),
        _js_assign("NW_TIER_ORDER", payload.get("NW_TIER_ORDER") or []),
        _js_assign("NW_SCALE", payload.get("NW_SCALE") or []),
        _js_assign("NW_WEEKS", payload.get("NW_WEEKS") or []),
        _js_assign("NW_FORMS", payload.get("NW_FORMS") or {}),
        _js_assign("NW_CHECKINS", payload.get("NW_CHECKINS") or {}),
        _js_assign("NW_SUMMARY", payload.get("NW_SUMMARY") or {}),
    ]
    rel = "9well-learn/curriculum.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return rel


def write_shop(root: Path, payload: dict) -> str:
    parts = [
        "// Generated by 9well CMS\n",
        _js_assign("NW_SHOP_DISCLAIMER", payload.get("disclaimer") or ""),
        _js_assign("NW_SHOP_CATS", payload.get("cats") or {}),
        _js_assign("NW_PRODUCTS", payload.get("products") or []),
    ]
    rel = "9well-shop/products.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return rel


def write_hub_videos(root: Path, payload: dict) -> str:
    videos = payload.get("videos") if isinstance(payload, dict) else payload
    if isinstance(videos, dict) and "videos" in videos:
        videos = videos["videos"]
    rel = "9well-hub/videos.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("// Generated by 9well CMS\n" + _js_assign("NINEWELL_VIDEOS", videos or []), encoding="utf-8")
    return rel


def write_hub_cats_into_articles_header(root: Path, cats: dict) -> None:
    """Cats live in articles.js as NINEWELL_CATS — merged in write_hub_articles."""
    pass


def write_hub_articles(root: Path, posts: list[dict], cats: dict) -> str:
    articles = []
    for p in posts:
        articles.append(
            {
                "slug": p.get("slug"),
                "cat": p.get("cat_key") or "co-the",
                "title": p.get("title"),
                "excerpt": p.get("excerpt") or "",
                "author": p.get("author") or "",
                "reviewed": p.get("reviewed") or "",
                "date": (str(p.get("published_at") or "")[:10] or ""),
                "created_at": str(p.get("created_at") or p.get("published_at") or ""),
                "readMin": int(p.get("read_min") or 5),
                "featured": bool(p.get("featured")),
                "tags": p.get("tags") if isinstance(p.get("tags"), list) else [],
                "body": p.get("body_html") or "",
            }
        )
    rel = "9well-hub/articles.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "// Generated by 9well CMS\n"
        + _js_assign("NINEWELL_CATS", cats or {})
        + _js_assign("NINEWELL_ARTICLES", articles)
    )
    path.write_text(text, encoding="utf-8")
    return rel


def write_portal(root: Path, payload: dict) -> str:
    rel = "9well-app/portal-data.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Generated by 9well CMS\n" + _js_assign("NW_PORTAL_DATA", payload or {}),
        encoding="utf-8",
    )
    return rel


def write_trainer(root: Path, payload: dict) -> str:
    rel = "9well-trainer/trainer-data.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Generated by 9well CMS\n" + _js_assign("NW_TRAINER_DATA", payload or {}),
        encoding="utf-8",
    )
    return rel


def write_game(root: Path, payload: dict) -> str:
    rel = "9well-game/game-data.js"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Generated by 9well CMS\n" + _js_assign("NW_GAME_DATA", payload or {}),
        encoding="utf-8",
    )
    return rel


def publish_all_static(client: Client, blog_posts: list[dict]) -> list[str]:
    roots = get_static_roots()
    files: list[str] = []

    def payload(key: str) -> dict:
        row = get_bundle(client, key)
        return (row or {}).get("payload") or {}

    learn = payload("learn_curriculum")
    shop = payload("shop_catalog")
    videos = payload("hub_videos")
    cats_row = payload("hub_categories")
    cats = cats_row.get("cats") if isinstance(cats_row, dict) else cats_row
    portal = payload("portal_app")
    trainer = payload("trainer")
    game = payload("game")

    written_rel: list[str] = []
    for root in roots:
        batch: list[str] = []
        if learn:
            batch.append(write_learn(root, learn))
        if shop:
            batch.append(write_shop(root, shop))
        batch.append(write_hub_videos(root, videos))
        batch.append(write_hub_articles(root, blog_posts, cats or {}))
        batch.append(write_portal(root, portal))
        batch.append(write_trainer(root, trainer))
        batch.append(write_game(root, game))
        for key in ("landing_copy", "legal_pages"):
            p = payload(key)
            snap = root / "_cms" / f"{key}.json"
            snap.parent.mkdir(parents=True, exist_ok=True)
            snap.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
            batch.append(str(snap.relative_to(root)))
        if root == roots[0]:
            written_rel = batch
    return written_rel
