# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **JMeter Performance Testing Knowledge Transfer** documentation project. It contains markdown files documenting a practical, real-world workflow for performance testing using Apache JMeter. The content is authored collaboratively with the repository owner and reflects their personal approach - not generic textbook material.

The documentation is intended to be hosted on **GitLab** for team consumption.

## Repository Structure

- `README.md` - Main navigation / table of contents with links to all doc sections
- `PLAN.md` - Content outline and progress tracker for all 14 sections + appendix
- `docs/` - All content files, numbered `01-` through `14-` plus `99-` for appendix
- `docs/images/` - Screenshots organized by section (e.g., `images/01/`)
- `scripts/` - Python scripts and batch files (referenced from docs)
- `samples/` - Sample `.jmx` files and CSV templates

## Content Conventions

- Each doc file has a **Table of Contents** at the top using anchor links
- Screenshots are marked with `<!-- TODO: Screenshot - description -->` where not yet captured
- Sections follow: **Why** (context) → **How** (steps) → **Tips** (lessons learned)
- The tone is practical and first-person ("my approach"), not academic

## Author Naming Conventions (Important)

The author uses specific naming conventions for JMeter elements that must be preserved:
- **Transaction Controllers:** `A-Z - <Action>` (e.g., `A - Login`, `B - Dashboard`) - letter prefix for sorted grouping in web reports
- **HTTP Samplers:** `01 - METHOD - <Description>` (e.g., `01 - POST - Submit Login`) - numbered prefix for sorted flow order in reports, no square brackets around method

## Key Technical Details

- Recommends **JDK 21** for JMeter (Groovy support, plugin compatibility)
- Uses **dual recording** approach: Blazemeter (for .jmx) + Fiddler (for correlation tracing)
- Fiddler proxy port is **8888**, Capture Traffic is **disabled** (proxy-only capture)
- Blazemeter Advanced Options: **Record Ajax Requests** enabled, **Randomize Think Time** disabled
- Python is used for test data distribution in distributed testing scenarios
