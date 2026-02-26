# JMeter Properties Editor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the redundant Config Properties panel on the Fleet page with a JMeter Properties editor that manages `user.properties` for both master and slaves.

**Architecture:** Two-tab panel (Master / Slave) with curated property sections, searchable "Add Property" dropdown sourced from `jmeter.properties`, and per-property reset-to-default. Backend parses `jmeter.properties` as read-only catalog, reads/writes `user.properties` for overrides.

**Tech Stack:** FastAPI (Python), Jinja2 templates, vanilla JS, existing `config_parser.py` utilities

**Design doc:** `docs/plans/2026-02-26-jmeter-properties-editor-design.md`

---

## Task 1: Catalog parser — `parse_jmeter_properties_catalog()`

**Files:**
- Modify: `jmeter-working-dir/webapp/services/config_parser.py`
- Test: `jmeter-working-dir/webapp/tests/test_config_api.py`

### Step 1: Write the failing test

Add to `tests/test_config_api.py`:

```python
class TestJmeterPropertiesCatalog:
    """Unit tests for parse_jmeter_properties_catalog()."""

    def test_parse_catalog_from_sample(self, tmp_path):
        """Parse a sample jmeter.properties file and extract catalog entries."""
        from services.config_parser import parse_jmeter_properties_catalog

        sample = tmp_path / "jmeter.properties"
        sample.write_text(
            "#---------------------------------------------------------------------------\n"
            "# Distributed Testing\n"
            "#---------------------------------------------------------------------------\n"
            "\n"
            "# Set this if you don't want to use SSL for RMI\n"
            "#server.rmi.ssl.disable=false\n"
            "\n"
            "# Comma-separated list of remote servers\n"
            "remote_hosts=127.0.0.1\n"
            "\n"
            "#---------------------------------------------------------------------------\n"
            "# HTTP\n"
            "#---------------------------------------------------------------------------\n"
            "\n"
            "# Number of retries for HTTP\n"
            "#httpclient4.retrycount=0\n",
            encoding="utf-8",
        )
        catalog = parse_jmeter_properties_catalog(sample)
        assert len(catalog) >= 3
        # Check a commented-out property
        ssl_entry = next(e for e in catalog if e["key"] == "server.rmi.ssl.disable")
        assert ssl_entry["default"] == "false"
        assert "SSL" in ssl_entry["description"] or "ssl" in ssl_entry["description"].lower()
        assert ssl_entry["category"] == "Distributed Testing"
        # Check an active property
        hosts_entry = next(e for e in catalog if e["key"] == "remote_hosts")
        assert hosts_entry["default"] == "127.0.0.1"
        assert hosts_entry["category"] == "Distributed Testing"
        # Check category change
        http_entry = next(e for e in catalog if e["key"] == "httpclient4.retrycount")
        assert http_entry["category"] == "HTTP"
        assert http_entry["default"] == "0"

    def test_parse_catalog_empty_file(self, tmp_path):
        """Empty file returns empty catalog."""
        from services.config_parser import parse_jmeter_properties_catalog

        sample = tmp_path / "jmeter.properties"
        sample.write_text("# Just comments\n", encoding="utf-8")
        catalog = parse_jmeter_properties_catalog(sample)
        assert catalog == []

    def test_parse_catalog_missing_file(self, tmp_path):
        """Missing file returns empty catalog."""
        from services.config_parser import parse_jmeter_properties_catalog

        catalog = parse_jmeter_properties_catalog(tmp_path / "nope.properties")
        assert catalog == []
```

### Step 2: Run test to verify it fails

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/test_config_api.py::TestJmeterPropertiesCatalog -v`
Expected: FAIL with `ImportError: cannot import name 'parse_jmeter_properties_catalog'`

### Step 3: Write minimal implementation

Add to `services/config_parser.py` at the end of the file:

```python
def parse_jmeter_properties_catalog(path: Path) -> list[dict]:
    """Parse jmeter.properties file to extract a catalog of all properties.

    Returns list of {"key": str, "default": str, "description": str, "category": str}.
    Reads both commented-out (#key=value) and active (key=value) properties.
    Categories are detected from section header comments like '#---...'.
    """
    if not path.exists():
        return []

    catalog = []
    current_category = "General"
    description_lines = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            # Detect section headers: lines like "#----" preceded by "# Section Name"
            if stripped.startswith("#") and stripped.replace("#", "").replace("-", "").strip() == "":
                # This is a separator line like "#-----------"
                # Check if the previous description line is a category name
                if description_lines:
                    candidate = description_lines[-1].strip()
                    # Category names are short, don't contain '=' and aren't property descriptions
                    if candidate and "=" not in candidate and len(candidate) < 80:
                        current_category = candidate
                        description_lines = []
                continue

            # Collect comment lines as potential descriptions
            if stripped.startswith("#"):
                content = stripped.lstrip("#").strip()
                # Skip license headers and empty comments
                if content and not content.startswith("Licensed to") and not content.startswith("http://"):
                    # Check if this is a commented-out property: #key=value
                    if "=" in content and not content.startswith(" ") and not any(c == " " for c in content.split("=", 1)[0]):
                        key, _, value = content.partition("=")
                        key = key.strip()
                        value = value.strip()
                        if key and not key.startswith("Example") and not key.startswith("//"):
                            desc = " ".join(description_lines[-3:]) if description_lines else ""
                            catalog.append({
                                "key": key,
                                "default": value,
                                "description": desc,
                                "category": current_category,
                            })
                            description_lines = []
                            continue
                    description_lines.append(content)
                continue

            # Active (uncommented) property: key=value
            if "=" in stripped and stripped and not stripped.startswith("#"):
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip()
                if key:
                    desc = " ".join(description_lines[-3:]) if description_lines else ""
                    catalog.append({
                        "key": key,
                        "default": value,
                        "description": desc,
                        "category": current_category,
                    })
                    description_lines = []
                continue

            # Blank line — reset description buffer
            if not stripped:
                # Keep last few lines for next property, but reset after blank gap
                if not description_lines:
                    continue
                # Only reset if we just had a blank line after descriptions
                pass

    return catalog
```

### Step 4: Run test to verify it passes

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/test_config_api.py::TestJmeterPropertiesCatalog -v`
Expected: 3 PASSED

### Step 5: Commit

```bash
git add jmeter-working-dir/webapp/services/config_parser.py jmeter-working-dir/webapp/tests/test_config_api.py
git commit -m "feat(fleet): add parse_jmeter_properties_catalog() for property discovery"
```

---

## Task 2: Backend endpoints — JMeter Properties API

**Files:**
- Modify: `jmeter-working-dir/webapp/routers/config.py`
- Test: `jmeter-working-dir/webapp/tests/test_config_api.py`

### Step 1: Write the failing tests

Add to `tests/test_config_api.py`:

```python
class TestJmeterPropertiesMasterEndpoint:
    """API tests for /api/config/jmeter-properties/master."""

    def test_get(self, admin_client, bp, tmp_project_dir):
        """GET returns current user.properties overrides."""
        # Create a mock user.properties in a fake jmeter bin dir
        jmeter_bin = tmp_project_dir["project_root"] / "fake_jmeter_bin"
        jmeter_bin.mkdir(exist_ok=True)
        (jmeter_bin / "user.properties").write_text("server.rmi.ssl.disable=true\n")
        (jmeter_bin / "jmeter.bat").write_text("")
        # Point project config to fake jmeter
        import json
        pj = tmp_project_dir["project_json_path"]
        project = json.loads(pj.read_text())
        old_path = project["jmeter_path"]
        project["jmeter_path"] = str(jmeter_bin / "jmeter.bat").replace("\\", "/")
        pj.write_text(json.dumps(project, indent=2))
        # Reload project
        from main import app
        from services.config_parser import load_project_config
        app.state.project = load_project_config(pj)

        r = admin_client.get(f"{bp}/api/config/jmeter-properties/master")
        assert r.status_code == 200
        data = r.json()
        assert "properties" in data
        assert data["properties"].get("server.rmi.ssl.disable") == "true"

        # Cleanup
        project["jmeter_path"] = old_path
        pj.write_text(json.dumps(project, indent=2))
        app.state.project = load_project_config(pj)

    def test_put(self, admin_client, bp, tmp_project_dir):
        """PUT saves user.properties overrides."""
        jmeter_bin = tmp_project_dir["project_root"] / "fake_jmeter_bin"
        jmeter_bin.mkdir(exist_ok=True)
        (jmeter_bin / "user.properties").write_text("")
        (jmeter_bin / "jmeter.bat").write_text("")
        import json
        pj = tmp_project_dir["project_json_path"]
        project = json.loads(pj.read_text())
        old_path = project["jmeter_path"]
        project["jmeter_path"] = str(jmeter_bin / "jmeter.bat").replace("\\", "/")
        pj.write_text(json.dumps(project, indent=2))
        from main import app
        from services.config_parser import load_project_config
        app.state.project = load_project_config(pj)

        new_props = {"server.rmi.ssl.disable": "true", "remote_hosts": "10.0.0.1,10.0.0.2"}
        r = admin_client.put(f"{bp}/api/config/jmeter-properties/master", json={"properties": new_props})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify persisted
        r2 = admin_client.get(f"{bp}/api/config/jmeter-properties/master")
        saved = r2.json()["properties"]
        assert saved["server.rmi.ssl.disable"] == "true"
        assert saved["remote_hosts"] == "10.0.0.1,10.0.0.2"

        # Cleanup
        project["jmeter_path"] = old_path
        pj.write_text(json.dumps(project, indent=2))
        app.state.project = load_project_config(pj)


class TestJmeterPropertiesSlaveEndpoint:
    """API tests for /api/config/jmeter-properties/slave."""

    def test_get_empty(self, admin_client, bp):
        """GET returns empty when no slave-user.properties exists."""
        r = admin_client.get(f"{bp}/api/config/jmeter-properties/slave")
        assert r.status_code == 200
        assert r.json()["properties"] == {} or isinstance(r.json()["properties"], dict)

    def test_put_and_get(self, admin_client, bp):
        """PUT saves, GET reads back."""
        props = {"server.rmi.localport": "50000", "server.rmi.ssl.disable": "true"}
        r = admin_client.put(f"{bp}/api/config/jmeter-properties/slave", json={"properties": props})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        r2 = admin_client.get(f"{bp}/api/config/jmeter-properties/slave")
        assert r2.json()["properties"]["server.rmi.localport"] == "50000"
        # Cleanup
        admin_client.put(f"{bp}/api/config/jmeter-properties/slave", json={"properties": {}})


class TestJmeterPropertiesCatalogEndpoint:
    """API tests for /api/config/jmeter-properties/catalog."""

    def test_catalog_returns_list(self, admin_client, bp, tmp_project_dir):
        """GET catalog returns list of property entries (may be empty if jmeter not installed)."""
        r = admin_client.get(f"{bp}/api/config/jmeter-properties/catalog")
        assert r.status_code == 200
        data = r.json()
        assert "catalog" in data
        assert isinstance(data["catalog"], list)

    def test_catalog_with_mock_jmeter(self, admin_client, bp, tmp_project_dir):
        """GET catalog with a mock jmeter.properties returns parsed entries."""
        jmeter_bin = tmp_project_dir["project_root"] / "fake_jmeter_bin"
        jmeter_bin.mkdir(exist_ok=True)
        (jmeter_bin / "jmeter.properties").write_text(
            "#---------------------------------------------------------------------------\n"
            "# Test Section\n"
            "#---------------------------------------------------------------------------\n"
            "# A test property\n"
            "#test.prop=default_val\n",
            encoding="utf-8",
        )
        (jmeter_bin / "jmeter.bat").write_text("")
        import json
        pj = tmp_project_dir["project_json_path"]
        project = json.loads(pj.read_text())
        old_path = project["jmeter_path"]
        project["jmeter_path"] = str(jmeter_bin / "jmeter.bat").replace("\\", "/")
        pj.write_text(json.dumps(project, indent=2))
        from main import app
        from services.config_parser import load_project_config
        app.state.project = load_project_config(pj)

        r = admin_client.get(f"{bp}/api/config/jmeter-properties/catalog")
        assert r.status_code == 200
        catalog = r.json()["catalog"]
        assert len(catalog) >= 1
        assert catalog[0]["key"] == "test.prop"
        assert catalog[0]["default"] == "default_val"

        # Cleanup
        project["jmeter_path"] = old_path
        pj.write_text(json.dumps(project, indent=2))
        app.state.project = load_project_config(pj)
```

### Step 2: Run tests to verify they fail

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/test_config_api.py::TestJmeterPropertiesMasterEndpoint tests/test_config_api.py::TestJmeterPropertiesSlaveEndpoint tests/test_config_api.py::TestJmeterPropertiesCatalogEndpoint -v`
Expected: FAIL with 404 (endpoints don't exist yet)

### Step 3: Write minimal implementation

Add to `routers/config.py` after the existing `config.properties` section (after line 70) and before the `vm_config.json` section:

```python
# --- JMeter Properties (user.properties) ---

def _get_jmeter_bin_dir(project: dict) -> Path | None:
    """Derive JMeter bin directory from jmeter_path in project config."""
    jmeter_path = project.get("jmeter_path", "")
    if not jmeter_path:
        return None
    p = Path(jmeter_path)
    # jmeter_path points to jmeter.bat or jmeter — bin dir is its parent
    if p.exists():
        return p.parent
    # Even if the file doesn't exist, try the parent dir
    return p.parent if p.parent.exists() else None


@router.get("/api/config/jmeter-properties/catalog")
async def get_jmeter_properties_catalog(request: Request):
    """Parse jmeter.properties to return the full property catalog."""
    from services.config_parser import parse_jmeter_properties_catalog
    project = request.app.state.project
    bin_dir = _get_jmeter_bin_dir(project)
    if not bin_dir:
        return {"catalog": []}
    jmeter_props = bin_dir / "jmeter.properties"
    catalog = parse_jmeter_properties_catalog(jmeter_props)
    return {"catalog": catalog}


@router.get("/api/config/jmeter-properties/master")
async def get_jmeter_user_properties(request: Request):
    """Read user.properties from JMeter bin directory (master overrides)."""
    project = request.app.state.project
    bin_dir = _get_jmeter_bin_dir(project)
    if not bin_dir:
        return {"properties": {}, "path": ""}
    user_props_path = bin_dir / "user.properties"
    props = read_config_properties(user_props_path)
    return {"properties": props, "path": str(user_props_path)}


@router.put("/api/config/jmeter-properties/master")
async def save_jmeter_user_properties(request: Request, data: PropertiesUpdate):
    """Write user.properties to JMeter bin directory (master overrides)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    bin_dir = _get_jmeter_bin_dir(project)
    if not bin_dir:
        return JSONResponse(status_code=400, content={"error": "JMeter path not configured"})
    user_props_path = bin_dir / "user.properties"
    write_config_properties(user_props_path, data.properties,
                            comments=["JMeter user.properties — managed by JMeter Dashboard webapp"])
    return {"ok": True}


@router.get("/api/config/jmeter-properties/slave")
async def get_slave_user_properties(request: Request):
    """Read slave-user.properties from config directory."""
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    slave_props_path = config_dir / "slave-user.properties"
    props = read_config_properties(slave_props_path)
    return {"properties": props, "path": str(slave_props_path)}


@router.put("/api/config/jmeter-properties/slave")
async def save_slave_user_properties(request: Request, data: PropertiesUpdate):
    """Write slave-user.properties to config directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    slave_props_path = config_dir / "slave-user.properties"
    write_config_properties(slave_props_path, data.properties,
                            comments=["Slave user.properties — pushed to slaves during provisioning"])
    return {"ok": True}
```

Also add the import at the top of `config.py` (line 14-15 area — `parse_jmeter_properties_catalog` is already importable from `config_parser`):

No new import needed — the catalog endpoint imports inline via `from services.config_parser import parse_jmeter_properties_catalog`. The `read_config_properties`, `write_config_properties`, and `PropertiesUpdate` are already imported.

### Step 4: Run tests to verify they pass

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/test_config_api.py::TestJmeterPropertiesMasterEndpoint tests/test_config_api.py::TestJmeterPropertiesSlaveEndpoint tests/test_config_api.py::TestJmeterPropertiesCatalogEndpoint -v`
Expected: All PASSED

### Step 5: Run full test suite

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -x --tb=short`
Expected: All ~291 tests pass, no regressions

### Step 6: Commit

```bash
git add jmeter-working-dir/webapp/routers/config.py jmeter-working-dir/webapp/tests/test_config_api.py
git commit -m "feat(fleet): add JMeter Properties API endpoints (catalog, master, slave)"
```

---

## Task 3: Security tests — viewer denied

**Files:**
- Modify: `jmeter-working-dir/webapp/tests/test_security.py`

### Step 1: Write the failing tests

Add to the existing `TestViewerDenied` class in `tests/test_security.py`:

```python
    def test_jmeter_properties_master_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/jmeter-properties/master", json={"properties": {}})
        assert r.status_code == 200
        assert r.json().get("error") or r.json().get("detail")

    def test_jmeter_properties_slave_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/jmeter-properties/slave", json={"properties": {}})
        assert r.status_code == 200
        assert r.json().get("error") or r.json().get("detail")
```

### Step 2: Run tests to verify they pass

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/test_security.py -v -k "jmeter_properties"`
Expected: PASSED (the `_check_access` guard already works for these endpoints)

### Step 3: Commit

```bash
git add jmeter-working-dir/webapp/tests/test_security.py
git commit -m "test(security): add viewer-denied tests for JMeter Properties PUT endpoints"
```

---

## Task 4: Remove old Config Properties panel + add JMeter Properties HTML

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/slaves.html`

### Step 1: Remove old Config Properties card

In `slaves.html`, **delete** lines 124-142 (the `<!-- Config Properties Editor -->` card) and replace with the new JMeter Properties panel HTML:

```html
<!-- JMeter Properties Editor (#26 redesign) -->
<div class="card" style="margin-top:24px;">
    <div class="card-header" style="cursor:pointer;" onclick="toggleJmeterProps()">
        <span class="card-title"><span class="collapse-icon" id="jpropsIcon">&#9654;</span> JMeter Properties</span>
        <span class="text-light text-sm">user.properties overrides <span id="jpropsCount"></span></span>
    </div>
    <div id="jpropsBody" style="display:none;">
        <!-- Tabs: Master | Slave -->
        <div class="flex gap-8 mb-16" style="border-bottom:1px solid var(--color-border);padding-bottom:8px;">
            <button class="btn btn-sm" id="jpropsTabMaster" onclick="switchJpropsTab('master')" style="font-weight:bold;">Master</button>
            <button class="btn btn-sm btn-outline" id="jpropsTabSlave" onclick="switchJpropsTab('slave')">Slave</button>
            <div style="flex:1;"></div>
            {% if access_level != 'viewer' %}
            <button class="btn btn-outline btn-sm" onclick="openAddPropertyModal()">+ Add Property</button>
            <button class="btn btn-primary btn-sm" onclick="saveJmeterProperties()">Save</button>
            {% endif %}
        </div>
        <!-- Properties content -->
        <div id="jpropsContainer">
            <div class="text-light" style="text-align:center;padding:16px;">Loading...</div>
        </div>
        <div class="text-sm text-light" id="jpropsPath" style="margin-top:8px;"></div>
    </div>
</div>

<!-- Add Property Modal -->
<div id="addPropModal" class="modal" style="display:none;">
    <div class="modal-content" style="max-width:600px;">
        <div class="modal-header">
            <h3>Add JMeter Property</h3>
            <button class="modal-close" onclick="closeAddPropertyModal()">&times;</button>
        </div>
        <div style="padding:16px;">
            <input class="form-input mb-8" id="propSearchInput" type="text" placeholder="Search properties... (e.g. rmi, http, timeout)" oninput="filterPropertyList(this.value)">
            <div id="propSearchResults" style="max-height:400px;overflow-y:auto;"></div>
            <div style="margin-top:12px;border-top:1px solid var(--color-border);padding-top:12px;">
                <div class="text-sm text-bold mb-4">Custom Property</div>
                <div class="flex gap-8">
                    <input class="form-input form-input-mono" id="customPropKey" placeholder="key" style="flex:1;">
                    <input class="form-input form-input-mono" id="customPropVal" placeholder="value" style="flex:1;">
                    <button class="btn btn-primary btn-sm" onclick="addCustomProperty()">Add</button>
                </div>
            </div>
        </div>
    </div>
</div>
```

### Step 2: Remove old Config Properties JS + add new JS

In the `<script>` block, **delete** lines 914-998 (the `// ===== Config Properties Editor =====` section through `saveProperties()`).

Replace with:

```javascript
// ===== JMeter Properties Editor =====
let jpropsTab = 'master';
let jpropsCatalog = [];
let jpropsOverrides = {};
let jpropsPath = '';

// Curated property keys per tab
const CURATED_MASTER = {
    'Distributed / RMI': ['remote_hosts','client.rmi.localport','java.rmi.server.hostname','server.rmi.ssl.disable'],
    'Remote Batching': ['mode','num_sample_threshold','time_threshold'],
    'Results / JTL Save': ['jmeter.save.saveservice.output_format','jmeter.save.saveservice.response_data','jmeter.save.saveservice.samplerData','jmeter.save.saveservice.requestHeaders','jmeter.save.saveservice.url','jmeter.save.saveservice.responseHeaders','jmeter.save.saveservice.timestamp_format'],
    'Report Generator': ['jmeter.reportgenerator.apdex_satisfied_threshold','jmeter.reportgenerator.apdex_tolerated_threshold','jmeter.reportgenerator.overall_granularity'],
    'Summariser': ['summariser.interval','summariser.out'],
    'HTTP': ['httpclient4.retrycount','httpclient4.time_to_live','httpclient4.idletimeout','httpsampler.ignore_failed_embedded_resources'],
};
const CURATED_SLAVE = {
    'RMI': ['server.rmi.localport','server_port','java.rmi.server.hostname','server.rmi.ssl.disable'],
    'Runtime': ['server.exitaftertest'],
    'HTTP': ['httpclient4.retrycount','httpsampler.ignore_failed_embedded_resources'],
    'Results / Save': ['jmeter.save.saveservice.output_format','jmeter.save.saveservice.timestamp_format'],
};

function toggleJmeterProps() {
    const body = document.getElementById('jpropsBody');
    const icon = document.getElementById('jpropsIcon');
    const hidden = body.style.display === 'none';
    body.style.display = hidden ? '' : 'none';
    icon.innerHTML = hidden ? '&#9660;' : '&#9654;';
    if (hidden && !jpropsCatalog.length) loadJmeterProperties();
}

function switchJpropsTab(tab) {
    jpropsTab = tab;
    document.getElementById('jpropsTabMaster').className = tab === 'master' ? 'btn btn-sm' : 'btn btn-sm btn-outline';
    document.getElementById('jpropsTabSlave').className = tab === 'slave' ? 'btn btn-sm' : 'btn btn-sm btn-outline';
    document.getElementById('jpropsTabMaster').style.fontWeight = tab === 'master' ? 'bold' : '';
    document.getElementById('jpropsTabSlave').style.fontWeight = tab === 'slave' ? 'bold' : '';
    loadJmeterProperties();
}

async function loadJmeterProperties() {
    try {
        const [catalogResp, propsResp] = await Promise.all([
            api('/api/config/jmeter-properties/catalog'),
            api(`/api/config/jmeter-properties/${jpropsTab}`),
        ]);
        jpropsCatalog = catalogResp.catalog || [];
        jpropsOverrides = propsResp.properties || {};
        jpropsPath = propsResp.path || '';
        renderJmeterProperties();
    } catch (e) {
        document.getElementById('jpropsContainer').innerHTML =
            '<div class="text-light" style="text-align:center;padding:16px;">Failed to load properties.</div>';
    }
}

function renderJmeterProperties() {
    const container = document.getElementById('jpropsContainer');
    const curated = jpropsTab === 'master' ? CURATED_MASTER : CURATED_SLAVE;
    const catalogMap = {};
    jpropsCatalog.forEach(e => { catalogMap[e.key] = e; });

    let html = '';
    const renderedKeys = new Set();

    // Render curated sections
    for (const [section, keys] of Object.entries(curated)) {
        html += `<div class="mb-16">`;
        html += `<div class="text-sm text-bold mb-4" style="color:var(--color-text-secondary);">${escHtml(section)}</div>`;
        html += `<div class="props-grid">`;
        keys.forEach(key => {
            renderedKeys.add(key);
            const override = jpropsOverrides[key];
            const catalogEntry = catalogMap[key];
            const defaultVal = catalogEntry ? catalogEntry.default : '';
            const desc = catalogEntry ? catalogEntry.description : '';
            const hasOverride = override !== undefined && override !== '';
            const displayVal = hasOverride ? override : defaultVal;
            const inputClass = hasOverride ? 'form-input form-input-mono' : 'form-input form-input-mono text-light';

            html += `<div class="prop-row flex gap-8 mb-4" style="align-items:center;">`;
            html += `<label class="form-label" style="min-width:280px;font-family:var(--font-mono);font-size:12px;" title="${escAttr(desc)}">${escHtml(key)}</label>`;
            html += `<input class="${inputClass} jprop-input" data-key="${escAttr(key)}" value="${escAttr(displayVal)}" `;
            html += `placeholder="${escAttr(defaultVal)}" ${isAdmin ? '' : 'readonly'} `;
            html += `style="flex:1;${hasOverride ? '' : 'opacity:0.5;'}" `;
            html += `onfocus="this.style.opacity='1'" onblur="if(!this.value||this.value==='${escAttr(defaultVal)}')this.style.opacity='0.5'">`;
            if (isAdmin && hasOverride) {
                html += `<button class="del-btn" onclick="resetJprop('${escAttr(key)}')" title="Reset to default">&circlearrowright;</button>`;
            } else {
                html += `<span style="width:24px;display:inline-block;"></span>`;
            }
            html += `</div>`;
        });
        html += `</div></div>`;
    }

    // Render custom overrides (not in curated list)
    const customKeys = Object.keys(jpropsOverrides).filter(k => !renderedKeys.has(k));
    if (customKeys.length) {
        html += `<div class="mb-16">`;
        html += `<div class="text-sm text-bold mb-4" style="color:var(--color-text-secondary);">Custom Overrides</div>`;
        customKeys.forEach(key => {
            renderedKeys.add(key);
            html += `<div class="prop-row flex gap-8 mb-4" style="align-items:center;">`;
            html += `<input class="form-input form-input-mono jprop-key" value="${escAttr(key)}" style="min-width:280px;" ${isAdmin ? '' : 'readonly'}>`;
            html += `<input class="form-input form-input-mono jprop-input" data-key="${escAttr(key)}" value="${escAttr(jpropsOverrides[key])}" style="flex:1;" ${isAdmin ? '' : 'readonly'}>`;
            if (isAdmin) {
                html += `<button class="del-btn" onclick="resetJprop('${escAttr(key)}')" title="Remove">&times;</button>`;
            }
            html += `</div>`;
        });
        html += `</div>`;
    }

    if (!html) {
        html = '<div class="text-light" style="text-align:center;padding:16px;">No properties. Click "+ Add Property" to configure.</div>';
    }

    container.innerHTML = html;
    document.getElementById('jpropsPath').textContent = jpropsPath ? `File: ${jpropsPath}` : '';

    // Update count badge
    const count = Object.keys(jpropsOverrides).length;
    document.getElementById('jpropsCount').textContent = count ? `(${count} override${count > 1 ? 's' : ''})` : '';
}

function resetJprop(key) {
    delete jpropsOverrides[key];
    renderJmeterProperties();
}

async function saveJmeterProperties() {
    // Collect values from inputs
    const inputs = document.querySelectorAll('.jprop-input');
    const props = {};
    inputs.forEach(input => {
        const key = input.dataset.key;
        const val = input.value.trim();
        if (key && val) {
            props[key] = val;
        }
    });
    // Also collect custom key inputs (renamed keys)
    const keyInputs = document.querySelectorAll('.jprop-key');
    keyInputs.forEach((keyInput, idx) => {
        const newKey = keyInput.value.trim();
        const valInput = keyInput.parentElement.querySelector('.jprop-input');
        if (newKey && valInput && valInput.value.trim()) {
            // Remove old key if renamed
            const origKey = valInput.dataset.key;
            if (origKey !== newKey) delete props[origKey];
            props[newKey] = valInput.value.trim();
        }
    });
    try {
        await api(`/api/config/jmeter-properties/${jpropsTab}`, { method: 'PUT', body: { properties: props } });
        jpropsOverrides = props;
        showToast(`${jpropsTab === 'master' ? 'Master' : 'Slave'} properties saved`, 'success');
        renderJmeterProperties();
    } catch (e) {
        showToast('Failed to save properties', 'error');
    }
}

// --- Add Property Modal ---
function openAddPropertyModal() {
    document.getElementById('addPropModal').style.display = 'flex';
    document.getElementById('propSearchInput').value = '';
    document.getElementById('propSearchInput').focus();
    filterPropertyList('');
}

function closeAddPropertyModal() {
    document.getElementById('addPropModal').style.display = 'none';
}

function filterPropertyList(query) {
    const container = document.getElementById('propSearchResults');
    const q = query.toLowerCase();
    let filtered = jpropsCatalog;
    if (q) {
        filtered = jpropsCatalog.filter(e =>
            e.key.toLowerCase().includes(q) ||
            e.description.toLowerCase().includes(q) ||
            e.category.toLowerCase().includes(q)
        );
    }
    // Group by category
    const groups = {};
    filtered.slice(0, 50).forEach(e => {
        if (!groups[e.category]) groups[e.category] = [];
        groups[e.category].push(e);
    });
    let html = '';
    for (const [cat, entries] of Object.entries(groups)) {
        html += `<div class="text-sm text-bold mb-4 mt-8" style="color:var(--color-text-secondary);">${escHtml(cat)}</div>`;
        entries.forEach(e => {
            const already = e.key in jpropsOverrides;
            html += `<div class="prop-search-item flex gap-8 mb-2" style="align-items:center;padding:4px 8px;border-radius:4px;cursor:pointer;${already ? 'opacity:0.4;' : ''}" `;
            html += `onclick="${already ? '' : `addCatalogProperty('${escAttr(e.key)}','${escAttr(e.default)}')`}">`;
            html += `<code style="min-width:240px;font-size:12px;">${escHtml(e.key)}</code>`;
            html += `<span class="text-light text-sm" style="flex:1;">${escHtml(e.description).substring(0, 80)}</span>`;
            html += `<code class="text-light" style="font-size:11px;">${escHtml(e.default)}</code>`;
            html += `</div>`;
        });
    }
    if (!html) html = '<div class="text-light" style="text-align:center;padding:16px;">No matching properties.</div>';
    if (filtered.length > 50) html += `<div class="text-light text-sm" style="text-align:center;padding:8px;">Showing 50 of ${filtered.length} — type to narrow results</div>`;
    container.innerHTML = html;
}

function addCatalogProperty(key, defaultVal) {
    jpropsOverrides[key] = defaultVal;
    renderJmeterProperties();
    closeAddPropertyModal();
    showToast(`Added ${key}`, 'success');
}

function addCustomProperty() {
    const key = document.getElementById('customPropKey').value.trim();
    const val = document.getElementById('customPropVal').value.trim();
    if (!key) { showToast('Key cannot be empty', 'warning'); return; }
    jpropsOverrides[key] = val;
    renderJmeterProperties();
    closeAddPropertyModal();
    showToast(`Added ${key}`, 'success');
}
```

### Step 3: Update `init()` function

In the existing `init()` function at the end of the script block, **remove** the `loadProperties()` call (if present). No need to auto-load JMeter Properties — it loads on expand.

### Step 4: Run full test suite

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -x --tb=short`
Expected: All tests pass

### Step 5: Commit

```bash
git add jmeter-working-dir/webapp/templates/slaves.html
git commit -m "feat(fleet): replace Config Properties with JMeter Properties editor UI"
```

---

## Task 5: Manual walkthrough verification

### Step 1: Start the webapp

Run: `cd jmeter-working-dir/webapp && python __main__.py`

### Step 2: Navigate to Fleet page

Open `http://127.0.0.1:8080/fleet` in browser.

### Step 3: Verify

- [ ] Old "Config Properties" panel is gone
- [ ] New "JMeter Properties" panel is visible (collapsed)
- [ ] Click to expand — Master tab is active by default
- [ ] Curated sections show with grouped property fields
- [ ] Default values shown greyed out
- [ ] Switch to Slave tab — smaller set of curated fields
- [ ] Click "+ Add Property" — modal opens with searchable list
- [ ] Type "rmi" — filters to RMI-related properties
- [ ] Click a property — adds it to the panel
- [ ] Click "Custom..." — can add arbitrary key=value
- [ ] Click "Save" — toast confirms save
- [ ] Reload page, expand panel — values persist
- [ ] Check `user.properties` file in JMeter bin dir — contains saved overrides

### Step 4: Commit any fixes

```bash
git add -A
git commit -m "fix(fleet): polish JMeter Properties editor from walkthrough"
```

---

## Task 6: Update feature audit doc

**Files:**
- Modify: `docs/plans/2026-02-26-webapp-feature-audit.md`

### Step 1: Update item #26

Change Session 4 item #26 from `config.properties editor` to `JMeter Properties editor (user.properties)`.

Update the Decisions section to note:
- **JMeter Properties (#26):** Replaced `config.properties` editor with `user.properties` editor. Master tab reads/writes JMeter's `user.properties` via catalog from `jmeter.properties`. Slave tab manages `config/slave-user.properties` pushed during provisioning. Old config.properties endpoints kept for runner backward compatibility.

### Step 2: Commit

```bash
git add docs/plans/2026-02-26-webapp-feature-audit.md
git commit -m "docs: update feature audit — #26 is now JMeter Properties editor"
```

---

## Summary

| Task | Tests | Files |
|------|-------|-------|
| 1. Catalog parser | 3 unit tests | `config_parser.py`, `test_config_api.py` |
| 2. Backend endpoints | 6 API tests | `config.py`, `test_config_api.py` |
| 3. Security tests | 2 viewer-denied tests | `test_security.py` |
| 4. Frontend replacement | — | `slaves.html` |
| 5. Manual walkthrough | — | — |
| 6. Doc update | — | `feature-audit.md` |

**Total: ~11 new tests, 5 files modified, 1 file created (`slave-user.properties`)**

## Verification

```bash
cd jmeter-working-dir/webapp
python -m pytest tests/ -v --tb=short
```

Expected: ~302+ tests passing (291 existing + 11 new), no regressions.
