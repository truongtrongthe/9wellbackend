## 9well frontend integration notes (replace localStorage mock)

### Run the API (from repo root `9wellbackend/`)
Do **not** run `python app/main.py` (Python puts `app/` on `sys.path`, so `import app` fails). Use either:
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- `python run_server.py`
- `python -m app`

### Auth
- **Signup**: `POST /auth/signup`
  - Body: `{ name, email, phone?, password, confirmPassword }`
  - Response: `{ message, user }`
- **Login**: `POST /auth/login`
  - Body: `{ email, password }`
  - Response: `{ user, token, refreshToken }`
- **Me**: `GET /auth/me` with header `Authorization: Bearer <token>`
- **Refresh**: `POST /auth/refresh` with body `{ refreshToken }` (rotate refresh token)
- **Logout**: `POST /auth/logout` with header `Authorization: Bearer <token>`
  - Body: `{ refreshToken? }` (omit to logout all sessions)

**Suggested client storage**
- Store `token` in memory (or short-lived storage) and `refreshToken` in secure storage.
- If a request returns 401 with `X-Token-Expired: true`, call `/auth/refresh`, then retry.

### Membership / entitlement
- **Packages catalog**: `GET /membership/packages` (public)
- **My membership**: `GET /membership/me` (Bearer)
  - Response: `{ status: 'none'|'trial'|'active'|'expired'|'canceled', current_period_end, package? }`

**Mapping from current UI**
- Replace `SubscriptionContext` localStorage with a query to `/membership/me`.
- Keep `canAccessContent(status, meta)` logic, but feed it `status` from backend.

### Purchase (MoMo)
- Create checkout: `POST /checkout/momo` (Bearer)
  - Body: `{ packageCode, returnUrl, notifyUrl?, mode: 'redirect'|'qr', idempotencyKey? }`
  - Response: `{ orderId, paymentId, payUrl?, deeplink?, qrCodeUrl? }`
- After redirect/QR payment completes, the backend is updated via MoMo IPN:
  - `POST /webhooks/momo/ipn` (server-to-server)

**Client flow**
- Call checkout, then:
  - If `payUrl` exists: redirect browser to it.
  - Else if `qrCodeUrl` exists: render QR.
- Poll `/membership/me` (or refresh page and call it) to reflect activation.

### Learning roadmap (progress + notes)
Apply `sql/002_learning_roadmap.sql` in Supabase **after** `sql/001_init.sql`. All routes require `Authorization: Bearer <token>`.

- **Roadmap**: `GET /roadmap` — modules with effective `status` (`locked` | `in_progress` | `completed`). First visit bootstraps progress + default AI guidance row.
- **AI guidance**: `GET /roadmap/ai-guidance` — latest message or `{ message: null }`.
- **Notes**: `GET /roadmap/notes?limit=20&offset=0`, `POST /roadmap/notes` with body `{ content }`.
- **Progress**: `PATCH /roadmap/progress/{moduleId}` with body `{ status: 'in_progress' | 'completed' }` — completing a module unlocks the next (`in_progress`).

Admin console (login as admin user, subscription grants, API key): see [FRONTEND_ADMINCONSOLE.md](FRONTEND_ADMINCONSOLE.md).
