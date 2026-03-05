# UI/UX Redesign — Session Prompts

Run these sessions **in order** (each builds on the previous).

---

## Session 1: Design System Foundation (Tasks 1-4)

```
Read the implementation plan at docs/plans/2026-02-26-uiux-redesign-plan.md and the design doc at docs/plans/2026-02-26-uiux-redesign-design.md.

Execute Tasks 1 through 4 from the plan using the executing-plans skill. These are:

- Task 1: CSS Token Refresh — colors, typography scale, spacing utilities, grid helpers, radius tokens
- Task 2: Lucide Icon System — create icons.html with 33+ SVG macros, add .icon CSS
- Task 3: Replace Navigation Icons — swap Unicode chars for Lucide SVGs in sidebar + bottom nav
- Task 4: Theme Toggle in Topbar — add sun/moon toggle, remove theme from Settings

Important context:
- The webapp is at jmeter-working-dir/webapp/
- Run tests with: cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q
- Commit after each task
- The CSS file is at webapp/static/css/style.css (927 lines)
- The base template is at webapp/templates/base.html (88 lines)
- The JS is at webapp/static/js/app.js (238 lines)
- After all 4 tasks, verify the app runs: cd jmeter-working-dir/webapp && python -m webapp
```

---

## Session 2: Interaction Components (Tasks 5-9)

```
Read the implementation plan at docs/plans/2026-02-26-uiux-redesign-plan.md.

Execute Tasks 5 through 9 from the plan using the executing-plans skill. These are:

- Task 5: Styled Confirm Modal — replace all 16 window.confirm() calls with async styled modal
- Task 6: Styled Prompt Modal — replace all 4 window.prompt() calls with input modal + validation
- Task 7: Loading Skeletons & Empty States — add skeleton placeholders and empty states to all data pages
- Task 8: Dropdown Menu Component — reusable click-triggered dropdown for action overflow
- Task 9: Tooltip Component — CSS-only tooltips via data-tooltip attribute

Important context:
- Session 1 has already been completed (CSS tokens, icons, nav, theme toggle are in place)
- The confirm modal change (Task 5) is the biggest — confirmAction becomes async/Promise-based, so every call site needs `await` and the containing function needs `async`
- There are 16 confirmAction calls across 6 templates and 4 prompt() calls across 4 templates — the plan has exact line numbers but they may have shifted from Session 1 changes, so search for the actual patterns
- Run tests with: cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q
- Commit after each task
```

---

## Session 3: Page Polish — Dashboard, Plans, Results (Tasks 10-12)

```
Read the implementation plan at docs/plans/2026-02-26-uiux-redesign-plan.md and the design doc at docs/plans/2026-02-26-uiux-redesign-design.md.

Execute Tasks 10 through 12 from the plan using the executing-plans skill. These are:

- Task 10: Dashboard Polish — replace inline grid styles with utilities, add icons, information hierarchy, empty state, bring monitoring cards into .card system
- Task 11: Test Plans & Runner Polish — code preview styling, stat card color tints, Lucide icons on buttons, keyboard shortcut tooltip on Run button
- Task 12: Results Page — convert 5 action buttons to Stats + Report visible + 3-dot dropdown for rest, contextual delete confirm, loading skeleton, compare styling

Important context:
- Sessions 1-2 are complete — all design system components are available (Lucide icons via {{ icon('name', size) }}, styled confirm/prompt modals, dropdowns, tooltips, skeletons, empty states, spacing utilities)
- Read the current state of each template before modifying — line numbers in the plan may have shifted
- The icon macro is imported in base.html and available in all templates: {{ icon('name', size) }}
- Use the new CSS utility classes (.grid-2, .grid-3, .mt-16, .mb-8, .gap-16, etc.) to replace inline styles
- Use data-tooltip="hint text" for tooltips
- For the Results dropdown (Task 12), use the dropdown component: .dropdown > button.btn-icon(onclick=toggleDropdown(this)) + .dropdown-menu > .dropdown-item elements
- Run tests after each task: cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q
- Commit after each task
```

---

## Session 4: Page Polish — Data, Fleet, Settings, Final (Tasks 13-17)

```
Read the implementation plan at docs/plans/2026-02-26-uiux-redesign-plan.md and the design doc at docs/plans/2026-02-26-uiux-redesign-design.md.

Execute Tasks 13 through 17 from the plan using the executing-plans skill. These are:

- Task 13: Test Data Polish — preview zebra striping, column type icons, distribute progress, remove inline styles
- Task 14: Fleet Page Polish — visible config toggle (not hidden opacity), accordion chevrons, status text labels, sticky bulk action bar, empty state
- Task 15: Settings Page — consolidate to single Save button with sticky footer, unsaved changes dot indicator on tabs, system info cards into .surface-card, tab icons
- Task 16: Final Consistency Pass — audit remaining inline styles, fix .btn-close, verify all modal footers use .modal-footer, dark mode check, mobile check, run full test suite
- Task 17: Update CLAUDE.md and PHASE_PLAN.md — document icon system, new interaction components, utility classes, theme toggle location

Important context:
- Sessions 1-3 are complete — design system and Dashboard/Plans/Results are already polished
- Read the current state of each template before modifying — line numbers will have shifted significantly
- For Task 15 (Settings single Save): the current settings.html has two save buttons — one in card header and one in Report tab. Consolidate to a sticky footer bar. Track unsaved changes by adding `input`/`change` event listeners that add a .has-changes class to the tab button
- For Task 16: search for remaining style=" attributes and convert the layout/spacing ones to utility classes. Some style="display:none" for JS visibility toggles are fine to keep.
- For Task 17: update webapp/CLAUDE.md Component Library table, add sections on icon system and interaction components
- Run tests after each task: cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q
- After Task 17, run the full test suite with coverage to confirm nothing broke:
  python -m pytest tests/ -v --tb=short --cov=routers --cov=services --cov=main --cov-report=term-missing
```

---

## Review Checkpoints

After each session, visually verify by running the app:

```bash
cd jmeter-working-dir/webapp && python -m webapp
```

Then open http://localhost:8080 and check:
- **After Session 1:** Sidebar has Lucide icons, theme toggle works in topbar, colors look refined in both light/dark
- **After Session 2:** Delete a result → styled modal appears (not browser dialog). Add a slave → styled input modal. Empty pages show empty states.
- **After Session 3:** Dashboard has clear hierarchy. Results use dropdown for overflow actions. Plans show keyboard shortcut hint.
- **After Session 4:** All pages polished. Settings has single save. No inline style clutter. Dark mode consistent everywhere.
