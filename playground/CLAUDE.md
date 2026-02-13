# CLAUDE.md - Playground

## What This Is

This is the **playground** folder - a Docker-based target application ("TaskFlow") purpose-built for learning **JMeter performance testing** and **Playwright automation testing**. It is the shared test target for all testing tools in this knowledge base.

This is not a production app - it's a **testing training ground** where different user flows present different testing challenges.

## Build Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation (MVP) - Docker, DB, Auth, Task CRUD | Done |
| 2 | Full API - All TC03-TC10 endpoints + Playwright approval | Done |
| 3 | Frontend - All pages, Playwright UI features | In Progress |
| 4 | Polish - Error pages, responsive, docs | Not Started |

## Test Cases Overview

| TC | Flow | Difficulty | Key Challenges |
|----|------|-----------|----------------|
| TC01 | Login and Browse | Beginner | Embedded resources, `_csrf` hidden input, JWT correlation |
| TC02 | Create a Task | Beginner | CSV parameterization, prerequisite flow reuse |
| TC03 | Task with File Attachment | Intermediate | Multipart file upload, chained requests |
| TC04 | Schedule Booking * | Advanced | Multi-step correlation chain, 302 redirect, raw hash link, mixed data sources |
| TC05 | Batch Update * | Advanced | JSR223 Groovy, URL-encoded JSON in form field |
| TC06 | Registration + Email Verification | Intermediate | URL token extraction, nested extraction |
| TC07 | Password Reset | Intermediate | Hash + expiry in URL, redirect handling |
| TC08 | Slow and Flaky Endpoints * | Beginner | Timeouts, error assertions, rate limiting |
| TC09 | Admin Panel (Cookie Session) * | Beginner | HTTP Cookie Manager, server-side sessions |
| TC10 | Bulk Export (Async Polling) * | Intermediate | While Controller, RegEx on plain text, poll-until-done |

## Directory Structure (Current)

```
playground/
├── CLAUDE.md                    # This file
├── PLAN.md                      # Full spec (test cases, API design, phases)
├── README.md
├── docker-compose.yml           # 5 services: nginx, frontend, backend, postgres, redis
├── .env.example
├── .gitignore
├── nginx/
│   └── nginx.conf               # Reverse proxy: / → frontend:5173, /api → backend:4000
├── db/
│   └── init.sql                 # Schema + seed data (users, tasks, comments, etc.)
├── scripts/
│   ├── health-check.sh
│   └── seed-data.sh
├── backend/
│   ├── Dockerfile               # Node 20 Alpine, tsx watch for dev
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts             # Express app entry, route mounting, middleware
│       ├── config/
│       │   ├── index.ts         # Environment variables (PORT, DB, Redis, JWT, CORS)
│       │   ├── database.ts      # pg.Pool + queryDb/queryOne helpers
│       │   └── redis.ts         # Redis client connection
│       ├── middleware/
│       │   ├── auth.ts          # JWT verify (authenticate + optionalAuth)
│       │   ├── csrf.ts          # CSRF generate/validate (Redis, 30min TTL, one-time)
│       │   ├── roles.ts         # requireRole('manager', 'admin')
│       │   ├── ajax.ts          # Require Accept + X-Requested-With headers (406 if missing)
│       │   └── rateLimit.ts     # In-memory rate limiter (per-IP, 429 + Retry-After)
│       ├── routes/
│       │   ├── auth.ts          # register, login, verify, forgot/reset password, refresh, logout
│       │   ├── tasks.ts         # CRUD + batch-edit/update + report/export + attachments + comments + approval workflow
│       │   ├── users.ts         # list, profile, avatar upload/serve
│       │   ├── dashboard.ts     # stats, recent activity
│       │   ├── admin.ts         # cookie session auth + health/seed + users/stats
│       │   ├── files.ts         # file download by attachment ID
│       │   ├── schedules.ts     # GET/POST schedule form, list schedules
│       │   ├── scheduleConfirm.ts # review, confirm, raw hash confirm link
│       │   ├── reports.ts       # full-export (memory-intensive join)
│       │   └── exports.ts       # async export: POST→202, poll text/html, download
│       ├── services/
│       │   └── auth.ts          # JWT sign/verify, bcrypt hash/verify, refresh token CRUD
│       └── seed/
│           └── seed.ts          # Programmatic re-seed (drops all data, re-runs init.sql seed section)
└── frontend/
    ├── Dockerfile               # Node 20 Alpine, Vite dev server
    ├── package.json             # React 19, React Router 7, Vite 6
    ├── tsconfig.json
    ├── vite.config.ts           # Port 5173, proxy /api → backend:4000
    ├── index.html               # Entry with Inter font preload
    ├── public/
    │   ├── favicon.ico
    │   ├── fonts/.gitkeep       # Inter font woff2 goes here
    │   └── images/logo.svg      # Blue checkmark logo
    └── src/
        ├── main.tsx             # React entry with BrowserRouter
        ├── App.tsx              # Routes + ProtectedRoute HOC
        ├── index.css            # All styles (Inter font, layout, components)
        ├── components/
        │   ├── Toast.tsx        # Context-based toast notifications (Phase 3 WIP)
        │   ├── ConfirmDialog.tsx # Reusable confirmation modal (Phase 3 WIP)
        │   └── Navbar.tsx       # Shared navigation bar (Phase 3 WIP)
        ├── pages/
        │   ├── LoginPage.tsx    # CSRF hidden inputs, JWT storage
        │   ├── DashboardPage.tsx # Parallel AJAX (stats + recent)
        │   ├── TaskListPage.tsx # Pagination, status filter
        │   ├── TaskCreatePage.tsx # CSRF + users dropdown
        │   └── ReviewQueuePage.tsx # Manager approve/reject with modal
        └── services/
            └── api.ts           # Fetch wrapper with JWT + AJAX headers
```

## Backend API Summary

### Auth Routes (`/api/auth`) — Requires AJAX headers
| Method | Path | Auth | CSRF | Special |
|--------|------|:----:|:----:|---------|
| GET | `/api/auth/csrf` | No | — | Returns `{_csrf, _formId}` |
| POST | `/api/auth/login` | No | Yes | Rate limited (10/min). Returns JWT + refresh token |
| POST | `/api/auth/register` | No | Yes | Returns `verificationUrl` with token+hash |
| GET | `/api/auth/verify` | No | — | Validates token+hash → **302** to `/login?verified=true` |
| POST | `/api/auth/forgot-password` | No | Yes | Returns `resetUrl` with hash+expires |
| GET | `/api/auth/reset-password` | No | — | Validates hash → returns CSRF + resetToken |
| POST | `/api/auth/reset-password` | No | Yes | Changes password → **302** to `/login?reset=success` |
| POST | `/api/auth/refresh` | No | — | Rotates refresh token, returns new JWT |
| POST | `/api/auth/logout` | Yes | — | Revokes refresh token |

### Task Routes (`/api/tasks`) — Requires Auth + AJAX headers
| Method | Path | CSRF | Special |
|--------|------|:----:|---------|
| GET | `/api/tasks` | — | Paginated (?page, ?limit, ?status, ?assignee). Staff sees own tasks only |
| GET | `/api/tasks/batch-edit` | — | Returns tasks + CSRF tokens for batch form |
| POST | `/api/tasks/batch-update` | Yes | Accepts `changesList` (URL-encoded JSON) |
| GET | `/api/tasks/report` | — | Slow endpoint (?delay=ms, max 10s) |
| GET | `/api/tasks/export` | — | Flaky endpoint (20% random 500) |
| GET | `/api/tasks/:id` | — | Returns task + comments + CSRF tokens |
| POST | `/api/tasks` | Yes | Create task |
| PUT | `/api/tasks/:id` | Yes | Update task (staff: own only) |
| DELETE | `/api/tasks/:id` | Yes | Delete task (staff: own only) |
| POST | `/api/tasks/:id/attachments` | Yes | Multipart upload (multer → then CSRF) |
| GET | `/api/tasks/:id/attachments` | — | List with downloadUrl |
| POST | `/api/tasks/:id/comments` | Yes | Add comment |
| PUT | `/api/tasks/:id/submit-review` | Yes | Staff submits (open/in_progress/rejected → pending_review) |
| PUT | `/api/tasks/:id/approve` | Yes | Manager only (pending_review → approved) |
| PUT | `/api/tasks/:id/reject` | Yes | Manager only, requires remarks |

### Schedule Routes (`/api/tasks` + `/api/schedules`) — Requires Auth + AJAX headers
| Method | Path | CSRF | Special |
|--------|------|:----:|---------|
| GET | `/api/tasks/:id/schedule` | — | Returns available slots, departments, CSRF tokens |
| POST | `/api/tasks/:id/schedule` | Yes | Heavy payload (15+ fields) → **302** redirect to review |
| GET | `/api/tasks/:id/schedules` | — | List existing schedules |
| GET | `/api/schedules/:confirmationId/review` | — | Schedule details + CSRF tokens |
| POST | `/api/schedules/:confirmationId/confirm` | Yes | Returns `confirmUrl` with **raw hash** (no key=value) |
| GET | `/api/schedules/confirm?<hash>` | — | Raw hash lookup (entire query string is the hash) |

### User Routes (`/api/users`) — Requires Auth + AJAX headers
| Method | Path | CSRF | Special |
|--------|------|:----:|---------|
| GET | `/api/users` | — | List all users (for dropdowns) |
| GET | `/api/users/me` | — | Current user profile |
| PUT | `/api/users/me` | Yes | Update displayName |
| POST | `/api/users/me/avatar` | Yes | Multipart upload (2MB, images only) |
| GET | `/api/users/avatars/:filename` | — | Serve avatar file (no auth) |

### Dashboard Routes (`/api/dashboard`) — Requires Auth + AJAX headers
| Method | Path | Special |
|--------|------|---------|
| GET | `/api/dashboard/stats` | Task counts by status. Staff sees own tasks only |
| GET | `/api/dashboard/recent` | Recent tasks + comments (?limit, max 50) |

### Admin Routes (`/api/admin` + `/admin`) — Cookie-based session, NO AJAX headers required
| Method | Path | Auth | CSRF | Special |
|--------|------|:----:|:----:|---------|
| GET | `/api/admin/health` | No | — | Health check (DB + Redis) |
| POST | `/api/admin/seed` | No | — | Reset DB to seeded state |
| GET | `/admin/login` | No | — | Sets SESSIONID cookie + returns CSRF tokens |
| POST | `/api/admin/auth/login` | No | Yes | Validates admin creds, sets session cookie (Redis) |
| POST | `/api/admin/auth/logout` | No | — | Clears session (Redis + DB + cookie) |
| GET | `/api/admin/users` | Session | — | List all users (requires admin session cookie) |
| GET | `/api/admin/stats` | Session | — | System stats (users, tasks, comments by status/role) |

### Export Routes (`/api/exports`) — Requires Auth + AJAX headers
| Method | Path | CSRF | Special |
|--------|------|:----:|---------|
| POST | `/api/exports` | — | Returns **202 Accepted** + `{jobId, statusUrl}` |
| GET | `/api/exports/:jobId/status` | — | Returns **text/html**: `<OK>2/5` or `<OK>@LNK<url>` |
| GET | `/api/exports/download/:hash` | — | Returns export data JSON |

### Other
| Method | Path | Special |
|--------|------|---------|
| GET | `/api/files/:fileId/:fileName` | File download (requires Auth only, no AJAX headers) |
| GET | `/api/reports/full-export` | Memory-intensive export (requires Auth + AJAX) |

## Authentication Patterns

### JWT Auth (API routes)
1. Client calls `GET /api/auth/csrf` → receives `{_csrf, _formId}`
2. Client POSTs to `/api/auth/login` with email + password + _csrf + _formId
3. Server returns `{accessToken, refreshToken, user}`
4. Client stores accessToken in localStorage, sends as `Authorization: Bearer <token>`
5. Access token expires in 15 minutes; refresh via `POST /api/auth/refresh`
6. Refresh tokens are SHA256-hashed in DB, 7-day expiry, rotated on each refresh

### Cookie Auth (Admin routes)
1. Client calls `GET /admin/login` → receives `Set-Cookie: SESSIONID=...` + `{_csrf, _formId}`
2. Client POSTs to `/api/admin/auth/login` with email + password + _csrf + _formId
3. Server stores session in Redis (`admin_session:<id>` → userId, 1hr TTL), sets new SESSIONID cookie
4. Browser automatically sends cookie on subsequent requests
5. `requireAdminSession` middleware reads cookie → checks Redis → validates admin role

### CSRF Tokens
- Generated as pair: `{_csrf, _formId}`
- Stored in Redis with key `csrf:<formId>` → csrf value, 30-minute TTL
- Validated by comparing `req.body._csrf` against Redis-stored value for `req.body._formId`
- **One-time use**: deleted from Redis after validation
- Must be sent in request body (or headers `x-csrf-token` + `x-form-id`)
- For multipart uploads: multer parses form data FIRST, then CSRF middleware reads `req.body`

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | id, email, password_hash, display_name, role, is_verified, avatar_url |
| `tasks` | id, title, description, status, priority, assignee_id, creator_id, project_code |
| `comments` | id, task_id, user_id, content |
| `refresh_tokens` | id, user_id, token_hash, expires_at |
| `attachments` | id, task_id, user_id, original_name, stored_name, mime_type, size_bytes |
| `schedules` | id, task_id, user_id, confirmation_id, confirm_hash, slot_date, slot_time, department, priority, notes, payload (JSONB), status |
| `verification_tokens` | id, user_id, token, type (email_verify/password_reset), used, expires_at |
| `export_jobs` | id, user_id, job_id, status, total_steps, current_step, download_hash, filters, completed_at |
| `admin_sessions` | id, session_id, user_id, expires_at |

## Seed Data

| Entity | Count | Pattern |
|--------|-------|---------|
| Users (staff) | 15 | `user01@taskflow.local` / `password01` through `user15` / `password15` |
| Users (manager) | 5 | `user16@taskflow.local` / `password16` through `user20` / `password20` |
| Admin | 1 | `admin@taskflow.local` / `admin123` (cookie session only) |
| Tasks | 200 | Mixed statuses, assigned to various users |
| Comments | 500 | Distributed across tasks |

## Docker Commands

```bash
docker compose up -d                    # Start all services
docker compose down                     # Stop all services
docker compose up -d --build            # Rebuild and start
docker compose up -d --build --renew-anon-volumes  # Rebuild with fresh node_modules
docker compose restart backend          # Restart backend (after code changes)
docker compose logs -f backend          # Tail backend logs
docker builder prune -f                 # Fix Docker cache issues
```

Reset database: `curl -X POST http://localhost:4000/api/admin/seed`
Health check: `curl http://localhost:4000/api/admin/health`

## Frontend Pages (Phase 3 Progress)

| Page | Route | Status | Purpose |
|------|-------|--------|---------|
| Login | `/login` | Done | CSRF hidden inputs, JWT storage |
| Register | `/register` | TODO | Registration + verification URL |
| Dashboard | `/dashboard` | Done | Parallel AJAX (stats + recent) |
| Task List | `/tasks` | Done | Pagination, status filter |
| Task Detail | `/tasks/:id` | TODO | 4 parallel AJAX, comments, attachments |
| Create Task | `/tasks/new` | Done | CSRF + users dropdown |
| Schedule Task | `/tasks/:id/schedule` | TODO | Heavy form, conditional fields |
| Batch Edit | `/tasks/batch-edit` | TODO | JS-built changesList payload |
| Profile | `/profile` | TODO | Avatar upload, edit name |
| Review Queue | `/tasks/review` | Done | Manager approve/reject modal |
| Admin Login | `/admin/login` | TODO | Cookie-based session auth |
| Admin Dashboard | `/admin/dashboard` | TODO | User list, system stats |

## Important Rules

- Never add external service dependencies - the app must run fully offline in Docker
- Seed data credentials must stay predictable (`user01`/`password01` pattern) - tests depend on this
- The `/api/admin/seed` endpoint must always be available to reset the DB to a known state
- Deliberate test scenarios (slow/flaky endpoints) should be configurable via query params, not removed
- Keep the frontend simple - it exists for Playwright testing, not to win design awards
- Educational bolt-ons (marked with * in PLAN.md) exist to create testing challenges - preserve them
- Hidden tokens are limited to `_csrf` and `_formId` - do not add extra token types
- Role-based permissions must be enforced server-side (not just UI hiding)
- AJAX navigation: after initial page load, all in-app navigation uses JSON API calls (no full page reload)
- Backend enforces `Accept: application/json` and `X-Requested-With: XMLHttpRequest` headers for AJAX routes
- Admin routes do NOT require AJAX headers or JWT - they use cookie-based sessions
- For multipart file uploads, multer middleware must come BEFORE CSRF validation in the middleware chain
- Route ordering in tasks.ts: batch-edit, report, export routes are placed BEFORE `/:id` to avoid Express parameter capture

## Known Quirks

- **Docker volume caching**: After adding new npm packages, use `--renew-anon-volumes` to refresh the anonymous `node_modules` volume
- **tsx watch in Docker**: File change detection through Docker volume mount from Windows can be unreliable. Use `docker compose restart backend` if changes aren't detected
- **CORS origin**: Set to `http://taskflow.local` in .env. For direct `localhost:4000` access, CORS may block browser requests
- **Cygwin curl**: Avoid `;type=` syntax for multipart uploads (use plain `-F "file=@path"` instead)
