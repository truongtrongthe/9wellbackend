# Admin console — frontend integration

Same API base URL as the main 9well app. An **admin is a normal user** in `users`: they sign up / log in with the same auth endpoints; the only difference is `role: "admin"` in the database (and optionally `ADMIN_API_KEY` for server-to-server calls without a user session).

## Auth for admin users (same as end users)

Use the standard auth flow; include `role` from `user` in the login response when you build the admin shell.

- **Login**: `POST /auth/login`
  - Body: `{ email, password }`
  - Response: `{ user, token, refreshToken }` — `user` includes `role` (`"user"` | `"admin"`). After login, if `user.role !== "admin"`, do not expose admin routes in the UI (or redirect).
- **Current session**: `GET /auth/me` with header `Authorization: Bearer <token>` — confirms the token and returns the same user shape (including `role`).
- **Refresh**: `POST /auth/refresh` with body `{ refreshToken }` (rotate refresh token).
- **Logout**: `POST /auth/logout` with header `Authorization: Bearer <token>` and body `{ refreshToken? }`.

**Suggested client storage (admin app or admin area)**

- Store `token` / `refreshToken` the same way as the main app.
- On 401 with `X-Token-Expired: true`, call `/auth/refresh` and retry the admin request.

**Bootstrap checklist**

1. Run `sql/003_admin_user_role.sql` in Supabase so `users.role` exists.
2. Promote at least one account: e.g. `update users set role = 'admin' where email = '<your-admin-email>';`
3. That person logs in via `POST /auth/login` like any other user; the admin console uses their Bearer token on `/admin/*` routes below.

## Admin API — list users

- **List users**: `GET /admin/users?limit=50&offset=0`
  - **Auth (pick one)**:
    - **`X-Admin-Key`**: must match env `ADMIN_API_KEY`, or
    - **`Authorization: Bearer <access_token>`**: admin user token.
  - Query params:
    - `limit` (1–200, default 50)
    - `offset` (default 0)
  - Response: array of user objects, sorted by newest first.

**Example**

```http
GET /admin/users?limit=20&offset=0
Authorization: Bearer <access_token>
```

**Response**

```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "name": "Nguyễn Văn A",
    "role": "user",
    "created_at": "2025-01-07T10:00:00+00:00"
  }
]
```

---

## Admin API — grant / activate subscription

- **Activate (gift / support)**: `POST /admin/subscriptions/activate`
  - **Auth (pick one)**:
    - **`X-Admin-Key`**: must match env `ADMIN_API_KEY` on the server (good for scripts / internal tools without a logged-in admin user), or
    - **`Authorization: Bearer <access_token>`**: access token from `POST /auth/login` for a user whose row has **`role = 'admin'`** in the database.
  - Body (camelCase or snake_case): `{ userId, packageCode, durationDays?, status? }`
    - `status`: `active` or `trial` (default `active`).
    - If `durationDays` is omitted, the catalog package’s `duration_days` is used.

**Example (logged-in admin)**

```http
POST /admin/subscriptions/activate
Authorization: Bearer <access_token>
Content-Type: application/json

{ "userId": "<target-user-uuid>", "packageCode": "monthly", "status": "active" }
```

**Example (API key, no user session)**

```http
POST /admin/subscriptions/activate
X-Admin-Key: <same value as ADMIN_API_KEY in server env>
Content-Type: application/json

{ "userId": "<target-user-uuid>", "packageCode": "monthly" }
```
