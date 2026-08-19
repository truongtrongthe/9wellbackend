from app.content.geo import (
    build_blog_markdown,
    build_llms_txt,
    build_sitemap_xml,
    html_to_markdown,
)


SAMPLE = {
    "slug": "xuat-tinh-som-goc-nhin-than-kinh",
    "title": "Xuất tinh sớm nhìn từ góc độ thần kinh: vì sao không phải là “yếu”",
    "excerpt": "Phản xạ xuất tinh được điều khiển bởi hệ thần kinh, không phải bởi “bản lĩnh”. Hiểu đúng cơ chế là bước đầu để tự chủ.",
    "author": "Đội ngũ chuyên môn 9well",
    "category": "Hiểu cơ thể",
    "featured": True,
    "published_at": "2026-08-01T00:00:00+00:00",
    "updated_at": "2026-08-14T00:00:00+00:00",
    "body_html": "<h2 id=\"phan-xa\">Xuất tinh là một phản xạ</h2><p>Giống như phản xạ giật tay.</p>",
}


def test_html_to_markdown_keeps_headings():
    md = html_to_markdown(SAMPLE["body_html"])
    assert "## Xuất tinh là một phản xạ" in md
    assert "Giống như phản xạ giật tay" in md


def test_llms_txt_lists_posts_and_md_twins():
    txt = build_llms_txt("https://9well.com", [SAMPLE])
    assert "/blog/xuat-tinh-som-goc-nhin-than-kinh" in txt
    assert "/blog/xuat-tinh-som-goc-nhin-than-kinh.md" in txt
    assert "llms-full.txt" in txt
    assert "## Bài viết kiến thức" in txt


def test_sitemap_includes_blog_lastmod_not_listing():
    xml = build_sitemap_xml("https://9well.com", [SAMPLE], today="2026-08-14")
    assert "<loc>https://9well.com/blog/xuat-tinh-som-goc-nhin-than-kinh</loc>" in xml
    assert "<lastmod>2026-08-14</lastmod>" in xml
    assert "<loc>https://9well.com/blog</loc>" not in xml
    assert "<priority>0.9</priority>" in xml


def test_blog_markdown_source_line():
    md = build_blog_markdown(SAMPLE, "https://9well.com")
    assert md.startswith("# Xuất tinh sớm")
    assert "Source: https://9well.com/blog/xuat-tinh-som-goc-nhin-than-kinh" in md
