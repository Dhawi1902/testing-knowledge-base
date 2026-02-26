# JMeter Properties Editor — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the redundant Config Properties panel on the Fleet page with a JMeter Properties editor that manages `user.properties` for both master and slaves.

**Architecture:** Two-tab panel (Master / Slave) with curated property sections, searchable "Add Property" dropdown sourced from `jmeter.properties`, and per-property reset-to-default. Reads from `jmeter.properties` (catalog/defaults), writes to `user.properties` (overrides).

**Tech Stack:** FastAPI backend (Python), Jinja2 templates, vanilla JS frontend (existing patterns)

---

## Context

### What's being replaced
The **"Config Properties"** panel on the Fleet page (`slaves.html` lines 124-142) edits `jmeter-working-dir/config.properties`. Investigation revealed:
- This file is **NOT passed to JMeter** via `-q` or any flag
- It is **NOT sent to slaves** during provisioning
- It's only used for: legacy test_plan name fallback + snapshot copy into result folders
- The panel is **redundant** on the Fleet page

### What we're building
A **JMeter Properties editor** that manages `user.properties` — the correct file for JMeter configuration overrides. JMeter loads `user.properties` after `jmeter.properties`, so overrides take effect. This file survives JMeter upgrades (unlike editing `jmeter.properties` directly).

---

## Design

### Two Tabs: Master | Slave

#### Master Tab
- **Reads/writes:** `{jmeter_bin_dir}/user.properties` (path derived from `jmeter_path` in `project.json`)
- **Catalog source:** `{jmeter_bin_dir}/jmeter.properties` (~300 properties with defaults and comments)
- **Curated sections** (collapsible):
  - **Distributed/RMI** — `remote_hosts`, `client.rmi.localport`, `java.rmi.server.hostname`, `server.rmi.ssl.disable`
  - **Remote Batching** — `mode`, `num_sample_threshold`, `time_threshold`
  - **Results/JTL Save** — `jmeter.save.saveservice.*` fields
  - **Report Generator** — `jmeter.reportgenerator.apdex_satisfied_threshold`, etc.
  - **Summariser** — `summariser.interval`, `summariser.out`
  - **HTTP** (collapsed by default) — `httpclient4.retrycount`, `httpclient4.time_to_live`, `httpclient4.idletimeout`, `httpsampler.ignore_failed_embedded_resources`
- **Add Property** button → searchable dropdown of all ~300 properties from `jmeter.properties`, grouped by category, showing descriptions + "Custom..." option for arbitrary key=value
- **Each property row shows:** key, effective value (user override in normal text, `jmeter.properties` default greyed out), reset icon

#### Slave Tab
- **Reads/writes:** `jmeter-working-dir/config/slave-user.properties` (managed by webapp)
- **Curated fields only** (~10 properties):
  - **RMI** — `server.rmi.localport`, `server_port`, `java.rmi.server.hostname`, `server.rmi.ssl.disable`
  - **Runtime** — `server.exitaftertest`
  - **HTTP** — `httpclient4.retrycount`, `httpsampler.ignore_failed_embedded_resources`
  - **Results/Save** — `jmeter.save.saveservice.*` (must match master)
- **Add Property** button → same searchable dropdown but filtered to ~30 slave-relevant properties
- **Deployed to slaves** as `~/jmeter-slave/user.properties` during provisioning/start

### Property Value Resolution
- **Set** = property exists in `user.properties` → shown in normal text, editable
- **Default** = property only in `jmeter.properties` → shown greyed out with default value
- **Reset to default** = remove line from `user.properties` → falls back to `jmeter.properties` value
- **Override** = write `key=value` to `user.properties` → overrides whatever `jmeter.properties` says

### Data Flow

```
jmeter.properties (read-only) ──→ Property catalog (names, defaults, descriptions)
                                    ↓
user.properties (master r/w)  ──→ Master tab overrides
                                    ↓
slave-user.properties (r/w)   ──→ Slave tab overrides
                                    ↓ (on provision/start)
                              ~/jmeter-slave/user.properties (on each slave)
```

---

## Backend API

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config/jmeter-properties/catalog` | GET | Parse `jmeter.properties`, return all property keys with defaults, comments, and categories |
| `/api/config/jmeter-properties/master` | GET | Read `user.properties` from JMeter bin dir |
| `/api/config/jmeter-properties/master` | PUT | Write `user.properties` (admin only) |
| `/api/config/jmeter-properties/slave` | GET | Read `config/slave-user.properties` |
| `/api/config/jmeter-properties/slave` | PUT | Write `config/slave-user.properties` (admin only) |

### Catalog Parser
New function `parse_jmeter_properties_catalog(path)` that reads `jmeter.properties` and extracts:
- Property key
- Default value (from commented-out or active lines)
- Description (from preceding comment lines)
- Category (from section header comments like `#-----------`)

Reuses existing `read_config_properties()` / `write_config_properties()` from `config_parser.py` for reading/writing `user.properties` files.

### Existing Endpoints
`/api/config/properties` GET/PUT — **kept** for backward compatibility (runner snapshot logic). UI panel removed.

---

## Frontend

### HTML (slaves.html)
- **Remove** Config Properties card (lines 124-142)
- **Add** JMeter Properties card in same location with:
  - Tab bar: Master | Slave
  - Curated sections (collapsible groups of labeled inputs)
  - "Add Property" button
  - Save button
  - Property count badge showing "N overrides"

### Add Property Modal
- Search input at top
- Properties listed grouped by category
- Each shows: key, default value, description snippet
- Click to add → appears in the main panel
- "Custom..." option at bottom for arbitrary key=value

### JavaScript
- `loadJmeterProperties(tab)` — fetch catalog + user overrides
- `renderJmeterProperties(tab, catalog, overrides)` — render curated + custom sections
- `saveJmeterProperties(tab)` — collect overrides, PUT to backend
- `resetProperty(key)` — remove from overrides, revert to default display
- `openAddPropertyModal(tab)` — show searchable property list

---

## What Gets Removed

| Item | Action |
|------|--------|
| Config Properties HTML card (slaves.html:124-142) | **DELETE** |
| Config Properties JS functions (slaves.html:914-998) | **DELETE** |
| `loadProperties()`, `renderProperties()`, `addProperty()`, `removeProperty()`, `saveProperties()` | **DELETE** |
| `/api/config/properties` endpoints | **KEEP** (used by runner internally) |

---

## Files Modified/Created

| File | Action |
|------|--------|
| `services/config_parser.py` | **EDIT** — add `parse_jmeter_properties_catalog()` |
| `routers/config.py` | **EDIT** — add 5 new endpoints, keep old ones |
| `templates/slaves.html` | **EDIT** — replace Config Properties with JMeter Properties panel |
| `config/slave-user.properties` | **CREATE** — slave user.properties (initially empty) |
| `tests/test_config_api.py` | **EDIT** — add tests for new endpoints |

---

## Decisions

- **`user.properties` over `jmeter.properties`** — survives JMeter upgrades, clean separation
- **Slave properties stored locally** in `config/slave-user.properties` — pushed to slaves on provision/start, not edited on slaves directly
- **Config Properties panel removed** — file not used by JMeter, not sent to slaves, redundant
- **Old `/api/config/properties` kept** — runner uses it for snapshots, no breaking change
- **~300 property catalog** — parsed from actual `jmeter.properties` file, always up to date with installed JMeter version
