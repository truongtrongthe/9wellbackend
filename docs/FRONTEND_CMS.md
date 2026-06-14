# Frontend CMS — API 9wellbackend

## Public site (`apps/web`) — không cần auth

Prefix: `/content`

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/course` | 8 tuần + lesson metadata (no body) |
| GET | `/lessons/{id}` | Full lesson nếu free_trial hoặc Bearer + subscription |
| GET | `/blog` | List posts |
| GET | `/blog/{slug}` | Chi tiết bài |
| GET | `/pricing` | Plans + FAQ + timeline + settings |
| GET | `/settings` | Zalo, Messenger links |
| POST | `/revalidate` | Header `X-Revalidate-Secret` — purge Next.js cache |

Lesson gating: `403` + `{ locked: true }` — không trả `body_html`.

## Admin UI (`apps/admin`)

Prefix: `/admin/content` — Bearer + `role=admin`

| Method | Path | Mô tả |
|--------|------|--------|
| GET/PATCH | `/lessons`, `/blog`, … | CRUD (như cũ) |
| POST | `/media` | Upload ảnh → Supabase `cms-media` |
| POST | `/publish` | Revalidate Next.js (không còn build static) |

## Auth

`POST /auth/login`, `GET /auth/me`, `GET /membership/me` — gating bài học trả phí.

## Env backend

```
REVALIDATE_SECRET=
VERCEL_REVALIDATE_URL=https://9well.com
CORS_ORIGINS=https://9well.com,https://admin.9well.com
```

## Env web (Vercel)

```
NEXT_PUBLIC_API_BASE_URL=https://api.9well.com
REVALIDATE_SECRET=
SITE_URL=https://9well.com
```
