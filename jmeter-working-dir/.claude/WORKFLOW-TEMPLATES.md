# Claude Code Workflow Templates (ECC Edition)

Quick-reference for working with Everything Claude Code (ECC) and installed plugins. Skills auto-trigger based on what you say — no slash commands needed.

---

## Quick Reference

| I want to... | Say something like... | Skills that activate |
|---|---|---|
| Plan a feature | "I want to add [feature]. Plan only." | brainstorming → writing-plans |
| Build a feature | "Implement [feature]. Follow existing patterns." | executing-plans, feature-dev, search-first |
| Fix a bug | "This is broken: [symptoms]. Debug it." | systematic-debugging |
| Write tests first | "Add [feature] using TDD." | test-driven-development, python-testing |
| Review my changes | "Review my recent changes." | requesting-code-review, python-review |
| Build UI | "Build a [page/component]. Make it polished." | frontend-design, frontend-patterns |
| Test in browser | "Open [URL] and verify [behavior]." | e2e (Playwright) |
| Update docs | "Audit CLAUDE.md files." / "What did we learn?" | claude-md-management, learn-eval |
| Check security | "Check this for security issues." | security-review, security-scan |
| Parallel tasks | "Do X, Y, and Z independently." | dispatching-parallel-agents |

---

## 1. Planning & Design

**When:** Starting a new feature, redesigning a page, or making architectural decisions.

**What happens:** Brainstorming asks clarifying questions one at a time, proposes 2-3 approaches, then writes a design doc. Once approved, writing-plans creates a step-by-step implementation plan.

**Say this:**
```
I want to add [feature description].
Constraints: [tech stack, patterns, boundaries].
Plan only — don't code yet.
```

```
I'm thinking about redesigning [page/component].
Here's what's wrong with the current approach: [problems].
What are my options?
```

**With library docs lookup (also triggers context7):**
```
I want to add [feature] using [library].
First, look up the latest [library] docs for [specific API].
Then plan the implementation. Don't code yet.
```

**Skill chain:** `brainstorming` → `writing-plans` → saves to `docs/plans/YYYY-MM-DD-<topic>-design.md`

---

## 2. Feature Implementation

**When:** You have a plan (or a clear enough task) and want to build it.

**What happens:** Searches for existing patterns first, then implements following codebase conventions. For multi-step plans, uses parallel agents for independent tasks.

**Say this:**
```
Implement [feature description].
Context: [where it fits, what it connects to].
Run tests after.
```

```
Execute the plan in docs/plans/[plan-file].
```

**For independent subtasks (triggers parallel agents):**
```
Implement these independently:
1. Add the new API endpoint in routers/
2. Add the service logic in services/
3. Add the frontend JS and template
```

**Key skills:** `executing-plans`, `feature-dev`, `search-first`, `backend-patterns`, `python-patterns`, `api-design`

---

## 3. Bug Fixing & Debugging

**When:** Something is broken and you need to find the root cause.

**What happens:** Systematic debugging follows a structured process — reproduce, hypothesize, verify. It won't jump to a fix before understanding the problem.

**Say this:**
```
This is broken: [describe symptoms].
Expected: [what should happen].
Actual: [what happens instead].
```

```
The [page/endpoint] returns [error].
I see this in the logs: [log output].
Debug it.
```

**Key skills:** `systematic-debugging`

---

## 4. TDD & Testing

**When:** Adding new features or fixing bugs — write tests first.

**What happens:** Writes a failing test (RED), implements just enough to pass (GREEN), then refactors (IMPROVE). Targets 80%+ coverage.

**Say this:**
```
Add [feature] using TDD.
Write the test first, then implement.
```

```
Write tests for [module/endpoint].
Cover the happy path and edge cases.
```

**For E2E test generation:**
```
Generate E2E tests for the [page name] page.
Cover: [list of user flows].
```

**Key skills:** `test-driven-development`, `python-testing`, `e2e-testing`

**Test command:** `python -m pytest tests/ -v --tb=short --cov=routers --cov=services --cov=main --cov-report=term-missing`

---

## 5. Code Review

**When:** After writing code, before committing.

**What happens:** Reviews for bugs, security, quality, and Python-specific patterns. Flags issues by severity (CRITICAL, HIGH, MEDIUM).

**Say this:**
```
Review my recent changes.
Focus on [bugs / security / performance / conventions].
```

```
Review the last [N] commits.
```

**After receiving review feedback:**
```
Address the review findings. Fix CRITICAL and HIGH issues.
```

**Key skills:** `requesting-code-review`, `python-review`, `security-review`

---

## 6. UI/Frontend Work

**When:** Building or redesigning pages and components for the webapp.

**What happens:** Creates production-grade, responsive UI following the existing design system (CSS tokens, Lucide icons, light/dark themes).

**Say this:**
```
Build a [page/component description].
Follow the existing design system in style.css.
Make it responsive and polished.
```

```
Redesign the [page] to look more like [reference].
Keep the existing functionality, improve the layout.
```

**Key skills:** `frontend-design`, `frontend-patterns`

**Design system:** CSS tokens in `static/css/style.css`, Lucide icons via `templates/icons.html`, dark/light themes

---

## 7. E2E Testing

**When:** Verifying user flows in the browser.

**What happens:** Launches a browser, navigates pages, interacts with elements, takes screenshots, and verifies behavior.

**Say this:**
```
Open http://localhost:8080 and take a screenshot.
Check if [expected behavior] is working.
```

```
Navigate to [page], click [element], fill in [form],
and verify [expected result]. Screenshot each step.
```

**Key skills:** `e2e` (Playwright)

**Screenshot location:** `webapp/tests/e2e/screenshots/`

---

## 8. Documentation & Learning

**When:** Updating project docs or capturing patterns from a session.

**What happens:** Audits CLAUDE.md files for accuracy, or extracts reusable patterns from the current session into skills/instincts.

**Say this:**
```
Audit all CLAUDE.md files in this repo.
Fix anything outdated or missing.
```

```
What patterns did we learn from this session?
Save anything reusable.
```

```
Check my ECC instincts. What have I learned so far?
```

**Key skills:** `claude-md-management`, `learn-eval`, `continuous-learning-v2`, `instinct-status`

---

## 9. Verification & Completion

**When:** About to call something "done" — before committing or creating a PR.

**What happens:** Runs a final check that tests pass, no regressions, security is clean, and the code matches what was requested.

**Say this:**
```
I think this is done. Verify everything before I commit.
```

```
Run the full verification — tests, security, code quality.
```

**Key skills:** `verification-before-completion`, `verification-loop`, `security-scan`

---

## Combining Workflows

Chain workflows naturally by describing what you want end-to-end:

### Full Cycle (Plan → Build → Review → Verify)
```
I want to [feature description].
1. Plan the approach first — wait for my approval
2. Look up any library docs you need
3. Implement using TDD
4. Review your own changes for bugs and security
5. Run full verification
```

### Debug → Fix → Test → Review
```
[Bug description].
Find the root cause, fix it with a test, then review the fix.
```

### Design → Build UI → E2E Test
```
I want to redesign [page].
1. Plan the layout changes
2. Build it with polished design
3. Take a browser screenshot to verify
4. Generate E2E tests for the new layout
```

---

## Skill Reference

All available ECC skills grouped by category. These activate automatically — listed here for reference only.

### Process (superpowers)

| Skill | Triggers when you... |
|---|---|
| `brainstorming` | Start creative work, new features |
| `writing-plans` | Have a spec that needs a step-by-step plan |
| `executing-plans` | Have a written plan to execute |
| `systematic-debugging` | Encounter bugs or unexpected behavior |
| `test-driven-development` | Want tests before implementation |
| `dispatching-parallel-agents` | Have 2+ independent tasks |
| `requesting-code-review` | Want your code reviewed |
| `receiving-code-review` | Get review feedback to address |
| `verification-before-completion` | Are about to claim work is done |
| `finishing-a-development-branch` | Need to merge/integrate completed work |
| `strategic-compact` | Hit context limits on long sessions |

### Domain (everything-claude-code)

| Skill | Purpose |
|---|---|
| `plan` | Create implementation plans |
| `tdd` | Enforce TDD workflow |
| `python-review` | Python-specific code review |
| `python-testing` | pytest strategies, fixtures, mocking |
| `python-patterns` | Pythonic idioms, PEP 8 |
| `backend-patterns` | API design, server-side architecture |
| `api-design` | REST conventions, status codes, pagination |
| `frontend-patterns` | UI development patterns |
| `e2e` | Generate and run Playwright tests |
| `e2e-testing` | Playwright patterns and config |
| `security-review` | Check for vulnerabilities |
| `security-scan` | Scan .claude/ config for issues |
| `search-first` | Research before coding |
| `coding-standards` | Universal code quality standards |
| `verification-loop` | Comprehensive verification system |
| `learn-eval` | Extract patterns from sessions |
| `continuous-learning-v2` | Instinct-based learning system |
| `instinct-status` | View learned instincts |
| `skill-create` | Create skills from git history |

### Plugins (non-ECC)

| Plugin | Purpose |
|---|---|
| `feature-dev` | Guided feature dev with architecture focus |
| `frontend-design` | Production-grade UI creation |
| `code-review` | PR and code review |
| `context7` | Live library docs lookup |
| `playwright` | Browser automation and screenshots |
| `ralph-loop` | Agentic loops for complex multi-step work |
| `claude-md-management` | Audit and improve CLAUDE.md files |

---

## Tips

- **Be specific about scope** — "add pagination to /results" beats "improve the app"
- **Name constraints** — "no new dependencies", "keep it under 50 lines"
- **Say "plan only"** to get design approval before any code is written
- **Say "run tests after"** to auto-validate changes
- **Mention library names** to trigger context7 docs lookup
- **Say "take a screenshot"** to trigger Playwright verification
- **Describe independent tasks** as a numbered list to trigger parallel agents
- **Say "what did we learn"** at the end of a session to capture patterns
