# LoadLitmus Version Roadmap Design

> **For Claude:** This is a vision document, not an implementation plan. Use `superpowers:writing-plans` to create implementation plans for individual versions.

**Goal:** Evolve LoadLitmus from a functional internal tool to a polished, open-source, multi-tool performance testing dashboard distributed as a standalone executable.

**Current state:** v0.4 — functional app, 313 tests (55% coverage), security hardening complete, no packaging infrastructure.

**Distribution:** Standalone `.exe` (Windows) + binary (Linux) via PyInstaller

**Audience:** Open source — public GitHub release at v1.0

**Multi-tool:** Post v1.0 — plugin architecture for k6, Gatling, Locust

---

## Pre-release (Private Repository)

### v0.5 — Packageable

**Theme:** Make the app installable and distributable as a standalone executable.

| # | Item | Detail |
|---|------|--------|
| 1 | `pyproject.toml` | Package metadata, entry point (`loadlitmus` CLI command), separate `[dev]` dependencies |
| 2 | `webapp/__version__.py` | Single source of truth: `__version__ = "0.5.0"` |
| 3 | `--version` flag | `python -m webapp --version` prints version and exits |
| 4 | Split dependencies | Runtime deps in `pyproject.toml`, test deps in `[project.optional-dependencies.dev]` |
| 5 | PyInstaller spec | `loadlitmus.spec` — bundles templates, static, config into single exe |
| 6 | Build script | `scripts/build.py` or Makefile — builds exe for current platform |
| 7 | Smoke test | Built exe starts, serves `/`, returns 200 |
| 8 | `.gitignore` update | Ignore `dist/`, `build/`, `*.spec` artifacts |

---

### v0.6 — Reliable

**Theme:** Fix deferred findings from the hardening evaluation and raise test coverage to 80%.

| # | Item | Detail |
|---|------|--------|
| 1 | SSH `AutoAddPolicy` fix | Replace with `RejectPolicy` + known_hosts file, warn on unknown host |
| 2 | SSH credential management | Move passwords out of `vm_config.json` to environment variables or `.env` file (gitignored) |
| 3 | Rate limiting on `/login` | Add `slowapi` middleware — 5 attempts per minute per IP |
| 4 | Split `slaves.py` (812 lines) | Break into `ssh.py` (SSH operations), `provisioning.py` (setup/clean), `slaves.py` (status/config) |
| 5 | Deduplicate disk walks | Cache directory scans in results/test_data routers — don't walk the same tree twice per request |
| 6 | Clean up dead code | Remove `previous_summary` parameter, unused JMeter version glob |
| 7 | Frontend perf | Cache `getComputedStyle` in FleetChart, consolidate spacing utilities |
| 8 | Test coverage to 80% | Write tests for untested services (slaves SSH, process_manager, data generation) |
| 9 | Integration tests | Add tests that exercise full workflows (upload CSV, distribute, verify) |

---

### v0.7 — Polished

**Theme:** Make the app approachable for someone who has never seen it before.

| # | Item | Detail |
|---|------|--------|
| 1 | Public README.md | Feature overview, screenshots, quick start, requirements (JMeter, Python or standalone exe) |
| 2 | Setup wizard improvements | First-run wizard detects JMeter path, validates project structure, shows clear errors |
| 3 | Error UX | User-friendly error pages (404, 500) instead of raw JSON. Toast messages for common failures |
| 4 | In-app help | Tooltips on key fields (what is ramp-up? what is think time?), link to docs |
| 5 | LICENSE file | MIT or Apache 2.0 (permissive, good for tools) |
| 6 | CONTRIBUTING.md | How to set up dev environment, run tests, submit PRs |
| 7 | Configuration docs | Document all settings.json and project.json fields with examples |
| 8 | Graceful degradation | App works without JMeter installed (dashboard, results viewing still functional) |

---

### v0.8 — Observable

**Theme:** Give users and operators visibility into what the app is doing.

| # | Item | Detail |
|---|------|--------|
| 1 | `/api/health` endpoint | Returns JSON with app status, uptime, version, JMeter detected, disk space |
| 2 | `/api/version` endpoint | Returns `{"version": "0.8.0", "python": "3.13", "platform": "win32"}` |
| 3 | Structured logging | JSON log format option (machine-parseable) alongside human-readable |
| 4 | Startup banner | Print version, platform, Python version, JMeter path (or "not found") on launch |
| 5 | Test run history | Persist run metadata (start time, duration, thread count, error rate) to `config/run_history.json` |
| 6 | Export metrics | Optional InfluxDB/Prometheus push for test run results (uses existing monitoring config) |
| 7 | Built-in heuristics | Rule-based analysis — no AI needed: error rate thresholds, p95 vs avg flags, throughput drop alerts |
| 8 | Result retention policy | Auto-archive or auto-delete old results after N days, configurable in settings |

---

### v0.9 — Battle-tested

**Theme:** Prove the app works across environments and get real feedback before v1.0.

| # | Item | Detail |
|---|------|--------|
| 1 | CI build pipeline | GitHub Actions builds exe for Windows + Linux on every tag push |
| 2 | Cross-platform testing | CI runs test suite on both Windows and Ubuntu |
| 3 | E2E smoke tests | Playwright tests: launch app, navigate all pages, verify no crashes |
| 4 | Beta release | GitHub Release (private repo) with `.exe` + Linux binary attached |
| 5 | Install/upgrade guide | Step-by-step: download exe, place in project dir, run, open browser |
| 6 | Migration guide | For existing users: how to move from `python -m webapp` to standalone exe |
| 7 | Bug bash | Hammer the exe on real projects, file issues |
| 8 | Edge cases | Test with: no JMeter, empty project, huge JTL files, no network (offline slaves) |

---

### v1.0 — Stable Release

**Theme:** The public launch. Everything works, is documented, and has a quality guarantee.

| # | Item | Detail |
|---|------|--------|
| 1 | CHANGELOG.md | Document all changes from v0.5 to v1.0 (Keep a Changelog format) |
| 2 | Semantic versioning contract | Public API stability promise — breaking changes only in major versions |
| 3 | GitHub Release | Tagged `v1.0.0`, release notes, Windows exe + Linux binary attached |
| 4 | Open source the repo | Make repo public, add badges (CI status, version, license) to README |
| 5 | Landing section in README | One-paragraph pitch, feature list, screenshot, quick start |
| 6 | Bug fix process | Issue templates, PR template, triage labels |
| 7 | Security policy | `SECURITY.md` — how to report vulnerabilities responsibly |

---

## Post-release (Public Repository)

### v1.1 — Mixed Fleet

**Theme:** Support Windows machines as JMeter slaves alongside Linux.

| # | Item | Detail |
|---|------|--------|
| 1 | Windows slave connection | WinRM + SSH (OpenSSH on Windows), auto-detect which is available |
| 2 | OS detection | Detect and display OS per slave (Windows/Linux icon in fleet UI) |
| 3 | PowerShell provisioning | Windows-equivalent of `setup-linux-slave.sh` |
| 4 | Path handling | Handle `\` vs `/`, `.bat` vs `.sh` per slave OS |
| 5 | Per-slave OS config | `"os": "windows"` or `"os": "linux"` in slaves.json |

---

### v1.2 — CI/CD + Sharing

**Theme:** Integrate with CI/CD pipelines and enable project sharing.

| # | Item | Detail |
|---|------|--------|
| 1 | Headless CLI mode | `loadlitmus run --plan test.jmx --threads 100` — no browser needed |
| 2 | Exit codes | Pass/fail based on configurable thresholds |
| 3 | Threshold gates | Define pass/fail criteria (avg RT < 2s, error rate < 1%, p95 < 5s) |
| 4 | JSON summary output | Machine-readable result summary for pipeline parsing |
| 5 | Pipeline examples | GitHub Actions, GitLab CI, Jenkins pipeline snippets |
| 6 | Notifications | Webhook support (Telegram, Discord, Slack) — "test finished" alerts |
| 7 | Project import/export | Package project (JMX, CSV, config, settings) as `.zip` for sharing |

---

### v1.3 — AI Providers

**Theme:** Abstract AI integration to support multiple providers.

| # | Item | Detail |
|---|------|--------|
| 1 | `AnalysisProvider` interface | Base class: `analyze()`, `summarize()`, `suggest()` |
| 2 | `OllamaProvider` | Current Ollama integration refactored into provider pattern |
| 3 | `OpenAIProvider` | OpenAI API backend (user provides their own key) |
| 4 | `ClaudeProvider` | Anthropic API backend (user provides their own key) |
| 5 | Provider selection in Settings | Choose provider, configure API key, test connection |

**Design principle:** App is fully useful with zero AI. Built-in heuristics (v0.8) cover common cases. AI enhances but is never required.

---

### v1.4 — Smart Analysis + Multi-project

**Theme:** AI-powered insights and local multi-project support.

| # | Item | Detail |
|---|------|--------|
| 1 | Anomaly detection | Auto-flag unusual patterns: spikes, stepped degradation, error cascades |
| 2 | Test plan suggestions | "No think time between requests — this isn't realistic" |
| 3 | Report summarization | Human-readable summary from JTL data for non-technical stakeholders |
| 4 | Baseline comparison | "p95 is 30% higher than your last 5 runs" |
| 5 | Capacity prediction | "System will likely hit its limit at ~800 concurrent users" |
| 6 | Multi-project (local) | Project switcher in sidebar, each project has own plans/data/results/slaves |

---

### v1.5 — Reporting

**Theme:** Generate shareable reports from test results.

| # | Item | Detail |
|---|------|--------|
| 1 | PDF export | One-click: summary stats, charts, pass/fail, top errors |
| 2 | Markdown export | Paste-friendly for Confluence, GitLab wiki, GitHub issues |
| 3 | Comparison report | Side-by-side "Run A vs Run B" as downloadable document |
| 4 | Trend report | "Last 10 runs" performance trends |
| 5 | Executive summary | Non-technical one-pager for management |
| 6 | Custom templates | User-defined sections, company logo |

---

### v1.6 — Visual Test Editor

**Theme:** Web-based test plan editor — no JMeter GUI needed.

| # | Item | Detail |
|---|------|--------|
| 1 | Visual flow builder | Drag-and-drop test plan creation in the browser |
| 2 | JMX import/export | Read existing JMX files, save edits back to JMX |
| 3 | Simplified model | Focus on common elements: HTTP requests, loops, timers, assertions |
| 4 | Parameter extraction | Visual correlation — click a response to extract a variable |
| 5 | Tool-agnostic design | Editor built to support non-JMX formats in v2.0 |

---

### v2.0 — Multi-tool

**Theme:** Support multiple performance testing tools through a plugin architecture.

| # | Item | Detail |
|---|------|--------|
| 1 | `ToolAdapter` interface | Base class: `parse_results()`, `build_command()`, `get_parameters()` |
| 2 | JMeter adapter | Extract current JMeter-specific code into first adapter |
| 3 | k6 adapter | Run k6 scripts, parse JSON results, generate summaries |
| 4 | Generic results format | Normalize results across tools into common schema |
| 5 | Tool auto-detection | Detect installed tools, show relevant UI |
| 6 | Per-project tool config | `project.json` declares which tool(s) the project uses |
| 7 | Editor multi-format | Visual editor exports to JMX, k6 JS, etc. |

---

### v2.1+ — More Tools

| Version | Tool | Detail |
|---------|------|--------|
| v2.1 | Gatling | Scala simulation support |
| v2.2 | Locust | Python load test support |
| v2.3 | Cross-tool comparison | Run same scenario in JMeter vs k6, compare results |

---

### v3.0 — Agent Architecture

**Theme:** Remote agents for multi-environment management.

| # | Item | Detail |
|---|------|--------|
| 1 | Agent service | Lightweight Python service — runner + slave management |
| 2 | Controller dashboard | "Environments" page — manage all remote agents from one UI |
| 3 | Agent communication | REST API + WebSocket for log streaming between controller and agents |
| 4 | Multi-environment | Manage PREP, staging, production from one dashboard |
| 5 | Agent auto-update | Controller pushes updates to remote agents |

---

### v3.1 — Team Features

| # | Item | Detail |
|---|------|--------|
| 1 | Shared projects | Multiple users access same project via agents |
| 2 | Role-based access | Admin, tester, viewer roles across agents |
| 3 | Audit log | Who ran what, when, with what parameters |

---

### v3.2 — Cloud Provisioning

| # | Item | Detail |
|---|------|--------|
| 1 | Cloud VM provisioning | Auto-deploy agents + slaves to AWS/OCI/Azure |
| 2 | Auto-scaling | Spin up slaves based on thread count requirements |
| 3 | Cost tracking | Estimate and track cloud costs per test run |

---

## Design Principles (All Versions)

1. **Works without AI** — built-in heuristics cover common cases, AI enhances but is never required
2. **Works without JMeter** — dashboard, results viewing, and analysis functional without JMeter installed
3. **No database** — file-based architecture through v1.x at minimum
4. **English only** — no i18n planned
5. **Per-project deployment** through v1.3, multi-project from v1.4
6. **Backward compatible** within major versions (semver from v1.0)
7. **Standalone first** — exe distribution is primary, `pip install` is secondary
