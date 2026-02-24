# JMeter Test Dashboard

Web-based dashboard for managing JMeter performance tests — run tests, manage slave VMs, view results, and analyze reports from a single interface.

## Quick Start

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8080
```

Open `http://localhost:8080`. On first run a setup wizard configures your project and generates an access token.

## Architecture

```
webapp/
├── main.py              ← FastAPI app, middleware, lifespan
├── routers/             ← API + page routes
│   ├── dashboard.py     ← Dashboard stats, alerts, trend data
│   ├── config.py        ← Slaves, VM config, properties
│   ├── results.py       ← Results listing, reports, regeneration
│   ├── test_plans.py    ← JMX management, runner, presets
│   ├── test_data.py     ← CSV upload/build/distribute
│   └── settings.py      ← App settings, system info
├── services/            ← Business logic
│   ├── auth.py          ← Token auth, access control, path safety
│   ├── config_parser.py ← Project config, path resolution
│   ├── jmeter.py        ← JMeter CLI wrapper
│   ├── jtl_parser.py    ← JTL parsing with JSON caching
│   ├── slaves.py        ← SSH operations, file distribution
│   ├── analysis.py      ← AI-powered result analysis
│   └── process_manager.py ← JMeter process lifecycle
├── templates/           ← Jinja2 HTML (extends base.html)
├── static/              ← CSS + JS
├── tests/               ← pytest suite (165 tests)
└── logs/                ← Rotating app logs (auto-created)
```

## Configuration

| File | Purpose |
|------|---------|
| `project.json` | Project paths (auto-detected on first run) |
| `settings.json` | App settings (theme, ports, auth, report config) |
| `config/vm_config.json` | SSH config for slave VMs |
| `slaves.txt` | Slave list with per-VM overrides |

All settings are editable through the web UI at **Settings**.

## Access Control

- **Localhost** requests have full admin access
- **Remote** users need a token (set in Settings > Auth)
- Token is stored as SHA-256 hash, transmitted via httponly cookie
- Viewers (no token) can read but not modify

## API Documentation

FastAPI auto-generated docs are available at:
- Swagger UI: `{base_path}/docs`
- ReDoc: `{base_path}/redoc`

## Key Features

- **Dashboard**: Stats overview, trend chart, alerts, slave health, disk usage
- **Test Plans**: Upload JMX, extract parameters, save presets, run tests
- **Results**: Browse results, view reports, compare runs, regenerate with filters
- **Test Data**: Upload/build CSV files, distribute to slaves (copy or split)
- **Slaves**: SSH management, start/stop JMeter servers, status monitoring
- **Properties**: JMeter properties editor with push-to-slaves

## Running Tests

```bash
cd jmeter-working-dir/webapp
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
```

With coverage report:

```bash
python -m pytest tests/ -v --tb=short \
  --cov=routers --cov=services --cov=main \
  --cov-report=term-missing
```

CI runs automatically via GitHub Actions on push/PR to `jmeter-working-dir/webapp/**`.

## Setup on a New Machine

```bash
git clone https://github.com/Dhawi1902/testing-knowledge-base.git
cd testing-knowledge-base/jmeter-working-dir/webapp
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8080
```

## Logging

API requests are logged to `logs/app.log` with rotating file handler (5MB max, 3 backups). Errors include full stack traces.
