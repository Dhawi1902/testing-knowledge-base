"""Test fixtures for the JMeter Dashboard webapp."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — create test data
# ---------------------------------------------------------------------------

def make_csv(data_dir: Path, name: str = "test_users.csv") -> Path:
    content = "username,password,status\nuser001,pass1,active\nuser002,pass2,inactive\n"
    path = data_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def make_jmx(jmx_dir: Path, name: str = "test.jmx") -> Path:
    content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <TestPlan testname="Test Plan">
      <stringProp name="threads">${__P(student,10)}</stringProp>
      <stringProp name="ramp">${__P(rampUp,5)}</stringProp>
    </TestPlan>
  </hashTree>
</jmeterTestPlan>"""
    path = jmx_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def make_result_folder(results_dir: Path, name: str = "20260224_1") -> Path:
    date_dir = results_dir / name[:8]
    date_dir.mkdir(parents=True, exist_ok=True)
    folder = date_dir / name
    folder.mkdir(exist_ok=True)
    jtl = (
        "timeStamp,elapsed,label,responseCode,responseMessage,threadName,"
        "dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,"
        "URL,Latency,IdleTime,Connect\n"
        "1708764000000,150,Login,200,OK,Thread-1,text,true,,1024,256,1,1,"
        "http://test/login,100,0,50\n"
        "1708764001000,200,Dashboard,200,OK,Thread-1,text,true,,2048,512,1,1,"
        "http://test/dashboard,150,0,60\n"
    )
    (folder / "results.jtl").write_text(jtl, encoding="utf-8")
    report = folder / "report"
    report.mkdir()
    (report / "index.html").write_text("<html><body>Report</body></html>")
    return folder


# ---------------------------------------------------------------------------
# Session-scoped temp directory tree
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tmp_project_dir(tmp_path_factory):
    """Create a temp directory tree mimicking the real project layout."""
    base = tmp_path_factory.mktemp("webapp_test")

    webapp_dir = base / "webapp"
    project_root = base / "project_root"
    webapp_dir.mkdir()
    project_root.mkdir()

    # Project sub-directories
    for d in ("test_plan", "test_data", "results", "config"):
        (project_root / d).mkdir()

    # Minimal settings.json — no auth token
    settings = {
        "theme": "dark",
        "sidebar_collapsed": False,
        "server": {
            "domain": "", "host": "127.0.0.1", "port": 8080,
            "allow_external": False, "base_path": "",
        },
        "runner": {"auto_scroll": True, "max_log_lines": 1000, "confirm_before_stop": True},
        "results": {"sort_order": "newest"},
        "analysis": {"ollama_url": "http://localhost:11434", "ollama_model": "llama3.1:8b", "ollama_timeout": 120},
        "auth": {"token": "", "cookie_name": "jmeter_token", "cookie_max_age": 86400},
        "monitoring": {"grafana_url": "", "influxdb_url": ""},
    }
    (webapp_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # project.json — absolute project_root so resolve_path() works
    project = {
        "name": "TestProject",
        "project_root": str(project_root).replace("\\", "/"),
        "jmeter_path": "jmeter",
        "paths": {
            "jmx_dir": "test_plan",
            "config_dir": "config",
            "config_properties": "config.properties",
            "results_dir": "results",
            "test_data_dir": "test_data",
            "slaves_file": "slaves.txt",
            "scripts_dirs": [],
        },
    }
    (webapp_dir / "project.json").write_text(json.dumps(project, indent=2))

    # Other config files
    (webapp_dir / "presets.json").write_text("{}")
    (webapp_dir / "filter_presets.json").write_text("{}")
    (webapp_dir / "config").mkdir()
    (project_root / "config.properties").write_text("test_plan=test.jmx\nstudent=10\n")
    (project_root / "config" / "vm_config.json").write_text("{}")
    (project_root / "slaves.txt").write_text("[]")

    return {
        "base": base,
        "webapp_dir": webapp_dir,
        "project_root": project_root,
        "settings_path": webapp_dir / "settings.json",
        "project_json_path": webapp_dir / "project.json",
    }


# ---------------------------------------------------------------------------
# Session-scoped path patching
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _patch_paths(tmp_project_dir):
    """Redirect all runtime file I/O to the temp directory tree."""
    d = tmp_project_dir

    import main
    import services.settings as settings_svc
    import routers.config as config_mod
    import routers.test_plans as plans_mod
    import routers.test_data as data_mod
    import services.auth as auth_mod

    patches = [
        patch.object(main, "PROJECT_JSON", d["project_json_path"]),
        patch.object(settings_svc, "SETTINGS_FILE", d["settings_path"]),
        patch.object(auth_mod, "_SETTINGS_FILE", d["settings_path"]),
        patch.object(config_mod, "PROJECT_JSON", d["project_json_path"]),
        patch.object(plans_mod, "PRESETS_FILE", d["webapp_dir"] / "presets.json"),
        patch.object(plans_mod, "FILTER_PRESETS_FILE", d["webapp_dir"] / "filter_presets.json"),
        patch.object(data_mod, "CSV_TEMPLATES_FILE", d["webapp_dir"] / "csv_templates.json"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Route prefix
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def bp():
    """Return the BASE_PATH that routes are registered under."""
    import main
    return main.BASE_PATH


# ---------------------------------------------------------------------------
# Test clients
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_client(monkeypatch):
    """TestClient treated as localhost — always admin.

    TestClient's default client host is 'testclient', not '127.0.0.1',
    so we patch is_localhost to ensure admin access even when a token is set.
    """
    import services.auth as auth_mod
    import main as main_mod

    monkeypatch.setattr(auth_mod, "is_localhost", lambda _req: True)
    monkeypatch.setattr(main_mod, "_is_localhost", lambda _req: True)

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def viewer_client(tmp_project_dir, monkeypatch):
    """TestClient simulating remote viewer (no valid cookie, token is set)."""
    import services.auth as auth_mod
    import main as main_mod

    # Set a known auth token so remote users need it
    sp = tmp_project_dir["settings_path"]
    settings = json.loads(sp.read_text())
    settings["auth"]["token"] = auth_mod.hash_token("viewer-test-token")
    sp.write_text(json.dumps(settings, indent=2))

    # Make all is_localhost calls return False
    monkeypatch.setattr(auth_mod, "is_localhost", lambda _req: False)
    monkeypatch.setattr(main_mod, "_is_localhost", lambda _req: False)

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c

    # Restore no-token state
    settings["auth"]["token"] = ""
    sp.write_text(json.dumps(settings, indent=2))


@pytest.fixture
def authed_remote_client(tmp_project_dir, monkeypatch):
    """Remote client WITH valid token cookie — admin via token auth."""
    import services.auth as auth_mod
    import main as main_mod

    plain_token = "remote-admin-token"
    sp = tmp_project_dir["settings_path"]
    settings = json.loads(sp.read_text())
    settings["auth"]["token"] = auth_mod.hash_token(plain_token)
    sp.write_text(json.dumps(settings, indent=2))

    monkeypatch.setattr(auth_mod, "is_localhost", lambda _req: False)
    monkeypatch.setattr(main_mod, "_is_localhost", lambda _req: False)

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app, cookies={"jmeter_token": plain_token}) as c:
        yield c

    settings["auth"]["token"] = ""
    sp.write_text(json.dumps(settings, indent=2))


# ---------------------------------------------------------------------------
# Test data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_project_dir):
    """Create a test CSV in the temp test_data directory."""
    data_dir = tmp_project_dir["project_root"] / "test_data"
    path = make_csv(data_dir)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def sample_jmx(tmp_project_dir):
    """Create a test JMX in the temp test_plan directory."""
    jmx_dir = tmp_project_dir["project_root"] / "test_plan"
    path = make_jmx(jmx_dir)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def sample_result(tmp_project_dir):
    """Create a fake result folder with JTL and report."""
    results_dir = tmp_project_dir["project_root"] / "results"
    folder = make_result_folder(results_dir)
    yield folder
    if folder.exists():
        shutil.rmtree(str(folder))
    # Clean up date dir if empty
    date_dir = folder.parent
    if date_dir.exists() and not any(date_dir.iterdir()):
        date_dir.rmdir()


@pytest.fixture
def second_result(tmp_project_dir):
    """Create a second result folder for compare tests."""
    results_dir = tmp_project_dir["project_root"] / "results"
    folder = make_result_folder(results_dir, "20260224_3")
    yield folder
    if folder.exists():
        shutil.rmtree(str(folder))
    date_dir = folder.parent
    if date_dir.exists() and not any(date_dir.iterdir()):
        date_dir.rmdir()
