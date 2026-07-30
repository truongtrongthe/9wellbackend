from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.admin.content.static_publish import BUNDLE_KEYS, list_bundles

SITE_ORIGIN = "https://9well.com"

MODULES: list[dict[str, Any]] = [
    {
        "id": "learn",
        "label": "Khóa học",
        "admin": "/learn",
        "live": "/learn",
        "bundle": "learn_curriculum",
        "publish_files": ["9well-learn/curriculum.js"],
        "description": "Curriculum 8 tuần — Lưu live qua API; mỗi bài VIDEO dán YouTube (ytid); free=true = học thử full trên overview; intro/demo video ở Portal → Video Learn (portal-config)",
    },
    {
        "id": "blog",
        "label": "Thư viện",
        "admin": "/blog",
        "live": "/blog",
        "bundle": "hub_videos + blog_posts",
        "publish_files": ["9well-hub/articles.js", "9well-hub/videos.js"],
        "description": "Bài viết live qua API; Video YouTube/Short: tab Video → Lưu (API /content/hub-videos + videos.js)",
    },
    {
        "id": "shop",
        "label": "Shop",
        "admin": "/shop",
        "live": "/shop",
        "bundle": "shop_catalog",
        "publish_files": ["9well-shop/products.js"],
        "description": "Sản phẩm TPCN và combo",
    },
    {
        "id": "portal",
        "label": "Portal",
        "admin": "/portal",
        "live": "/app",
        "bundle": "portal_app",
        "publish_files": ["9well-app/portal-data.js"],
        "description": "Plans, quiz, weeks; payment/Zalo + introYtid/demoVideoYtid Learn trong portal-config (tab Video Learn)",
    },
    {
        "id": "trainer",
        "label": "Trainer",
        "admin": "/trainer",
        "live": "/trainer",
        "bundle": "trainer",
        "publish_files": ["9well-trainer/trainer-data.js"],
        "description": "Bài tập và chương trình luyện",
    },
    {
        "id": "game",
        "label": "Game",
        "admin": "/game",
        "live": "/game",
        "bundle": "game",
        "publish_files": ["9well-game/game-data.js"],
        "description": "Câu hỏi quiz RPG và levels",
    },
    {
        "id": "landing",
        "label": "Landing",
        "admin": "/landing",
        "live": "/",
        "bundle": "landing_copy",
        "publish_files": ["_cms/landing_copy.json"],
        "description": "Hero, quiz 60s, FAQ — web đọc API /content/landing",
    },
    {
        "id": "pricing",
        "label": "Giá & FAQ",
        "admin": "/pricing",
        "live": "/lieu-trinh",
        "bundle": None,
        "publish_files": [],
        "description": "Gói pricing_plans + cms_faqs",
    },
    {
        "id": "legal",
        "label": "Legal",
        "admin": "/legal",
        "live": "/legal",
        "bundle": "legal_pages",
        "publish_files": ["_cms/legal_pages.json"],
        "description": "Miễn trừ, privacy, terms — web đọc API /content/legal",
    },
]

WORKFLOW = [
    {
        "step": 1,
        "action": "Lưu",
        "detail": "Blog: «Lưu & đưa lên web». Learn/Pricing/Landing/Legal: Lưu. Ghi DB → live qua API.",
    },
    {
        "step": 2,
        "action": "Seed (lần đầu)",
        "detail": "Trang Xuất bản → Seed từ offline v3 nếu DB trống.",
    },
    {
        "step": 3,
        "action": "Preview",
        "detail": "Mở URL live. Blog/Learn không cần /publish mỗi lần.",
    },
    {
        "step": 4,
        "action": "Xuất bản (chỉ khi cần)",
        "detail": "Shop/Portal/Trainer/Game: /publish ghi file tĩnh. Blog/Learn: chỉ khi sync articles.js / curriculum.js.",
    },
]

CHECKLIST = [
    "Đã Lưu (blog: Lưu & đưa lên web)",
    "Badge / preview live OK",
    "Seed (chỉ lần đầu hoặc reset)",
    "/publish chỉ nếu module cần file tĩnh hoặc được yêu cầu sync",
]

GLOSSARY = [
    {"term": "ytid", "meaning": "YouTube video ID trên lesson Learn hoặc hub video"},
    {"term": "free", "meaning": "Lesson Learn: học thử — overview khách xem full body"},
    {"term": "fmt", "meaning": "Loại bài: VIDEO, AUDIO, DOC, FORM, RESULT"},
    {"term": "write[]", "meaning": "Prompt nhật ký trong lesson: {k, q, ph}"},
    {"term": "NW_CHECKINS", "meaning": "Check-in tuần 1–8: intro, extra[], outro"},
    {"term": "NW_SUMMARY", "meaning": "Phiếu tổng kết bài 8.7"},
    {"term": "cat_key", "meaning": "Danh mục hub: co-the, luyen-tap, tam-ly, cap-doi, loi-song"},
    {"term": "bundle", "meaning": "JSON trong cms_content_bundles (key → payload)"},
    {
        "term": "đưa lên web",
        "meaning": "Nút «Lưu & đưa lên web» — set published + lưu; bài blog live ngay qua API",
    },
    {
        "term": "publish",
        "meaning": "/publish → ghi public/v2/*.js — bắt buộc Shop/Portal/Trainer/Game; KHÔNG bắt buộc mỗi bài blog",
    },
]

RECIPES = [
    {
        "title": "Sửa bài học 7.2",
        "steps": [
            "Mở /learn → tab Tuần & bài",
            "Chọn Tuần 7 → chip bài 7.2",
            "Sửa Title, Body → Lưu",
            "Preview https://9well.com/learn",
            "/publish chỉ khi được yêu cầu sync curriculum.js",
        ],
    },
    {
        "title": "Thêm bài blog",
        "steps": [
            "Mở /blog → tab Bài viết → + Thêm bài viết",
            "Điền slug, title, body, cat_key",
            "Bấm «Tạo & đưa lên web» (bài cũ: «Lưu & đưa lên web») — một nút đủ",
            "Xác nhận badge = «Đã xuất bản»",
            "Preview https://9well.com/blog/{slug}",
            "Không vào /publish trừ khi nhiệm vụ yêu cầu sync articles.js",
        ],
    },
    {
        "title": "Thêm video YouTube Short (Blog)",
        "steps": [
            "Mở /blog → tab Video → + Thêm video",
            "Dán link YouTube/Shorts → kiểm tra ID + tiêu đề + danh mục",
            "Thêm vào danh sách → Lưu video lên web",
            "Preview https://9well.com/blog (tab Video trên hub)",
        ],
    },
    {
        "title": "Gắn YouTube cho bài học",
        "steps": [
            "Mở /learn → Tuần & bài → chọn bài VIDEO",
            "Dán URL YouTube vào field YouTube → Lưu",
            "Intro/demo fallback: /portal → tab Video Learn",
            "Preview https://9well.com/learn — click bài trên overview để xem chi tiết",
        ],
    },
    {
        "title": "Đổi giá gói",
        "steps": [
            "Mở /pricing → chọn gói → sửa giá → Lưu gói",
            "Preview https://9well.com/lieu-trinh",
        ],
    },
]

RULES = [
    "Không sửa trực tiếp apps/web/public/v2/",
    "Blog/Learn/Pricing: Lưu (blog: đưa lên web) → preview — không bắt buộc /publish mỗi lần",
    "Shop/Portal/Trainer/Game: Lưu rồi /publish mới chắc trên web",
    "Tab JSON nâng cao chỉ khi cần sửa hàng loạt",
]


def _last_publish_log(client: Client) -> dict[str, Any] | None:
    try:
        res = (
            client.table("publish_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def build_site_map(client: Client) -> dict[str, Any]:
    bundle_rows = {r["key"]: r for r in list_bundles(client)}
    bundles = []
    for key in BUNDLE_KEYS:
        row = bundle_rows.get(key) or {}
        mod = next((m for m in MODULES if m.get("bundle") == key), None)
        bundles.append(
            {
                "key": key,
                "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
                "publish_files": mod["publish_files"] if mod else [],
                "admin": mod["admin"] if mod else None,
                "live": mod["live"] if mod else None,
            }
        )

    routes = [
        {
            "admin": m["admin"],
            "live": m["live"],
            "live_url": f"{SITE_ORIGIN}{m['live']}",
            "label": m["label"],
            "bundle": m.get("bundle"),
            "module": m["id"],
            "publish_files": m.get("publish_files") or [],
        }
        for m in MODULES
    ]

    last = _last_publish_log(client)
    last_publish = None
    if last:
        last_publish = {
            "status": last.get("status"),
            "message": last.get("message"),
            "created_at": str(last.get("created_at")) if last.get("created_at") else None,
        }

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "site_origin": SITE_ORIGIN,
        "modules": MODULES,
        "routes": routes,
        "bundles": bundles,
        "workflow": WORKFLOW,
        "checklist": CHECKLIST,
        "glossary": GLOSSARY,
        "recipes": RECIPES,
        "rules": RULES,
        "last_publish": last_publish,
    }
