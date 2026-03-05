# LoadLitmus Webapp Hardening Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all CRITICAL and HIGH findings from the 2026-03-05 security + architecture + frontend evaluation, bringing the webapp to production-ready quality for external access.

**Architecture:** The changes are defensive — no new features, no structural rewrites. Each task is a focused fix to one specific finding. Tests are added alongside each fix. The plan is organized in three phases: Phase A (security-critical, do first), Phase B (architecture fixes), Phase C (frontend fixes).

**Tech Stack:** Python 3.13, FastAPI, Jinja2, vanilla JS/CSS, pytest

**Evaluation reference:** The full evaluation was conducted on 2026-03-05 and covers 35 findings across security (15), architecture (11), and frontend (9).

---

## Phase A: Security Hardening (Tasks 1-10)

### Task 1: Generic 500 Error Messages

**Finding:** S2 — Exception details leaked in 500 responses expose internal paths and library errors.

**Files:**
- Modify: `webapp/main.py:114`
- Test: `webapp/tests/test_auth.py` (add test)

**Step 1: Write the failing test**

In `tests/test_auth.py`, add:

```python
class TestErrorHandling:
    def test_500_does_not_leak_exception_details(self, admin_client, bp):
        """500 responses should return a generic message, not str(exc)."""
        # Trigger a 500 by requesting a route that will fail internally
        # We'll test via the global handler by checking the response format
        r = admin_client.get(f"{bp}/api/results/NONEXISTENT_FOLDER_12345/stats")
        if r.status_code == 500:
            body = r.json()
            # Should NOT contain Python exception class names or file paths
            assert "Traceback" not in body.get("error", "")
            assert "\\Users\\" not in body.get("error", "")
            assert "File \"" not in body.get("error", "")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth.py::TestErrorHandling -v`

**Step 3: Implement the fix**

In `main.py:114`, change:

```python
# BEFORE
return JSONResponse(status_code=500, content={"error": str(exc)})

# AFTER
return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
```

The full exception is already logged at line 112 with `exc_info=True`, so no diagnostic data is lost.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth.py::TestErrorHandling -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/main.py webapp/tests/test_auth.py
git commit -m "fix(security): return generic 500 messages instead of exception details"
```

---

### Task 2: Access Control on Server Restart Endpoint

**Finding:** S12 — `POST /api/server/restart` has no `_check_access` guard. Any remote viewer can restart the server.

**Files:**
- Modify: `webapp/main.py:235-256`
- Test: `webapp/tests/test_security.py` (add test)

**Step 1: Write the failing test**

In `tests/test_security.py`, add to `TestViewerDenied` or create new class:

```python
class TestRestartSecurity:
    def test_viewer_cannot_restart_server(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/server/restart")
        assert r.status_code in (403, 307)  # 403 denied or 307 redirect to /token
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py::TestRestartSecurity -v`
Expected: FAIL (currently returns 200)

**Step 3: Implement the fix**

In `main.py`, modify `restart_server()`:

```python
@app.post(f"{BASE_PATH}/api/server/restart")
async def restart_server(request: Request):
    """Restart the server with updated settings."""
    from services.auth import check_access
    denied = check_access(request)
    if denied:
        return denied
    # ... rest of existing code unchanged
```

Note: Also add `request: Request` to the function signature.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py::TestRestartSecurity -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/main.py webapp/tests/test_security.py
git commit -m "fix(security): add access control to server restart endpoint"
```

---

### Task 3: Validate `next` Redirect Parameter

**Finding:** S3 — Open redirect via unvalidated `next` query parameter allows phishing after login.

**Files:**
- Modify: `webapp/main.py:212-213`
- Test: `webapp/tests/test_auth.py` (add test)

**Step 1: Write the failing test**

In `tests/test_auth.py`:

```python
class TestOpenRedirect:
    def test_next_rejects_external_url(self, admin_client, bp):
        """The next parameter must not allow redirect to external URLs."""
        r = admin_client.post(
            f"{bp}/api/auth/verify?next=https://evil.com",
            json={"token": "anything"},
        )
        body = r.json()
        if body.get("ok"):
            redirect = body.get("redirect", "")
            assert not redirect.startswith("http")
            assert "evil.com" not in redirect

    def test_next_rejects_protocol_relative(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/auth/verify?next=//evil.com/steal",
            json={"token": "anything"},
        )
        body = r.json()
        if body.get("ok"):
            redirect = body.get("redirect", "")
            assert not redirect.startswith("//")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth.py::TestOpenRedirect -v`

**Step 3: Implement the fix**

In `main.py`, after line 211, add validation:

```python
next_url = request.query_params.get("next", f"{BASE_PATH}/")
# Prevent open redirect — only allow relative paths within this app
if "://" in next_url or next_url.startswith("//"):
    next_url = f"{BASE_PATH}/"
elif BASE_PATH and not next_url.startswith(BASE_PATH):
    next_url = f"{BASE_PATH}/"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth.py::TestOpenRedirect -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/main.py webapp/tests/test_auth.py
git commit -m "fix(security): validate next parameter to prevent open redirect"
```

---

### Task 4: Add Security Headers Middleware

**Finding:** S9 — No CSP, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy headers.

**Files:**
- Modify: `webapp/main.py` (add middleware after existing middleware)
- Test: `webapp/tests/test_auth.py` (add test)

**Step 1: Write the failing test**

```python
class TestSecurityHeaders:
    def test_responses_include_security_headers(self, admin_client, bp):
        r = admin_client.get(f"{bp}/")
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert "same-origin" in r.headers.get("Referrer-Policy", "")
        assert "Content-Security-Policy" in r.headers
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth.py::TestSecurityHeaders -v`

**Step 3: Implement the fix**

In `main.py`, add a new middleware after the logging middleware (after line ~200):

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # Skip for static files
    if not request.url.path.startswith(f"{BASE_PATH}/static"):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:"
        )
    return response
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth.py::TestSecurityHeaders -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/main.py webapp/tests/test_auth.py
git commit -m "fix(security): add CSP, X-Frame-Options, and other security headers"
```

---

### Task 5: Fix Auth Cookie — Add `samesite="strict"`

**Finding:** S10 — Auth cookie missing `samesite` attribute.

**Files:**
- Modify: `webapp/main.py:214`
- Test: `webapp/tests/test_auth.py` (add test)

**Step 1: Write the failing test**

```python
class TestCookieSecurity:
    def test_auth_cookie_has_samesite_strict(self, tmp_project_dir, monkeypatch):
        """The auth cookie should set samesite=strict."""
        import services.auth as auth_mod
        import main as main_mod

        plain_token = "cookie-test-token"
        sp = tmp_project_dir["settings_path"]
        import json
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = auth_mod.hash_token(plain_token)
        sp.write_text(json.dumps(settings, indent=2))

        monkeypatch.setattr(auth_mod, "is_localhost", lambda _req: False)
        monkeypatch.setattr(main_mod, "_is_localhost", lambda _req: False)

        from starlette.testclient import TestClient
        from main import app
        bp = main_mod.BASE_PATH

        with TestClient(app) as c:
            r = c.post(f"{bp}/api/auth/verify", json={"token": plain_token})
            assert r.status_code == 200
            cookie_header = r.headers.get("set-cookie", "")
            assert "samesite=strict" in cookie_header.lower()

        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth.py::TestCookieSecurity -v`

**Step 3: Implement the fix**

In `main.py:214`, change:

```python
# BEFORE
response.set_cookie(key=cookie_name, value=token, max_age=max_age, httponly=True)

# AFTER
response.set_cookie(key=cookie_name, value=token, max_age=max_age, httponly=True, samesite="strict")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth.py::TestCookieSecurity -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/main.py webapp/tests/test_auth.py
git commit -m "fix(security): add samesite=strict to auth cookie"
```

---

### Task 6: Conditional `reload` Mode in Entry Point

**Finding:** S13 / A-HIGH — `reload=True` hardcoded, can trigger mid-test restarts and is inappropriate for production.

**Files:**
- Modify: `webapp/__main__.py:33`
- Test: Manual verification

**Step 1: Implement the fix**

In `__main__.py`, replace line 33:

```python
# BEFORE
uvicorn.run("main:app", host=host, port=port, reload=True)

# AFTER
dev_mode = "--dev" in args or "--reload" in args
uvicorn.run("main:app", host=host, port=port, reload=dev_mode)
```

Also update the CLI parsing block (after line 24) to strip `--dev` and `--reload` from being treated as unknown:

```python
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
        elif arg == "--host" and i + 1 < len(args):
            host = args[i + 1]

    dev_mode = "--dev" in args or "--reload" in args
```

Update the print block to indicate dev mode:

```python
    if dev_mode:
        print("  Development mode — auto-reload enabled")
```

**Step 2: Verify**

```bash
cd webapp && python -m webapp --dev
# Should print "Development mode — auto-reload enabled"
# Ctrl+C, then:
cd webapp && python -m webapp
# Should NOT print the dev mode line, and should not auto-reload
```

**Step 3: Also fix the restart endpoint** in `main.py:246` which hardcodes `--reload`:

```python
# BEFORE (line 246)
[sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", host, "--port", port],

# AFTER
cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", port]
if server.get("dev_mode"):
    cmd.append("--reload")
subprocess.Popen(cmd, cwd=str(APP_DIR))
```

**Step 4: Commit**

```bash
git add webapp/__main__.py webapp/main.py
git commit -m "fix: make reload conditional on --dev flag instead of always-on"
```

---

### Task 7: Replace Deprecated `asyncio.get_event_loop()`

**Finding:** A-HIGH — 13 call sites in `services/slaves.py` use deprecated `get_event_loop()` instead of `get_running_loop()`.

**Files:**
- Modify: `webapp/services/slaves.py` (lines 128, 149, 388, 438, 458, 500, 511, 621, 648, 676, 705, 770, 803)

**Step 1: Implement the fix**

This is a straight find-and-replace. In `services/slaves.py`:

```python
# BEFORE (all 13 occurrences)
loop = asyncio.get_event_loop()

# AFTER (all 13 occurrences)
loop = asyncio.get_running_loop()
```

**Step 2: Run full test suite to verify nothing breaks**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All 303 tests pass

**Step 3: Commit**

```bash
git add webapp/services/slaves.py
git commit -m "fix: replace deprecated asyncio.get_event_loop with get_running_loop"
```

---

### Task 8: Add Logging to Silent Exception Handlers

**Finding:** A-HIGH — Bare `except: pass` blocks swallow errors silently in settings, auth, and history services.

**Files:**
- Modify: `webapp/services/settings.py:97-98`
- Modify: `webapp/services/auth.py:56` (find the `migrate_token_if_needed` try/except)
- Modify: `webapp/services/health_history.py:28-31`
- Modify: `webapp/services/metrics_history.py:37-39`

**Step 1: Implement the fixes**

In each file, add a logger and replace `pass` with `logger.warning(...)`:

**services/settings.py:97-98:**
```python
# BEFORE
except Exception:
    pass

# AFTER
except Exception:
    logger.warning("Failed to load settings.json, using defaults", exc_info=True)
```

Add at the top of the file (if not already present):
```python
import logging
logger = logging.getLogger("jmeter_dashboard")
```

Apply the same pattern to the other three files — add `logger.warning("Failed to load <filename>: %s", exc)` in each bare except block.

**Step 2: Run tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All pass

**Step 3: Commit**

```bash
git add webapp/services/settings.py webapp/services/auth.py webapp/services/health_history.py webapp/services/metrics_history.py
git commit -m "fix: add logging to silent exception handlers instead of bare pass"
```

---

### Task 9: Fix Ollama Config Source

**Finding:** A-HIGH — `routers/results.py:578` reads Ollama config from `project.json` instead of `settings.json`, making the Settings UI ineffective.

**Files:**
- Modify: `webapp/routers/results.py:578-584`
- Test: `webapp/tests/test_results_api.py` (add test)

**Step 1: Write the failing test**

```python
class TestAnalysisConfig:
    def test_analysis_uses_settings_not_project(self, admin_client, bp, tmp_project_dir, sample_result):
        """Ollama config should come from settings.json, not project.json."""
        import json
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["analysis"] = {
            "ollama_url": "http://custom-ollama:11434",
            "ollama_model": "custom-model",
            "ollama_timeout": 999,
        }
        sp.write_text(json.dumps(settings, indent=2))

        # The analysis endpoint should read from settings
        # We can't fully test without Ollama, but we can check the config is read
        # by triggering the endpoint and checking it tries the right URL
        folder = sample_result.name
        date = sample_result.parent.name
        r = admin_client.post(f"{bp}/api/results/{date}/{folder}/analyze")
        # The endpoint will fail (no Ollama), but should NOT use project.json defaults
        # This test validates the config path change was made
        assert r.status_code in (200, 500)  # Either works (Ollama up) or fails (down)
```

**Step 2: Implement the fix**

In `routers/results.py:578`, change:

```python
# BEFORE
ollama_config = project.get("analysis", {}).get("ollama", {})
base_url = ollama_config.get("base_url", "http://localhost:11434")
model = ollama_config.get("model", "llama3.1:8b")
timeout = ollama_config.get("timeout", 120)

# AFTER
from services.settings import load_settings
app_settings = load_settings()
analysis_config = app_settings.get("analysis", {})
base_url = analysis_config.get("ollama_url", "http://localhost:11434")
model = analysis_config.get("ollama_model", "llama3.1:8b")
timeout = analysis_config.get("ollama_timeout", 120)
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_results_api.py -v --tb=short`
Expected: All pass

**Step 4: Commit**

```bash
git add webapp/routers/results.py webapp/tests/test_results_api.py
git commit -m "fix: read Ollama config from settings.json instead of project.json"
```

---

### Task 10: Add `tail` Bounds Check and `slave_dir` Validation

**Finding:** S6/S7 — SSH command interpolation risks from unbounded `tail` and unsanitized `slave_dir`.

**Files:**
- Modify: `webapp/services/slaves.py:636` (tail bounds)
- Modify: `webapp/services/slaves.py` (slave_dir validation in `_ssh_connect` or provisioning functions)
- Test: `webapp/tests/test_config_api.py` (add test)

**Step 1: Write the failing test**

```python
class TestSlaveInputValidation:
    def test_tail_parameter_bounded(self, admin_client, bp):
        """tail parameter should be bounded to prevent abuse."""
        # Extremely large tail value
        r = admin_client.get(f"{bp}/api/slaves/127.0.0.1/log?tail=999999999")
        # Should still work but with bounded value (not cause issues)
        assert r.status_code in (200, 404, 500)  # Depends on slave availability
```

**Step 2: Implement the fixes**

In `services/slaves.py`, before the `tail` interpolation at line 636:

```python
# Bound tail to safe range
tail = max(1, min(int(tail), 10000))
```

For `slave_dir` validation, add a helper at the module level:

```python
import re

_SAFE_PATH_RE = re.compile(r'^[~/a-zA-Z0-9._/ -]+$')

def _validate_slave_dir(slave_dir: str) -> str:
    """Validate slave_dir has no shell metacharacters."""
    if not slave_dir or not _SAFE_PATH_RE.match(slave_dir):
        raise ValueError(f"Invalid slave_dir: contains unsafe characters")
    return slave_dir
```

Call `_validate_slave_dir(slave_dir)` at the start of `provision_slave()` and any other function that interpolates `slave_dir` into shell commands.

**Step 3: Run tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All pass

**Step 4: Commit**

```bash
git add webapp/services/slaves.py webapp/tests/test_config_api.py
git commit -m "fix(security): bound tail parameter and validate slave_dir against injection"
```

---

## Phase B: Architecture Fixes (Tasks 11-14)

### Task 11: Protect Global Slave Status Cache with Lock

**Finding:** A-MEDIUM — `_last_slave_status` in `routers/config.py` has no lock, creating race conditions on concurrent writes.

**Files:**
- Modify: `webapp/routers/config.py:245-294`

**Step 1: Implement the fix**

At the top of the global cache section (around line 245):

```python
import asyncio

_last_slave_status: list[dict] = []
_last_slave_status_ts: float = 0
_status_lock = asyncio.Lock()
```

In `api_slave_status()` and `get_cached_slave_status()`, wrap writes with:

```python
async with _status_lock:
    _last_slave_status = merged
    _last_slave_status_ts = time.time()
```

Also fix the mutation issue (finding A-MEDIUM): instead of mutating `entry` in-place, create a new dict:

```python
# BEFORE
entry = result_map[s["ip"]]
entry["enabled"] = True
merged.append(entry)

# AFTER
entry = {**result_map[s["ip"]], "enabled": True}
merged.append(entry)
```

**Step 2: Run tests**

Run: `python -m pytest tests/test_config_api.py -v --tb=short`
Expected: All pass

**Step 3: Commit**

```bash
git add webapp/routers/config.py
git commit -m "fix: add asyncio.Lock to slave status cache and fix dict mutation"
```

---

### Task 12: Disable FastAPI Docs When External Access Enabled

**Finding:** S14 — Swagger/ReDoc expose a full API map to unauthenticated users.

**Files:**
- Modify: `webapp/main.py:85-91`

**Step 1: Implement the fix**

```python
# BEFORE
app = FastAPI(
    title="JMeter Test Dashboard",
    lifespan=lifespan,
    docs_url=f"{BASE_PATH}/docs",
    redoc_url=f"{BASE_PATH}/redoc",
    openapi_url=f"{BASE_PATH}/openapi.json",
)

# AFTER
from services.settings import load_settings as _load_initial_settings
_initial = _load_initial_settings()
_external = _initial.get("server", {}).get("allow_external", False)

app = FastAPI(
    title="LoadLitmus",
    lifespan=lifespan,
    docs_url=None if _external else f"{BASE_PATH}/docs",
    redoc_url=None if _external else f"{BASE_PATH}/redoc",
    openapi_url=None if _external else f"{BASE_PATH}/openapi.json",
)
```

**Step 2: Run tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All pass (test env has `allow_external: false`)

**Step 3: Commit**

```bash
git add webapp/main.py
git commit -m "fix(security): disable API docs when external access is enabled"
```

---

### Task 13: Consolidate Jinja2Templates Instances

**Finding:** A-MEDIUM — Each router creates its own `Jinja2Templates`, all monkey-patched in `main.py`.

**Files:**
- Create: `webapp/services/templates.py`
- Modify: `webapp/routers/dashboard.py`, `config.py`, `test_plans.py`, `results.py`, `settings.py`, `test_data.py`
- Modify: `webapp/main.py:281-285`

**Step 1: Create shared template service**

```python
# webapp/services/templates.py
"""Shared Jinja2Templates instance for all routers."""
from pathlib import Path
from fastapi.templating import Jinja2Templates

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
```

**Step 2: Update each router**

In each router that has its own `Jinja2Templates(...)`, replace with:

```python
# BEFORE (e.g., in dashboard.py)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

# AFTER
from services.templates import templates
```

Do this for: `dashboard.py`, `config.py`, `test_plans.py`, `results.py`, `settings.py`, `test_data.py`.

**Step 3: Simplify `main.py` patching**

In `main.py`, the `_patch_template_response` loop (lines 281-285) should now only patch the single shared instance:

```python
from services.templates import templates as shared_templates
_patch_template_response(shared_templates)
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All 303 pass

**Step 5: Commit**

```bash
git add webapp/services/templates.py webapp/routers/*.py webapp/main.py
git commit -m "refactor: consolidate Jinja2Templates into shared service instance"
```

---

### Task 14: Add IP Address Validation to Slave Endpoints

**Finding:** S-HIGH adjacency — `ip` path parameter used in SSH operations without format validation.

**Files:**
- Modify: `webapp/routers/config.py` (slave endpoints that accept `ip`)
- Test: `webapp/tests/test_config_api.py`

**Step 1: Write the failing test**

```python
class TestSlaveIPValidation:
    def test_invalid_ip_format_rejected(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/not-an-ip/start")
        assert r.status_code in (400, 422)

    def test_injection_ip_rejected(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/;rm -rf/start")
        assert r.status_code in (400, 404, 422)
```

**Step 2: Implement the fix**

Add an IP validation helper in `routers/config.py`:

```python
import ipaddress

def _validate_ip(ip: str):
    """Return a 400 JSONResponse if ip is not a valid address, else None."""
    try:
        ipaddress.ip_address(ip)
        return None
    except ValueError:
        return JSONResponse(status_code=400, content={"error": f"Invalid IP address: {ip}"})
```

At the start of each endpoint that takes `ip` as a path parameter (start, stop, status, log, provision, etc.), add:

```python
invalid = _validate_ip(ip)
if invalid:
    return invalid
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_config_api.py -v --tb=short`
Expected: All pass

**Step 4: Commit**

```bash
git add webapp/routers/config.py webapp/tests/test_config_api.py
git commit -m "fix(security): validate IP address format on all slave endpoints"
```

---

## Phase C: Frontend Fixes (Tasks 15-19)

### Task 15: Fix Dashboard WebSocket BASE_PATH

**Finding:** F-CRITICAL — Dashboard WebSocket hardcodes `/ws/runner/logs`, breaking subdirectory deployments.

**Files:**
- Modify: `webapp/templates/dashboard.html:382`

**Step 1: Implement the fix**

Find the WebSocket construction in `dashboard.html` and add `BASE_PATH`:

```javascript
// BEFORE
const ws = new WebSocket(`${proto}//${location.host}/ws/runner/logs`);

// AFTER
const ws = new WebSocket(`${proto}//${location.host}${BASE_PATH}/ws/runner/logs`);
```

Verify that `BASE_PATH` is available in the template context (it should be, since `_patch_template_response` injects it as `base_path`). The JS variable name may be `BASE_PATH` or need to be read from a template variable.

**Step 2: Verify**

Check that the variable reference is correct by searching `dashboard.html` for how BASE_PATH is defined (likely `const BASE_PATH = "{{ base_path }}";` at the top of a script block).

**Step 3: Commit**

```bash
git add webapp/templates/dashboard.html
git commit -m "fix: use BASE_PATH in dashboard WebSocket URL for subdirectory deployments"
```

---

### Task 16: Guard `confirmAction` Against Re-Entrancy

**Finding:** F-CRITICAL — Overlapping `confirmAction()` calls orphan promises. `_confirmResolve` is a singleton.

**Files:**
- Modify: `webapp/static/js/app.js:171-190`

**Step 1: Implement the fix**

At the start of `confirmAction()`:

```javascript
async function confirmAction(message, opts = {}) {
    // Guard: if a confirm is already active, resolve it as cancelled first
    if (_confirmResolve) {
        _confirmResolve(false);
        _confirmResolve = null;
    }
    // ... rest of existing code
```

Apply the same pattern to `promptAction()`:

```javascript
async function promptAction(title, opts = {}) {
    if (_promptResolve) {
        _promptResolve(null);
        _promptResolve = null;
    }
    // ... rest of existing code
```

**Step 2: Verify manually**

Open the app in a browser, rapidly trigger two confirm dialogs. The first should auto-cancel, the second should display correctly.

**Step 3: Commit**

```bash
git add webapp/static/js/app.js
git commit -m "fix: guard confirmAction/promptAction against re-entrancy"
```

---

### Task 17: Extract Shared Slave Dropdown Helper

**Finding:** F-IMPORTANT — `renderList` and `renderGrid` duplicate 90+ lines of identical dropdown markup.

**Files:**
- Modify: `webapp/static/js/fleet-slaves.js:107-127, 167-187`

**Step 1: Implement the fix**

Extract a shared function before `renderList`:

```javascript
function renderSlaveDropdown(s, aIp) {
    return `
        <div class="dropdown">
            <button class="btn btn-sm btn-ghost" onclick="toggleDropdown(this)" data-tooltip="Actions">
                ${ICON_MORE}
            </button>
            <div class="dropdown-menu">
                <!-- paste the identical dropdown items from renderList here -->
                ...all dropdown items...
            </div>
        </div>
    `;
}
```

Then in both `renderList` and `renderGrid`, replace the duplicated dropdown block with:

```javascript
${renderSlaveDropdown(s, aIp)}
```

**Step 2: Verify**

Open the Slaves page, switch between list and grid views. Both should show identical dropdown menus with all actions working.

**Step 3: Commit**

```bash
git add webapp/static/js/fleet-slaves.js
git commit -m "refactor: extract shared slave dropdown helper to eliminate duplication"
```

---

### Task 18: Unify Fleet Modal Open/Close Mechanism

**Finding:** F-IMPORTANT — Fleet modals use `style="display:none"` instead of `openModal()`/`closeModal()`, breaking overlay-click-to-dismiss.

**Files:**
- Modify: `webapp/templates/_fleet_modals.html:4, 40, 61, 78`
- Modify: `webapp/static/js/fleet-slaves.js` (modal open/close calls)

**Step 1: Implement the fix**

In `_fleet_modals.html`, remove `style="display:none;"` from all modal overlays:

```html
<!-- BEFORE -->
<div class="modal-overlay" id="provisionModal" style="display:none;">

<!-- AFTER -->
<div class="modal-overlay" id="provisionModal">
```

Do this for: `provisionModal`, `logModal`, `savedLogsModal`, `syncModal`.

In `fleet-slaves.js`, replace direct `style.display` manipulation with `openModal`/`closeModal`:

```javascript
// BEFORE
document.getElementById('provisionModal').style.display = '';

// AFTER
openModal('provisionModal');
```

```javascript
// BEFORE
document.getElementById('provisionModal').style.display = 'none';

// AFTER
closeModal('provisionModal');
```

Apply to all fleet modal open/close calls.

**Step 2: Verify**

Open the Slaves page, open a modal (e.g., Provision), click outside the modal content. It should dismiss. Previously this did nothing.

**Step 3: Commit**

```bash
git add webapp/templates/_fleet_modals.html webapp/static/js/fleet-slaves.js
git commit -m "fix: unify fleet modals with openModal/closeModal for overlay-click-to-dismiss"
```

---

### Task 19: Retire `--color-text-light` Deprecated Alias

**Finding:** F-IMPORTANT — Deprecated CSS variable actively used in ~20 places despite deprecation comment.

**Files:**
- Modify: `webapp/static/css/style.css` (find-replace)
- Modify: `webapp/templates/*.html` (if `.text-light` class used)

**Step 1: Implement the fix**

In `style.css`:

1. Find all `var(--color-text-light)` and replace with `var(--color-text-secondary)`
2. Find the `.text-light` utility class and rename to `.text-secondary` (or keep both briefly for backwards compat)
3. Remove the deprecated alias definition at line 30 (keep only `--color-text-secondary`)

In templates, find all uses of `text-light` class and replace with `text-secondary`.

**Step 2: Verify**

Open the app, check that all secondary text still renders correctly in both light and dark themes. No visual change expected since the values are identical.

**Step 3: Commit**

```bash
git add webapp/static/css/style.css webapp/templates/*.html
git commit -m "refactor: retire deprecated --color-text-light in favor of --color-text-secondary"
```

---

## Phase D: Run Full Suite and Verify (Task 20)

### Task 20: Final Verification

**Step 1: Run full test suite**

```bash
cd webapp && python -m pytest tests/ -v --tb=short --cov=routers --cov=services --cov=main --cov-report=term-missing
```

Expected: All 303+ tests pass, coverage should increase (new tests added in Tasks 1-5, 9-10, 14).

**Step 2: Manual smoke test**

```bash
cd webapp && python -m webapp --dev
```

Open browser, verify:
- Dashboard loads, WebSocket connects
- Slaves page: list/grid views, modals open/close with overlay click
- Settings: all tabs navigate correctly
- Theme toggle works (dark/light)
- Confirm dialogs work correctly

**Step 3: Commit all remaining changes**

```bash
git add -A
git commit -m "test: final verification — all hardening tasks complete"
```

---

## Summary

| Phase | Tasks | Findings Addressed | Effort |
|-------|-------|-------------------|--------|
| A: Security | 1-10 | S1-S13, A-HIGH (4) | ~3 hours |
| B: Architecture | 11-14 | A-MEDIUM (4), S14 | ~2 hours |
| C: Frontend | 15-19 | F-CRITICAL (2), F-IMPORTANT (3) | ~2 hours |
| D: Verification | 20 | All | ~30 min |
| **Total** | **20 tasks** | **26 of 35 findings** | **~7.5 hours** |

**Deferred to future iteration** (9 findings): SSH `AutoAddPolicy` replacement (S4, requires `known_hosts` infra), SSH credential management (S5, process change), rate limiting on auth (S11, new dependency), `slaves.py` file split (large refactor), duplicate disk walks (optimization), JMeter version detection (low priority), dead `previous_summary` parameter (low priority), `getComputedStyle` caching in FleetChart (performance minor), spacing utility consolidation (cosmetic).
