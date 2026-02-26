"""Tests for test plans API — JMX CRUD, presets, runner status."""

import json

import pytest

from tests.conftest import make_jmx


class TestListPlans:
    def test_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/list")
        assert r.status_code == 200

    def test_with_jmx(self, admin_client, bp, sample_jmx):
        r = admin_client.get(f"{bp}/api/plans/list")
        assert r.status_code == 200
        data = r.json()
        plans = data.get("plans", [])
        names = [p.get("filename", p.get("name", "")) for p in plans]
        assert "test.jmx" in names


class TestPlanParams:
    def test_extract_params(self, admin_client, bp, sample_jmx):
        r = admin_client.get(f"{bp}/api/plans/test.jmx/params")
        assert r.status_code == 200
        data = r.json()
        params = data.get("params", [])
        # params is a list of {"name": "...", "default": "..."}
        param_names = [p["name"] for p in params] if isinstance(params, list) else list(params.keys())
        assert "student" in param_names

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/missing.jmx/params")
        assert r.status_code == 404


class TestDownloadPlan:
    def test_download(self, admin_client, bp, sample_jmx):
        r = admin_client.get(f"{bp}/api/plans/test.jmx/download")
        assert r.status_code == 200
        assert b"jmeterTestPlan" in r.content

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/missing.jmx/download")
        assert r.status_code == 404


class TestUploadPlan:
    def test_upload(self, admin_client, bp, tmp_project_dir):
        jmx_content = b'<?xml version="1.0"?><jmeterTestPlan version="1.2"></jmeterTestPlan>'
        r = admin_client.post(
            f"{bp}/api/plans/upload",
            files={"file": ("new_plan.jmx", jmx_content, "application/xml")},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Cleanup
        f = tmp_project_dir["project_root"] / "test_plan" / "new_plan.jmx"
        if f.exists():
            f.unlink()

    def test_wrong_extension(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/plans/upload",
            files={"file": ("bad.xml", b"<xml/>", "application/xml")},
        )
        assert r.status_code == 400

    def test_duplicate(self, admin_client, bp, sample_jmx):
        jmx_content = b'<?xml version="1.0"?><jmeterTestPlan/>'
        r = admin_client.post(
            f"{bp}/api/plans/upload",
            files={"file": ("test.jmx", jmx_content, "application/xml")},
        )
        assert r.status_code == 409


class TestPresets:
    def test_list_empty(self, admin_client, bp, tmp_project_dir):
        # Ensure empty presets
        (tmp_project_dir["webapp_dir"] / "presets.json").write_text("{}")
        r = admin_client.get(f"{bp}/api/runner/presets")
        assert r.status_code == 200
        assert r.json()["presets"] == {}

    def test_save_and_list(self, admin_client, bp, tmp_project_dir):
        r = admin_client.post(
            f"{bp}/api/runner/presets",
            json={"name": "my_preset", "values": {"student": "20"}},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

        r = admin_client.get(f"{bp}/api/runner/presets")
        assert "my_preset" in r.json()["presets"]

    def test_delete(self, admin_client, bp, tmp_project_dir):
        # Ensure preset exists
        presets_file = tmp_project_dir["webapp_dir"] / "presets.json"
        presets_file.write_text(json.dumps({"to_delete": {"k": "v"}}))

        r = admin_client.delete(f"{bp}/api/runner/presets/to_delete")
        assert r.status_code == 200

        r = admin_client.get(f"{bp}/api/runner/presets")
        assert "to_delete" not in r.json()["presets"]

    def test_save_no_name(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/runner/presets",
            json={"name": "", "values": {}},
        )
        assert r.status_code == 400


class TestDeletePlan:
    def test_delete(self, admin_client, bp, sample_jmx):
        r = admin_client.delete(f"{bp}/api/plans/test.jmx")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_not_found(self, admin_client, bp):
        r = admin_client.delete(f"{bp}/api/plans/nonexistent.jmx")
        assert r.status_code == 404


class TestPreviewCommand:
    def test_preview(self, admin_client, bp, sample_jmx):
        r = admin_client.post(
            f"{bp}/api/runner/preview",
            json={"filename": "test.jmx", "overrides": {"student": "20"}},
        )
        assert r.status_code == 200
        assert "command" in r.json()


class TestDryRun:
    def test_dry_run_basic(self, admin_client, bp, sample_jmx):
        r = admin_client.post(
            f"{bp}/api/runner/dry-run",
            json={"filename": "test.jmx", "overrides": {"student": "20"}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "command" in data
        assert "result_dir" in data
        assert "post_commands" in data
        assert "test.jmx" in data["command"]

    def test_dry_run_no_dirs_created(self, admin_client, bp, sample_jmx, tmp_project_dir):
        """Dry run should NOT create result directories."""
        results_dir = tmp_project_dir["project_root"] / "results"
        before = set(results_dir.rglob("*")) if results_dir.exists() else set()
        admin_client.post(
            f"{bp}/api/runner/dry-run",
            json={"filename": "test.jmx", "overrides": {}},
        )
        after = set(results_dir.rglob("*")) if results_dir.exists() else set()
        assert after == before, "Dry run should not create any new files/dirs"

    def test_dry_run_with_filter(self, admin_client, bp, sample_jmx):
        r = admin_client.post(
            f"{bp}/api/runner/dry-run",
            json={
                "filename": "test.jmx",
                "overrides": {},
                "filter_sub_results": True,
                "label_pattern": "^HTTP",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["post_commands"]) > 0

    def test_dry_run_invalid_regex(self, admin_client, bp, sample_jmx):
        r = admin_client.post(
            f"{bp}/api/runner/dry-run",
            json={
                "filename": "test.jmx",
                "overrides": {},
                "filter_sub_results": True,
                "label_pattern": "[invalid",
            },
        )
        assert r.status_code == 400


class TestRunnerBuffer:
    def test_empty_buffer(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/runner/buffer")
        assert r.status_code == 200
        data = r.json()
        assert "lines" in data
        assert "running" in data
        assert isinstance(data["lines"], list)


class TestFilterConfig:
    def test_defaults(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/runner/filter-config")
        assert r.status_code == 200
        data = r.json()
        assert "filter_sub_results" in data
        assert "label_pattern" in data


class TestRunnerStatus:
    def test_idle(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/runner/status")
        assert r.status_code == 200
        data = r.json()
        assert data["running"] is False
        assert data["post_processing"] is False
        assert data["label"] == ""
        assert data["live_stats"] == {}

    def test_includes_live_stats(self, admin_client, bp):
        """Runner status should include live_stats field."""
        r = admin_client.get(f"{bp}/api/runner/status")
        assert r.status_code == 200
        data = r.json()
        assert "live_stats" in data
        assert isinstance(data["live_stats"], dict)

    def test_includes_post_processing(self, admin_client, bp):
        """Runner status should include post_processing field."""
        r = admin_client.get(f"{bp}/api/runner/status")
        assert r.status_code == 200
        data = r.json()
        assert "post_processing" in data
        assert data["post_processing"] is False


class TestLiveStatsParsing:
    """Test ProcessManager's JMeter summary line parsing."""

    def test_parse_summary_equals(self):
        """Cumulative 'summary =' lines should update live stats."""
        from services.process_manager import ProcessManager

        pm = ProcessManager()
        line = "summary =  10000 in 00:01:40 =  100.0/s Avg:   148 Min:     5 Max:  2400 Err:    45 (0.45%)"
        pm._parse_summary_line(line)
        stats = pm.live_stats
        assert stats["total_samples"] == 10000
        assert stats["throughput"] == 100.0
        assert stats["avg"] == 148
        assert stats["min"] == 5
        assert stats["max"] == 2400
        assert stats["error_count"] == 45
        assert stats["error_pct"] == 0.45

    def test_parse_summary_plus_ignored(self):
        """Incremental 'summary +' lines should NOT update live stats."""
        from services.process_manager import ProcessManager

        pm = ProcessManager()
        line = "summary +    500 in 00:00:05 =  100.0/s Avg:   120 Min:     3 Max:   800 Err:     2 (0.40%)"
        pm._parse_summary_line(line)
        stats = pm.live_stats
        assert stats == {}

    def test_parse_non_summary_line(self):
        """Non-summary lines should not affect live stats."""
        from services.process_manager import ProcessManager

        pm = ProcessManager()
        pm._parse_summary_line("Starting the test on 10.0.0.1")
        assert pm.live_stats == {}

    def test_regex_pattern(self):
        """Test the regex directly against various formats."""
        from services.process_manager import _SUMMARY_RE

        line = "summary =    200 in 00:00:10 =   20.0/s Avg:    50 Min:    10 Max:   300 Err:     0 (0.00%)"
        m = _SUMMARY_RE.search(line)
        assert m is not None
        assert m.group(1) == "200"
        assert m.group(2) == "20.0"
        assert m.group(3) == "50"
        assert m.group(6) == "0"
        assert m.group(7) == "0.00"


class TestJmxPatcher:
    """Test JMX XML patching for Backend Listener."""

    def test_patch_backend_listener(self, tmp_path):
        from services.jmx_patcher import patch_jmx

        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <BackendListener testname="Backend Listener">
      <stringProp name="influxdbUrl">http://localhost:8086</stringProp>
      <stringProp name="application">myapp</stringProp>
      <stringProp name="runId">default</stringProp>
    </BackendListener>
  </hashTree>
</jmeterTestPlan>"""
        jmx_path = tmp_path / "test.jmx"
        jmx_path.write_text(jmx_content)
        output = tmp_path / "patched.jmx"

        patch_jmx(jmx_path, {"runId": "20260225_1", "application": "patched_app"}, output)

        assert output.exists()
        content = output.read_text()
        assert "20260225_1" in content
        assert "patched_app" in content
        assert "http://localhost:8086" in content  # unchanged

    def test_no_patches_no_output(self, tmp_path):
        from services.jmx_patcher import patch_jmx

        jmx_path = tmp_path / "test.jmx"
        jmx_path.write_text('<?xml version="1.0"?><jmeterTestPlan/>')
        output = tmp_path / "patched.jmx"

        patch_jmx(jmx_path, {}, output)
        # Empty patches should return without writing
        assert not output.exists()

    def test_extract_csv_data_set_configs(self, tmp_path):
        from services.jmx_patcher import extract_csv_data_set_configs

        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <CSVDataSet testname="CSV Data">
      <stringProp name="CSVDataSet.filename">test_data/users.csv</stringProp>
      <stringProp name="CSVDataSet.variableNames">username,password</stringProp>
      <stringProp name="CSVDataSet.delimiter">,</stringProp>
    </CSVDataSet>
  </hashTree>
</jmeterTestPlan>"""
        jmx_path = tmp_path / "test.jmx"
        jmx_path.write_text(jmx_content)

        configs = extract_csv_data_set_configs(jmx_path)
        assert len(configs) == 1
        assert configs[0]["filename"] == "test_data/users.csv"
        assert configs[0]["variableNames"] == "username,password"

    def test_extract_backend_listener_props(self, tmp_path):
        from services.jmx_patcher import extract_backend_listener_props

        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <BackendListener testname="Backend Listener">
      <stringProp name="influxdbUrl">http://localhost:8086</stringProp>
      <stringProp name="application">myapp</stringProp>
    </BackendListener>
  </hashTree>
</jmeterTestPlan>"""
        jmx_path = tmp_path / "test.jmx"
        jmx_path.write_text(jmx_content)

        props = extract_backend_listener_props(jmx_path)
        assert len(props) == 1
        assert props[0]["influxdbUrl"] == "http://localhost:8086"
        assert props[0]["application"] == "myapp"


class TestWebSocketLogs:
    """WebSocket integration tests for /ws/runner/logs."""

    def test_no_active_test(self, admin_client, bp):
        """When no test is running, WS should send idle message and close."""
        with admin_client.websocket_connect(f"{bp}/ws/runner/logs") as ws:
            msg = ws.receive_text()
            assert "[No active test]" in msg

    def test_buffer_replay(self, admin_client, bp, monkeypatch):
        """Buffer endpoint returns current log lines and running state."""
        r = admin_client.get(f"{bp}/api/runner/buffer")
        assert r.status_code == 200
        data = r.json()
        assert data["running"] is False
        assert isinstance(data["lines"], list)
        assert len(data["lines"]) == 0
