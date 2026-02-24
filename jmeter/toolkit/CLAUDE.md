# CLAUDE.md — JMeter Toolkit

This file provides guidance to Claude Code when working on the toolkit.

## Overview

The toolkit is a **reusable template** for JMeter performance testing projects. It is being generalized from a production MAYA Portal testing framework (`jmeter-working-dir/`) into a project-agnostic structure that can be copied into any new performance testing project.

See `PLAN.md` for the full implementation roadmap (5 phases).

## Current Status

The toolkit is in the **planning phase**. The working-dir webapp is fully implemented and serves as the source for generalization. Key changes already made to the working-dir (documented in PLAN.md section 3.3) should be carried forward.

## Target Structure

```
toolkit/
├── project.json.example      # Unified config (replaces multiple config files)
├── credentials.json.example   # SSH auth (gitignored)
├── .gitignore
├── setup.bat                  # First-time: Python check, venv, deps
├── init.bat                   # Project init: copy examples, create dirs
├── requirements.txt
├── test_plan/                 # User puts .jmx files here
├── test_data/                 # Generated/imported CSV files
├── results/                   # Auto-created by runner
├── extensions/                # JMeter plugins to deploy
├── utils/
│   ├── common.py              # Shared module (SSH, config, iteration)
│   ├── run_test.py            # Main test runner (replaces batch scripts)
│   ├── manage_servers.py      # Start/stop/status JMeter on slaves
│   ├── generate_data.py       # Config-driven data generation
│   ├── split_and_distribute.py
│   ├── setup_slave.py         # Bootstrap slave VMs
│   ├── collect_from_slaves.py
│   ├── clear_files.py
│   ├── create_folders.py
│   ├── deploy_extensions.py
│   ├── fetch_logs.py
│   ├── set_slave_ip.py
│   └── filter_jtl.py          # Already enhanced: sub-results + variables + regex
├── bin/
│   └── run.bat                # Thin launcher → python utils/run_test.py
├── webapp/                    # Dashboard (generalized from working-dir)
│   └── ...                    # See jmeter-working-dir/webapp/CLAUDE.md
└── monitoring/
    ├── docker-compose.yml     # InfluxDB + Grafana
    └── grafana/               # Pre-built JMeter dashboard
```

## Key Principles

1. **Single `project.json`** — replaces `config.properties` + `slaves.txt` + `vm_config.json` + other scattered configs
2. **`common.py` eliminates duplication** — SSH, config loading, slave iteration shared across all utils (~450 lines deduplicated)
3. **No MAYA-specific defaults** — all project-specific values come from config, not code
4. **Backward compatibility** — slaves file auto-migrates from plain text to JSON format
5. **Webapp reads from `project.json`** at toolkit root, not its own directory

## Already Implemented (in working-dir, carry forward)

### JTL Filter (`filter_jtl.py`)
- Removes sub-results (labels ending with `-N`), unresolved variables (`${...}`), optional regex
- Reduces JTL by ~80-85% (682 MB → 153 MB on real data)

### Slaves JSON Format (`config_parser.py`)
- `read_slaves()` returns `[{"ip": "x.x.x.x", "enabled": true}, ...]`
- `get_active_slaves()` returns only enabled IPs
- Auto-migrates plain text to JSON on first edit

### Report Optimization (`jmeter.py`)
- `REPORT_OPTIMIZE_PROPS` disables heavy over-time graphs
- Safe regeneration: filter → temp dir → swap on success

### Webapp Features (all pages)
- Full access control (admin/viewer/localhost)
- 7 pages: Dashboard, Test Plans & Runner, Results, Test Data, Slaves, Scripts, Settings
- CSV builder with 5 column types, distribution to slaves
- Live test execution with WebSocket streaming, summary stats, slave progress
- Mobile responsive with bottom nav bar
- Dark/light theme with CSS variables

## Coding Conventions

- All utils read from `project.json` via `common.load_project_config()`
- SSH credentials from `credentials.json` via `common.load_credentials()`
- Per-host overrides supported in credentials
- All file paths relative to toolkit root
- Use `common.for_each_slave()` for iteration with progress + summary
