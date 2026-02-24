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
        assert r.status_code in (403, 404)


class TestDownloadPlan:
    def test_download(self, admin_client, bp, sample_jmx):
        r = admin_client.get(f"{bp}/api/plans/test.jmx/download")
        assert r.status_code == 200
        assert b"jmeterTestPlan" in r.content

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/missing.jmx/download")
        assert r.status_code in (403, 404)


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
        assert r.status_code in (403, 404)


class TestPreviewCommand:
    def test_preview(self, admin_client, bp, sample_jmx):
        r = admin_client.post(
            f"{bp}/api/runner/preview",
            json={"filename": "test.jmx", "overrides": {"student": "20"}},
        )
        assert r.status_code == 200
        assert "command" in r.json()


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
        assert data.get("running") is False or data.get("status") != "running"
