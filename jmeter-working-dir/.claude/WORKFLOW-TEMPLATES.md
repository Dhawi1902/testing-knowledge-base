# Claude Code Workflow Templates

You are a senior, experienced software engineer. Always apply best practices including clean code principles, SOLID design, proper error handling, security awareness, and industry-standard patterns. Write production-quality code — never cut corners.

Quick-reference templates to get the best out of your installed plugins.

## Installed Plugins

| Plugin | What It Does | Auto-Triggers When You... |
|---|---|---|
| **code-review** | Reviews PRs for bugs, security, quality | Ask to review code/PR/changes |
| **feature-dev** | Plans architecture + builds features | Ask to add/implement a feature |
| **frontend-design** | Creates polished, production-grade UI | Ask to build pages/components |
| **code-simplifier** | Refactors for clarity and maintainability | Ask to clean up/simplify code |
| **context7** | Fetches live library docs and examples | Ask about a library/framework API |
| **playwright** | Browser automation and testing | Ask to test UI, take screenshots |
| **ralph-loop** | Runs agentic loops for complex tasks | Use `/ralph-loop` for multi-step work |
| **claude-md-management** | Audits and improves CLAUDE.md files | Ask to check/improve CLAUDE.md |

---

## 1. Code Review

**Plugin used:** `code-review`, `code-simplifier`

### Quick Review
```
Review the last [N] commits. Focus on [bugs / security / performance / conventions].
```

### PR Review
```
Review PR #[number]. Flag any security issues and logic errors.
```

### Review + Simplify
```
Review my recent changes, then simplify any code that's overly complex.
```

---

## 2. Planning

**Plugin used:** `feature-dev` (architecture phase)

### Plan a Feature
```
I want to [describe feature].
Constraints: [tech stack, patterns, boundaries].
Plan only — don't write code yet.
```

### Plan with Docs Lookup
```
I want to add [feature] using [library].
First, look up the latest [library] docs for [specific API/concept].
Then plan the implementation. Don't code yet.
```
> This triggers **context7** for docs + **feature-dev** for planning.

### Explore Before Planning
```
I'm not sure how [area of codebase] works.
Explore it and explain the architecture, then propose how to add [feature].
```

---

## 3. Development

**Plugin used:** `feature-dev`, `context7`, `code-simplifier`

### Build a Feature
```
Implement [feature description].
Context: [where it fits, what it connects to].
Run tests after.
```

### Build with Docs Reference
```
Add [feature] using [library/framework].
Look up the latest [library] docs if needed.
Follow existing patterns in the codebase.
Run tests after.
```

### Build a Frontend Page
```
Build a [page/component description].
Style: [modern, minimal, dashboard, etc.].
Make it responsive and polished.
```
> This triggers **frontend-design** for high-quality UI output.

---

## 4. Full Cycle (Plan → Build → Review)

**Plugins used:** `feature-dev` → `context7` → `code-simplifier` → `code-review`

### Standard Full Cycle
```
I want to [feature description].
1. Plan the approach first — wait for my approval
2. Look up any library docs you need
3. Implement it following existing patterns
4. Simplify anything overly complex
5. Review your own changes for bugs and security
6. Run tests
```

### Full Cycle with UI
```
I want to [UI feature description].
1. Plan the architecture
2. Build it with polished frontend design
3. Review the code
4. Take a browser screenshot to verify the result
5. Run tests
```
> This triggers **feature-dev** → **frontend-design** → **code-review** → **playwright**

---

## 5. Testing & Verification

**Plugin used:** `playwright`, `context7`

### Visual Verification
```
Open [URL] in the browser and take a screenshot.
Check if [expected behavior] is working.
```

### Browser Testing
```
Navigate to [URL], click [element], fill in [form fields],
and verify [expected result]. Take screenshots at each step.
```

### Look Up Test Library Docs
```
Look up the latest [pytest / playwright / jmeter] docs for [topic].
Show me examples of [specific pattern].
```

---

## 6. Maintenance

**Plugin used:** `claude-md-management`, `code-simplifier`

### Audit Project Docs
```
Audit all CLAUDE.md files in this repo. Improve anything outdated or missing.
```

### Clean Up Code
```
Review [file/folder] and simplify for readability.
Don't change behavior — just clean it up.
```

---

## Tips for Best Results

- **Be specific about scope** — "add pagination to /results" > "improve the app"
- **Name constraints** — "no new dependencies", "keep it under 50 lines"
- **Say "plan only"** when you want to approve before coding starts
- **Say "run tests after"** to auto-validate changes
- **Mention the library name** to trigger context7 docs lookup
- **Say "take a screenshot"** to trigger playwright verification
- **Chain steps with numbered lists** to run a full pipeline
