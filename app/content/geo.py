"""GEO text builders — keep aligned with apps/web/scripts/blog-geo.mjs"""

from __future__ import annotations

import re
from datetime import date, datetime
from html import unescape
from typing import Any
from xml.sax.saxutils import escape as xml_escape

STATIC_SITEMAP_PAGES: tuple[tuple[str, str, str], ...] = (
    ("/", "daily", "1.0"),
    ("/learn", "weekly", "0.8"),
    ("/shop", "weekly", "0.7"),
    ("/legal", "weekly", "0.3"),
    ("/lieu-trinh", "weekly", "0.8"),
    ("/khoa-hoc", "weekly", "0.5"),
    ("/chuyen-gia", "weekly", "0.6"),
)


def site_base(site_url: str) -> str:
    return site_url.rstrip("/")


def iso_date(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text[:10] if len(text) >= 10 and text[4] == "-" else None


def strip_html(html: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s.replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", s).strip()


def html_to_markdown(html: str) -> str:
    s = (html or "").replace("\r\n", "\n")

    def heading(level: int):
        def repl(_m: re.Match[str]) -> str:
            return f"\n\n{'#' * level} {strip_html(_m.group(1))}\n\n"

        return repl

    s = re.sub(r"<h1[^>]*>([\s\S]*?)</h1>", heading(1), s, flags=re.I)
    s = re.sub(r"<h2[^>]*>([\s\S]*?)</h2>", heading(2), s, flags=re.I)
    s = re.sub(r"<h3[^>]*>([\s\S]*?)</h3>", heading(3), s, flags=re.I)
    s = re.sub(
        r"<blockquote[^>]*>([\s\S]*?)</blockquote>",
        lambda m: f"\n\n> {strip_html(m.group(1))}\n\n",
        s,
        flags=re.I,
    )
    s = re.sub(r"<li[^>]*>([\s\S]*?)</li>", lambda m: f"\n- {strip_html(m.group(1))}", s, flags=re.I)
    s = re.sub(r"</(ul|ol)>", "\n\n", s, flags=re.I)
    s = re.sub(r"<(ul|ol)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<p[^>]*>([\s\S]*?)</p>", lambda m: f"\n\n{strip_html(m.group(1))}\n\n", s, flags=re.I)
    s = re.sub(r"<strong[^>]*>([\s\S]*?)</strong>", lambda m: f"**{strip_html(m.group(1))}**", s, flags=re.I)
    s = re.sub(r"<b[^>]*>([\s\S]*?)</b>", lambda m: f"**{strip_html(m.group(1))}**", s, flags=re.I)
    s = re.sub(r"<em[^>]*>([\s\S]*?)</em>", lambda m: f"*{strip_html(m.group(1))}*", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s.replace("&nbsp;", " "))
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def normalize_takeaways(post: dict[str, Any]) -> list[str]:
    raw = post.get("key_takeaways") or []
    items = [str(s).strip() for s in raw if str(s).strip()]
    if items:
        return items
    excerpt = str(post.get("excerpt") or post.get("seo_description") or "").strip()
    if not excerpt:
        return []
    parts = re.split(r"(?<=[.!?…])\s+", excerpt)
    return [p.strip() for p in parts if len(p.strip()) > 20][:4]


def normalize_faqs(post: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in post.get("faq_items") or []:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "").strip()
        a = str(item.get("answer") or "").strip()
        if q and a:
            out.append({"question": q, "answer": a})
    return out


def post_lastmod(post: dict[str, Any]) -> str | None:
    return iso_date(post.get("updated_at")) or iso_date(post.get("published_at")) or iso_date(post.get("created_at"))


def post_image(post: dict[str, Any]) -> str | None:
    return post.get("hero_image_url") or post.get("thumbnail_url") or None


def build_blog_markdown(post: dict[str, Any], site_url: str) -> str:
    base = site_base(site_url)
    slug = post.get("slug") or ""
    url = f"{base}/blog/{slug}"
    desc = str(post.get("seo_description") or post.get("excerpt") or "").strip()
    takeaways = normalize_takeaways(post)
    faqs = normalize_faqs(post)
    body = html_to_markdown(post.get("body_html") or "")
    lines: list[str] = [
        f"# {post.get('title') or ''}",
        "",
        f"Source: {url}",
        f"Markdown: {url}.md",
    ]
    if post.get("author"):
        lines.append(f"Author: {post['author']}")
    if post.get("category"):
        lines.append(f"Category: {post['category']}")
    if desc:
        lines.append(f"Summary: {desc}")
    lines.append("")
    if takeaways:
        lines.append("## Ý chính")
        lines.extend(f"- {t}" for t in takeaways)
        lines.append("")
    if body:
        lines.extend([body, ""])
    if faqs:
        lines.append("## Câu hỏi thường gặp")
        lines.append("")
        for faq in faqs:
            lines.extend([f"### {faq['question']}", "", strip_html(faq["answer"]), ""])
    lines.extend(["---", "Nội dung mang tính giáo dục sức khỏe, không thay thế tư vấn y khoa."])
    return "\n".join(lines) + "\n"


def build_llms_txt(site_url: str, posts: list[dict[str, Any]]) -> str:
    base = site_base(site_url)
    lines = [
        "# 9well him",
        "> Nền tảng cải thiện sức khỏe sinh lý nam giới — luyện tập, không thuốc, đồng hành cá nhân hóa.",
        "",
        "## Trang chính",
        f"- [Thư viện kiến thức]({base}/): Bài viết sức khỏe nam giới (canonical)",
        f"- [Liệu trình]({base}/lieu-trinh): Gói liệu trình 8 tuần",
        f"- [Khóa học 8 tuần]({base}/learn): Vòng Tự Chủ — lộ trình luyện tập",
        f"- [Shop]({base}/shop): TPCN & vitamin hỗ trợ nền tảng",
        f"- [Pháp lý]({base}/legal): Miễn trừ y tế, quyền riêng tư, điều khoản",
        f"- [Chuyên gia]({base}/chuyen-gia): Đội ngũ chuyên gia",
        "",
        "## Bài viết kiến thức",
    ]
    for post in posts:
        slug = post.get("slug") or ""
        title = post.get("title") or slug
        desc = str(post.get("excerpt") or post.get("seo_description") or "").strip()
        lines.append(f"- [{title}]({base}/blog/{slug})" + (f": {desc}" if desc else ""))
        lines.append(f"  - Markdown: {base}/blog/{slug}.md")
    lines.extend(
        [
            "",
            "## Cho AI crawler",
            f"- Bản đầy đủ: {base}/llms-full.txt",
            f"- Sitemap: {base}/sitemap.xml",
            "",
            "## Lưu ý cho AI",
            "- Nội dung mang tính giáo dục sức khỏe, không thay thế tư vấn y khoa.",
            "- Trang /app, /trainer, /game, /lo-trinh và /bai-hoc là nội dung cá nhân hóa — không index.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_llms_full_txt(site_url: str, posts: list[dict[str, Any]]) -> str:
    base = site_base(site_url)
    parts = [
        "# 9well him — full articles",
        "",
        f"Canonical hub: {base}/",
        f"Index: {base}/llms.txt",
        "",
    ]
    for post in posts:
        parts.extend([build_blog_markdown(post, site_url).strip(), "", "---", ""])
    return "\n".join(parts).rstrip() + "\n"


def build_sitemap_xml(site_url: str, posts: list[dict[str, Any]], today: str | None = None) -> str:
    base = site_base(site_url)
    day = today or date.today().isoformat()
    has_images = any(post_image(p) for p in posts)
    ns = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
    if has_images:
        ns += ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
    chunks: list[str] = []
    for path, freq, prio in STATIC_SITEMAP_PAGES:
        loc = f"{base}/" if path == "/" else f"{base}{path}"
        chunks.append(_url_xml(loc, day, freq, prio, None))
    for post in posts:
        slug = post.get("slug") or ""
        if not slug:
            continue
        loc = f"{base}/blog/{slug}"
        prio = "0.9" if post.get("featured") else "0.8"
        chunks.append(_url_xml(loc, post_lastmod(post) or day, "monthly", prio, post_image(post)))
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset {ns}>\n' + "\n".join(chunks) + "\n</urlset>\n"


def _url_xml(loc: str, lastmod: str | None, changefreq: str, priority: str, image: str | None) -> str:
    lines = ["  <url>", f"    <loc>{xml_escape(loc)}</loc>"]
    if lastmod:
        lines.append(f"    <lastmod>{xml_escape(lastmod)}</lastmod>")
    lines.append(f"    <changefreq>{xml_escape(changefreq)}</changefreq>")
    lines.append(f"    <priority>{xml_escape(priority)}</priority>")
    if image:
        lines.append("    <image:image>")
        lines.append(f"      <image:loc>{xml_escape(image)}</image:loc>")
        lines.append("    </image:image>")
    lines.append("  </url>")
    return "\n".join(lines)
