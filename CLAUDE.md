# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Testing Knowledge Base** — a practical, hands-on documentation project covering software testing tools and methodologies. The content is authored collaboratively with the repository owner and reflects their personal approach, not generic textbook material.

The long-term goal is to cover multiple testing disciplines (performance testing, UI automation, load testing) with a shared Docker-based playground application for hands-on practice.

## Repository Structure

```
testing-knowledge-base/
├── README.md              ← Root navigation
├── CLAUDE.md              ← This file (repo-wide instructions)
├── .github/workflows/     ← CI/CD (GitHub Actions)
├── jmeter/                ← JMeter performance testing docs (active)
├── jmeter-working-dir/    ← JMeter project + webapp
│   ├── webapp/            ← FastAPI test dashboard (198 tests, CI/CD)
│   ├── test_plan/         ← JMeter test plans (.jmx)
│   ├── test_data/         ← CSV test data
│   ├── results/           ← JTL logs and HTML reports
│   ├── config/            ← VM and test configuration
│   ├── ssh_key/           ← SSH keys for OCI slave access
│   └── setup-linux-slave.sh ← Automated OCI slave setup script
├── playwright/            ← UI automation testing (planned)
├── k6/                    ← Load testing (planned)
└── playground/            ← Docker-based target app (planned)
```

Each topic folder has its own `CLAUDE.md`, `PLAN.md`, and `README.md` with tool-specific instructions.

## Webapp

The JMeter Test Dashboard (`jmeter-working-dir/webapp/`) is a FastAPI web app for managing performance tests. See `webapp/CLAUDE.md` for full details. Key facts:

- **198 tests** across 8 test files (56% code coverage)
- **CI/CD**: GitHub Actions triggers on push/PR to `jmeter-working-dir/webapp/**`
- **Access control**: Token-based auth (localhost=admin, remote=token, viewer=read-only)
- **Distributed testing**: Supports OCI Linux slaves + local slaves (see docs 12 & 15)
- Run with: `cd jmeter-working-dir/webapp && pip install -r requirements.txt && python -m webapp`

## Content Conventions (All Topics)

- Each doc file has a **Table of Contents** at the top using anchor links
- Screenshots are marked with `<!-- TODO: Screenshot - description -->` where not yet captured
- Sections follow: **Why** (context) → **How** (steps) → **Tips** (lessons learned)
- The tone is practical and first-person ("my approach"), not academic
- Doc files are numbered for ordering (e.g., `01-`, `02-`)

## Hosting

- Currently hosted on **GitHub** (personal): https://github.com/Dhawi1902/testing-knowledge-base
- Long-term target is **GitLab** for team consumption
