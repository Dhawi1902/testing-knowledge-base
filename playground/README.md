# Playground - TaskFlow Application

A Docker-based task management application built as the **shared test target** for this knowledge base.

## Quick Start

**One-time setup** — add to your hosts file (`C:\Windows\System32\drivers\etc\hosts`):
```
127.0.0.1   taskflow.local
```

Then:
```bash
docker compose up -d
```

- App: http://taskflow.local
- Health Check: http://taskflow.local/api/admin/health
- Backend (direct): http://localhost:4000

## Test Credentials

| User | Email | Password |
|------|-------|----------|
| Admin | `admin@taskflow.local` | `admin123` |
| Test User 01 | `user01@taskflow.local` | `password01` |
| Test User 02-20 | `userNN@taskflow.local` | `passwordNN` |

## API Reference

See [PLAN.md](PLAN.md) for the full API design.

## Status

Under construction - see [PLAN.md](PLAN.md) for the build phases and progress.
