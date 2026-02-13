# Playground - Docker-Based Target Application Plan

## Objective

Build a purpose-built web application for learning **JMeter performance testing** and **automation testing (Playwright)**. The app runs in Docker and is designed so that different user flows present different testing challenges. Not every flow has every obstacle - each test case targets specific skills.

This is not a production app. It's a **testing training ground**.

---

## Why Build a Custom Playground?

- **Controlled challenges** - Each flow is designed to teach specific JMeter/automation obstacles
- **Multiple test cases** - Different flows for different skill levels and challenges
- **Offline & repeatable** - Docker-based, seeded data, one-command reset
- **Full coverage** - Across all flows, covers the full range of real-world PT challenges

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React (Vite) | SPA with real UI - embedded resources, AJAX navigation, JS-built payloads |
| Backend API | Node.js + Express | Lightweight, easy to add endpoints and middleware |
| Database | PostgreSQL | Real relational DB with realistic query patterns |
| Cache | Redis | Session storage + caching layer |
| Orchestration | Docker Compose | `docker compose up` and you're ready |

---

## Application Concept: **TaskFlow** - A Team Task Manager

A task management app. Simple enough to understand, complex enough to generate real testing scenarios. Some features are natural to a task manager; others are explicitly **educational bolt-ons** (marked with *) that exist solely to create testing challenges.

---

## Test Cases and Their Challenges

Each test case is a user flow that can be scripted independently in JMeter. Different flows teach different skills.

### TC01: Login and Browse Tasks
**Difficulty: Beginner**

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | `GET /` (initial page load) | Embedded resources (JS, CSS, fonts, images) |
| 2 | `GET /login` | Hidden input: `_csrf` token in form |
| 3 | `POST /api/auth/login` | Correlation: extract JWT from response |
| 4 | `GET /api/dashboard/stats` + `GET /api/dashboard/recent` | AJAX: parallel requests on page transition |
| 5 | `GET /api/tasks?page=1&limit=20` | Query parameters, pagination |

**Skills covered:** Embedded resources, hidden inputs, token correlation, AJAX parallel calls, HTTP headers

---

### TC02: Create a Task
**Difficulty: Beginner**

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | Login (TC01 steps 1-3) | Prerequisite |
| 2 | `GET /api/tasks/new` + `GET /api/users` | AJAX: 2 parallel calls (form + user dropdown) |
| 3 | `POST /api/tasks` | Parameterization from CSV (title, description, assignee, priority) |

**Skills covered:** CSV Data Set Config, parameterization, prerequisite flow reuse

---

### TC03: Task with File Attachment
**Difficulty: Intermediate**

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | Login + Create task (TC02) | Prerequisite, extract `taskId` from response |
| 2 | `POST /api/tasks/${taskId}/attachments` | `multipart/form-data` file upload |
| 3 | Response contains `downloadUrl` | Extract file path from JSON response |
| 4 | `GET /api/files/${fileId}/${fileName}` | Use extracted values to download |

**Skills covered:** File upload, multipart requests, response extraction, chained requests

---

### TC04: Schedule Booking - Multi-Step Chained Flow *
**Difficulty: Advanced**

Modeled after real booking systems (hostel, flight). The main correlation-heavy flow.

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | Login (TC01) | Prerequisite |
| 2 | `GET /api/tasks?status=open` | Extract `taskId` from JSON array |
| 3 | `GET /api/tasks/${taskId}` | Extract `projectCode` from response |
| 4 | `GET /api/tasks/${taskId}/schedule` | Extract `_csrf`, `_formId`, `availableSlots[]` |
| 5 | `POST /api/tasks/${taskId}/schedule` | Heavy payload: CSV data + `${__time()}` timestamp + correlated values |
| 6 | Response: **302 redirect** | Extract `confirmationId` from `Location` header |
| 7 | `POST /api/schedules/${confirmationId}/confirm` | Use extracted confirmationId |
| 8 | Response contains `confirmUrl` | Extract URL with **raw hash** as query string (no `key=value`) |
| 9 | `GET /api/schedules/confirm?<hash>` | Raw hash in URL — RegEx after `?`, build path with `${variable}` |

**Skills covered:** Multi-step correlation chain, 302 redirect handling, Location header extraction, mixed data sources (CSV + JMeter functions + correlation), timestamp validation, raw hash in URL (no key=value)

**Schedule payload (15+ fields from 3 sources):**

```json
{
  "assigneeId": 5,              // ← CSV test data
  "department": "Engineering",   // ← CSV test data
  "priority": "high",           // ← CSV test data
  "submittedAt": "2026-...",    // ← ${__time()} runtime function
  "scheduledDate": "2026-...",  // ← ${__timeShift()} runtime function
  "taskId": 42,                 // ← Correlated from step 2
  "projectCode": "PRJ-005",    // ← Correlated from step 3
  "_csrf": "abc123",           // ← Correlated from step 4
  "_formId": "f-98765"         // ← Correlated from step 4
}
```

---

### TC05: Batch Update - JS-Built Payload *
**Difficulty: Advanced**

Modeled after real grid/table update forms (student marks, bulk status changes). The JS-built payload challenge.

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | Login (TC01) | Prerequisite |
| 2 | `GET /api/tasks/batch-edit` | Extract task list + `_csrf` + `_formId` |
| 3 | `POST /api/tasks/batch-update` | `changesList` field contains URL-encoded JSON built by JS |

**The `changesList` payload** (what Fiddler shows, URL-decoded):

```json
{
  "1": {"ID": "task-101", "STS": "in_progress", "PRI": "high", "ASG": "3"},
  "2": {"ID": "task-102", "STS": "done", "PRI": "low", "ASG": "7"}
}
```

JS builds this from the table; JMeter has no JS engine. Requires **JSR223 PreProcessor (Groovy)** to dynamically construct the JSON from CSV data.

**Skills covered:** JSR223/Groovy scripting, dynamic payload construction, URL-encoded JSON in form fields, reverse-engineering payload format from Fiddler

---

### TC06: Registration with Email Verification
**Difficulty: Intermediate**

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | `GET /register` | Extract `_csrf` from hidden input |
| 2 | `POST /api/auth/register` | Response contains `verificationUrl` with token + hash |
| 3 | Parse `verificationUrl` | Nested extraction: JSON → URL string → query params (`token` and `hash`) |
| 4 | `GET /api/auth/verify?token=${token}&hash=${hash}` | **302 redirect** to `/login?verified=true` |
| 5 | `POST /api/auth/login` | Login with new credentials |

**Skills covered:** URL token extraction, nested extraction (JSON then RegEx), redirect handling, multi-step auth flow

---

### TC07: Password Reset
**Difficulty: Intermediate**

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | `POST /api/auth/forgot-password` | Response contains `resetUrl` with `?hash=...&expires=...` |
| 2 | `GET /api/auth/reset-password?hash=${hash}&expires=${expires}` | Extract `_csrf` and `resetToken` |
| 3 | `POST /api/auth/reset-password` | **302 redirect** to `/login?reset=success` |
| 4 | `POST /api/auth/login` | Login with new password |

**Skills covered:** URL hash extraction, expiry-based tokens, redirect handling, form token correlation

---

### TC08: Slow and Flaky Endpoints *
**Difficulty: Beginner (but important for load testing)**

| Endpoint | Behavior | Challenge |
|----------|----------|-----------|
| `GET /api/tasks/report?delay=2000` | Configurable response delay | Timeout settings, response time assertions |
| `GET /api/tasks/export` | Returns 500 randomly (~20%) | Error rate monitoring, retry logic |
| `POST /api/auth/login` (10+ requests/min) | Returns 429 | Rate limiting, pacing strategy |
| `GET /api/tasks?limit=1000` | Large JSON response | Response size impact, pagination vs bulk |
| `GET /api/reports/full-export` | Memory-intensive | Resource monitoring, server-side bottlenecks |

**Skills covered:** Timeout configuration, error assertions, rate limit handling, response size analysis, think time strategy

---

### TC09: Admin Panel - Cookie-Based Session *
**Difficulty: Beginner**

A separate admin section that uses traditional server-side sessions with cookies instead of JWT. This is how many real systems work - especially older or internal tools.

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | `GET /admin/login` | Returns `Set-Cookie: SESSIONID=...` + hidden `_csrf` |
| 2 | `POST /api/admin/auth/login` | Send credentials + `_csrf`, server sets session cookie |
| 3 | `GET /api/admin/users` | Cookie sent automatically by JMeter's HTTP Cookie Manager |
| 4 | `GET /api/admin/stats` | Session maintained across requests via cookie |
| 5 | `POST /api/admin/auth/logout` | Server invalidates session, cookie cleared |

**How it differs from JWT (TC01):**
- No `Authorization: Bearer <token>` header - cookies are sent automatically
- JMeter needs **HTTP Cookie Manager** (not HTTP Header Manager) to handle this
- Session is server-side (stored in Redis) - the cookie is just a reference
- No manual extraction needed if Cookie Manager is configured correctly

**Skills covered:** HTTP Cookie Manager, cookie-based auth, server-side sessions, contrast with token-based auth

---

### TC10: Bulk Export - Async Polling *
**Difficulty: Intermediate**

Submit a long-running job, poll until the server gives you a redirect link, then follow it. Modeled after real report generation systems where the server returns plain text progress, not JSON.

| Step | Request | Challenge |
|------|---------|-----------|
| 1 | Login (TC01) | Prerequisite |
| 2 | `POST /api/exports` with filters | Response: `202 Accepted` + `{ "jobId": "...", "statusUrl": "/api/exports/job-abc/status" }` |
| 3 | `GET /api/exports/${jobId}/status` | Response is **plain text**, not JSON (see below) |
| 4 | **Poll step 3** until response contains `@LNK` | JMeter **While Controller** + **RegEx Extractor** |
| 5 | `GET ${redirectUrl}` (extracted from poll response) | Follow the link to download the result |

**What the polling responses look like:**

During processing (Content-Type: `text/html`):
```
<OK>2/5
```

When complete — response contains `@LNK` followed by a redirect URL with a hash:
```
<OK>@LNK/api/exports/download/3D38F2E8DEBC4E47V6u9OLSwddi5R...
```

**Why this is harder than JSON polling:**
- **No JSON Extractor** — response is plain text, must use **RegEx Extractor**
- While Controller checks if response body contains `@LNK` (not a JSON field)
- The redirect URL after `@LNK` includes a long hash token — must extract with RegEx
- Content-Type says `text/html` but it's really a custom format — common in real systems

**Polling logic in JMeter:**
```
While Controller ("${exportResponse}" !contains "@LNK")
  ├── GET /api/exports/${jobId}/status
  ├── RegEx Extractor → exportResponse (full body)
  └── Constant Timer (2000ms between polls)

RegEx Extractor → redirectUrl (extract everything after @LNK)
GET ${redirectUrl}
```

**Skills covered:** While Controller, polling pattern, RegEx on plain text (not JSON), `@LNK` redirect extraction, text/html response handling, timer between polls

---

## Scenario-to-Skill Matrix

Which test case teaches which JMeter skill:

| JMeter Skill | TC01 | TC02 | TC03 | TC04 | TC05 | TC06 | TC07 | TC08 | TC09 | TC10 |
|-------------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| Embedded resources | x | | | | | | | | | |
| Hidden form inputs (`_csrf`, `_formId`) | x | | | x | x | x | x | | x | |
| JWT token correlation | x | x | x | x | x | x | x | | | x |
| CSV parameterization | | x | | x | x | | | | | |
| AJAX parallel requests | x | x | | | | | | | | |
| HTTP Header Manager | x | x | x | x | x | x | x | | | x |
| File upload (`multipart/form-data`) | | | x | | | | | | | |
| Multi-step chained correlation | | | x | x | | x | x | | | |
| 302 redirect / Location header | | | | x | | x | x | | | |
| `${__time()}` / runtime functions | | | | x | | | | | | |
| Heavy payload (mixed data sources) | | | | x | | | | | | |
| JSR223 Groovy scripting | | | | | x | | | | | |
| URL-encoded JSON in form field | | | | | x | | | | | |
| URL token/hash extraction | | | | x | | x | x | | | |
| Raw hash as query string (no key=value) | | | | x | | | | | | |
| Nested extraction (JSON → RegEx) | | | | | | x | x | | | |
| Timeout/error assertions | | | | | | | | x | | |
| Rate limiting / pacing | | | | | | | | x | | |
| Response size / pagination | x | | | | | | | x | | |
| Transaction Controller grouping | x | x | | x | | | | | | |
| Think time placement | x | x | | x | | | | | | x |
| HTTP Cookie Manager | | | | | | | | | x | |
| Cookie-based session (vs JWT) | | | | | | | | | x | |
| While Controller (polling) | | | | | | | | | | x |
| 202 Accepted / async pattern | | | | | | | | | | x |
| RegEx on plain text (non-JSON) | | | | | | | | | | x |
| `@LNK` redirect from text body | | | | | | | | | | x |

---

## Playwright Scenarios

Playwright-specific challenges that the app should support. These don't need dedicated JMeter TCs — they're UI automation concerns addressed during Phase 3 frontend build and documented in the Playwright knowledge base section later.

### Cross-User Approval Flow (E2E)

The main Playwright-specific scenario. Requires two browser contexts with different users.

| Step | Who | Action | Playwright Challenge |
|------|-----|--------|---------------------|
| 1 | User A (staff) | Login, create task, submit for review | Basic form + navigation |
| 2 | User B (manager) | Login (separate context), see pending task | Multi-context auth (`storageState`) |
| 3 | User B | Approve or reject with remarks | Cross-user state dependency |
| 4 | User A | Refresh, verify task status changed | Assert state change from another user's action |

**Playwright skills:** Multiple browser contexts, `storageState` for auth, cross-user assertions, test data coordination.

### UI Interaction Challenges

Features to build into the frontend that create Playwright testing scenarios:

| Feature | Where | Playwright Challenge |
|---------|-------|---------------------|
| Confirmation dialog | Delete task, reject task | `page.on('dialog')` or modal interaction |
| Toast notifications | After create/update/delete actions | Auto-dismiss timing, `waitForSelector` |
| Conditional form fields | Schedule form: fields change based on type selection | Dynamic element visibility, `waitFor` |
| Error states | Invalid form submission, 500 error page | Error message assertions, retry behavior |

### Roles for Playwright Testing

| Role | Users | Permissions |
|------|-------|-------------|
| Staff | `user01` - `user15` | Create tasks, submit for review, view own tasks |
| Manager | `user16` - `user19` | All staff permissions + approve/reject tasks |
| Admin | `admin` | Full access via cookie-based admin panel (TC09) |

---

## API Design

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user (returns `verificationUrl`) |
| POST | `/api/auth/login` | Login, returns JWT + refresh token |
| POST | `/api/auth/refresh` | Refresh expired JWT |
| POST | `/api/auth/logout` | Invalidate session |
| POST | `/api/auth/forgot-password` | Request reset (returns `resetUrl` with hash + expires) |
| GET | `/api/auth/reset-password` | Validate reset link, returns form tokens |
| POST | `/api/auth/reset-password` | Submit new password → **302** to `/login?reset=success` |
| GET | `/api/auth/verify` | Verify email → **302** to `/login?verified=true` |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks (`?status=`, `?search=`, `?page=`, `?limit=`) |
| GET | `/api/tasks/:id` | Get single task |
| POST | `/api/tasks` | Create task |
| PUT | `/api/tasks/:id` | Update task |
| DELETE | `/api/tasks/:id` | Delete task |
| POST | `/api/tasks/:id/comments` | Add comment |
| POST | `/api/tasks/:id/attachments` | Upload file → response includes `downloadUrl` |
| GET | `/api/tasks/:id/schedule` | Get schedule form (available slots + hidden tokens) |
| POST | `/api/tasks/:id/schedule` | Submit schedule → **302** to `/api/schedules/${confirmationId}/review` |
| GET | `/api/tasks/:id/schedules` | List existing schedules |
| POST | `/api/schedules/:confirmationId/confirm` | Confirm booking |
| GET | `/api/schedules/confirm?<hash>` | One-time link (raw hash, no key=value) |
| GET | `/api/tasks/batch-edit` | Load batch edit view (task list + tokens) |
| POST | `/api/tasks/batch-update` | Batch update (`changesList` = URL-encoded JSON) |
| PUT | `/api/tasks/:id/submit-review` | Submit task for review (staff → `pending_review`) |
| PUT | `/api/tasks/:id/approve` | Approve task (manager only → `approved`) |
| PUT | `/api/tasks/:id/reject` | Reject task with remarks (manager only → `rejected`) |
| GET | `/api/tasks?status=pending_review` | List tasks awaiting approval (manager view) |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List users (for dropdowns) |
| GET | `/api/users/me` | Current user profile |
| PUT | `/api/users/me` | Update profile |
| POST | `/api/users/me/avatar` | Upload avatar |

### Deliberate Test Scenarios (TC08)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/report` | Slow endpoint (configurable `?delay=`) |
| GET | `/api/tasks/export` | Flaky endpoint (random 500s) |
| GET | `/api/reports/full-export` | Memory-intensive export |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Task counts by status |
| GET | `/api/dashboard/recent` | Recent activity feed |

### Admin (Cookie-Based Session)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/login` | Admin login page (returns `Set-Cookie: SESSIONID=...`) |
| POST | `/api/admin/auth/login` | Admin login (session cookie auth, not JWT) |
| POST | `/api/admin/auth/logout` | Invalidate session |
| GET | `/api/admin/users` | List all users (requires valid session cookie) |
| GET | `/api/admin/stats` | System-wide stats (requires valid session cookie) |
| POST | `/api/admin/seed` | Reset DB to seeded state |
| GET | `/api/admin/health` | Health check |

### Exports (Async)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/exports` | Submit export job → `202 Accepted` + `{ jobId, statusUrl }` |
| GET | `/api/exports/:jobId/status` | Poll: returns `text/html` — `<OK>2/5` (in progress) or `<OK>@LNK<url>` (done) |
| GET | `/api/exports/download/:hash` | Download result (URL extracted from `@LNK` response) |

---

## Frontend Pages

| Page | URL | For JMeter | For Playwright |
|------|-----|-----------|----------------|
| Login | `/login` | Hidden `_csrf`, auth flow | Form validation, error messages |
| Register | `/register` | Hidden `_csrf`, registration flow | Form with validation rules |
| Dashboard | `/dashboard` | AJAX parallel calls on load | Charts, loading states |
| Task List | `/tasks` | Pagination, filtering, AJAX | Table sorting, filtering |
| Task Detail | `/tasks/:id` | 4 parallel AJAX calls | Comments, attachments |
| Schedule Task | `/tasks/:id/schedule` | Heavy form, hidden tokens | Date/time pickers, dropdowns |
| Batch Edit | `/tasks/batch-edit` | JS-built payload | Inline table editing |
| Create Task | `/tasks/new` | Form with hidden tokens, file upload | Form submission |
| Profile | `/profile` | Avatar upload | Edit form |
| Review Queue | `/tasks/review` | — | Manager approves/rejects (cross-user E2E) |
| Admin Login | `/admin/login` | Cookie-based session auth | Login form |
| Admin Dashboard | `/admin/dashboard` | Session cookie maintained across pages | User list, stats |

**Embedded resources** on all pages: images, CSS bundles, JS chunks, custom font (Inter), favicon, manifest.

**AJAX navigation:** After initial page load, all in-app navigation is AJAX (JSON API calls only, no full page reload). Backend enforces `Accept: application/json` and `X-Requested-With: XMLHttpRequest` headers.

---

## Seed Data

| Entity | Count | Notes |
|--------|-------|-------|
| Users (staff) | 15 | `user01` - `user15` / `password01` - `password15` (role: `staff`) |
| Users (manager) | 4 | `user16` - `user19` / `password16` - `password19` (role: `manager`) |
| Users (admin - JWT) | 1 | `user20` / `password20` (role: `manager`, also has JWT access) |
| Admin (cookie session) | 1 | `admin@taskflow.local` / `admin123` (admin panel only) |
| Tasks | 200 | Mixed statuses including `pending_review`, assigned to different users |
| Comments | 500 | Distributed across tasks |
| Attachments | 50 | Small placeholder files |
| Schedules | 100 | Pre-booked time slots |

---

## Docker Compose

### Local Domain Setup

The app uses an **nginx reverse proxy** so you access it via a local domain instead of `localhost:port`. This mimics real-world infrastructure where apps sit behind a reverse proxy.

**One-time setup** — add to your hosts file (`C:\Windows\System32\drivers\etc\hosts` on Windows, `/etc/hosts` on Linux/Mac):
```
127.0.0.1   taskflow.local
```

After that, access the app at `http://taskflow.local` — no port numbers needed.

### Services

| Service | Internal Port | Exposed Port | URL |
|---------|--------------|-------------|-----|
| `nginx` | 80 | **80** | `http://taskflow.local` |
| `frontend` | 5173 | — (internal only) | via nginx |
| `backend` | 4000 | **4000** | `http://taskflow.local/api/*` via nginx, or `localhost:4000` direct |
| `postgres` | 5432 | **5432** | Direct access for DB tools |
| `redis` | 6379 | **6379** | Direct access for debugging |

**Routing rules (nginx):**
- `taskflow.local/` → frontend (React app)
- `taskflow.local/api/*` → backend (Express API)
- `taskflow.local/admin/*` → backend (admin pages)

Backend port 4000 is also exposed directly for convenience during development/debugging, but JMeter and Playwright tests should go through nginx on port 80.

```bash
docker compose up -d
curl http://taskflow.local/api/admin/health
curl -X POST http://taskflow.local/api/admin/seed
open http://taskflow.local
```

---

## Directory Structure

```
playground/
├── PLAN.md
├── CLAUDE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── nginx/
│   └── nginx.conf           # Reverse proxy config (taskflow.local → frontend/backend)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   └── public/              # Static assets (images, fonts, favicon)
├── backend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── index.ts
│   │   ├── routes/
│   │   ├── middleware/      # Auth, CSRF, rate limiting
│   │   ├── models/
│   │   ├── services/
│   │   ├── seed/
│   │   └── config/
│   └── tests/
├── db/
│   └── init.sql
└── scripts/
    ├── seed-data.sh
    └── health-check.sh
```

---

## Build Phases

### Phase 1: Foundation (MVP)
- [ ] Docker Compose with PostgreSQL + Redis + Nginx reverse proxy
- [ ] Nginx config: `taskflow.local` → frontend, `taskflow.local/api/*` → backend
- [ ] Backend: Express app with health check
- [ ] Backend: Auth endpoints (register, login, JWT)
- [ ] Backend: Task CRUD endpoints
- [ ] User roles (staff, manager) with role-based permissions
- [ ] Database schema and seed script (with roles in user data)
- [ ] CSRF middleware + `_csrf` / `_formId` hidden token generation
- **Covers:** TC01, TC02
- **Goal:** JMeter can test login, browse, create task

### Phase 2: Full API
- [ ] File upload (attachments + avatar)
- [ ] Task scheduling with heavy payload + timestamp validation
- [ ] Schedule confirmation flow with 302 redirect + one-time raw hash link
- [ ] Batch update endpoint (`changesList` URL-encoded JSON)
- [ ] Task approval workflow (submit-review, approve, reject with remarks)
- [ ] Auth flows: email verification, password reset (with URL tokens + redirects)
- [ ] Deliberate test scenarios (slow, flaky, rate-limited endpoints)
- [ ] Admin cookie-based session auth (Redis session store, `Set-Cookie`, login/logout)
- [ ] Async export endpoints (POST → 202, poll status, download when complete)
- [ ] Admin seed/reset endpoint
- **Covers:** TC03, TC04, TC05, TC06, TC07, TC08, TC09, TC10 + Playwright approval flow
- **Goal:** All JMeter test cases + cross-user approval flow executable against the API

### Phase 3: Frontend
- [ ] React app with Vite
- [ ] All pages (login, register, dashboard, task list, detail, schedule, batch edit, profile)
- [ ] Admin pages (admin login, admin dashboard) - cookie-based auth
- [ ] Review queue page (`/tasks/review`) - manager approval interface
- [ ] Embedded resources: images, custom font, favicon, manifest
- [ ] JS-built `changesList` payload on batch edit page
- [ ] Hidden form inputs rendered in HTML
- [ ] AJAX navigation between pages
- [ ] Playwright-specific UI features:
  - [ ] Confirmation dialog on delete / reject actions
  - [ ] Toast notifications with auto-dismiss (success, error)
  - [ ] Conditional form fields (show/hide based on dropdown selection)
  - [ ] Error states (invalid form submission, error pages)
- **Covers:** All TCs with full browser recording, Playwright automation
- **Goal:** Complete recording and automation target

### Phase 4: Polish
- [ ] Error pages (404, 500)
- [ ] Responsive layout (mobile vs desktop)
- [ ] Documentation: setup guide, API reference
- **Goal:** Production-quality test target

---

## JMeter Documentation (Separate)

> The JMeter-specific guidance (Groovy scripts, extractor techniques, step-by-step JMeter configuration) will live in `jmeter/docs/15-playground-scenarios.md`, not in this plan. This plan defines **what the app does**. The JMeter docs explain **how to test it**.

---

## Design Principles

1. **One flow, one set of challenges** - Not everything in every flow; each TC targets specific skills
2. **Predictable data** - Seeded data is deterministic so tests are repeatable
3. **Easy reset** - `POST /api/admin/seed` resets to known state
4. **Self-contained** - No external dependencies, everything runs in Docker
5. **Progressive difficulty** - TC01-TC02, TC08-TC09 (beginner) → TC03, TC06-TC07, TC10 (intermediate) → TC04-TC05 (advanced)

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation (MVP) | Not Started |
| 2 | Full API | Not Started |
| 3 | Frontend | Not Started |
| 4 | Polish | Not Started |
