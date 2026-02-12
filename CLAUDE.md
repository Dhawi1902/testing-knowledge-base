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
├── jmeter/                ← JMeter performance testing (active)
├── playwright/            ← UI automation testing (planned)
├── k6/                    ← Load testing (planned)
└── playground/            ← Docker-based target app (planned)
```

Each topic folder has its own `CLAUDE.md`, `PLAN.md`, and `README.md` with tool-specific instructions.

## Content Conventions (All Topics)

- Each doc file has a **Table of Contents** at the top using anchor links
- Screenshots are marked with `<!-- TODO: Screenshot - description -->` where not yet captured
- Sections follow: **Why** (context) → **How** (steps) → **Tips** (lessons learned)
- The tone is practical and first-person ("my approach"), not academic
- Doc files are numbered for ordering (e.g., `01-`, `02-`)

## Hosting

- Currently hosted on **GitHub** (personal): https://github.com/Dhawi1902/testing-knowledge-base
- Long-term target is **GitLab** for team consumption
