# Design: Workflow Templates ECC Rewrite

**Date:** 2026-03-05
**Status:** Implemented

## Problem

The existing WORKFLOW-TEMPLATES.md was plugin-centric — organized around which plugin to use, with slash commands as the primary interaction. After installing ECC (Everything Claude Code), the template needed restructuring to leverage the full ECC skill ecosystem.

## Decision

**Option chosen: ECC-first rewrite** — restructure around workflows, not tools. Natural language triggers instead of slash commands. Non-ECC plugins kept only where ECC doesn't cover them.

## Design

### Structure
1. **Quick-reference table** — maps situations to natural language triggers and auto-activated skills
2. **9 workflow sections** — Planning, Implementation, Debugging, TDD, Code Review, UI, E2E, Docs, Verification
3. **Combining workflows** — chained examples for full-cycle work
4. **Skill reference** — grouped by category (superpowers, domain, plugins) for lookup

### Key changes from old template
- Workflow-centric instead of plugin-centric
- Natural language triggers instead of slash commands
- Added debugging, TDD, verification, and learning workflows (not in old version)
- Project-specific examples (FastAPI, pytest, CSS design system)
- Skill reference table at the bottom for all ECC + plugin skills

### Dropped from old template
- `code-simplifier` as a standalone section (folded into code review)
- Explicit slash command usage as primary interaction
- Generic prompts (replaced with project-relevant examples)
