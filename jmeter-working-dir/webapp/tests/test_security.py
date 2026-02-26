"""Security integration tests — path traversal rejection + viewer access denial."""

import pytest


# ====================================================================
# Path traversal tests — all should return 403 {"error": "Access denied"}
# ====================================================================

class TestPathTraversal:
    """Send traversal payloads to all safe_join-protected endpoints.

    HTTP URL normalization may resolve ../.. before routing (→ 404).
    Both 403 (safe_join rejection) and 404 (route mismatch) are valid
    rejections — the key assertion is: must NOT return 200 with content.
    """

    TRAVERSAL = "../../etc/passwd"

    def test_data_preview(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/data/preview/{self.TRAVERSAL}")
        assert r.status_code in (403, 404)

    def test_data_download(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/data/download/{self.TRAVERSAL}")
        assert r.status_code in (403, 404)

    def test_data_delete(self, admin_client, bp):
        r = admin_client.delete(f"{bp}/api/data/delete/{self.TRAVERSAL}")
        assert r.status_code in (403, 404)

    def test_data_rename_old(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": self.TRAVERSAL, "new": "safe.csv"},
        )
        assert r.status_code == 403

    def test_data_rename_new(self, admin_client, bp, sample_csv):
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": "test_users.csv", "new": self.TRAVERSAL},
        )
        assert r.status_code == 403

    def test_plans_params(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/{self.TRAVERSAL}/params")
        assert r.status_code in (403, 404)

    def test_plans_download(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/plans/{self.TRAVERSAL}/download")
        assert r.status_code in (403, 404)

    def test_results_report_path(self, admin_client, bp, sample_result):
        r = admin_client.get(
            f"{bp}/api/results/{sample_result.name}/report/{self.TRAVERSAL}"
        )
        assert r.status_code in (403, 404)


# ====================================================================
# Viewer access denial — all write endpoints should return 403
# ====================================================================

class TestViewerDenied:
    """Viewer (remote, no valid token) should be denied on all write ops."""

    # -- Settings --
    def test_settings_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/settings", json={"settings": {"theme": "light"}})
        assert r.status_code == 403

    def test_settings_report_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/settings/report", json={"settings": {}})
        assert r.status_code == 403

    # -- Config --
    def test_config_vm_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/vm", json={"config": {}})
        assert r.status_code == 403

    def test_config_slaves_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/slaves", json={"slaves": []})
        assert r.status_code == 403

    def test_config_project_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/project", json={})
        assert r.status_code == 403

    # -- Slaves --
    def test_slaves_start(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/start")
        assert r.status_code == 403

    def test_slaves_stop(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/stop")
        assert r.status_code == 403

    # -- Runner --
    def test_runner_start(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/runner/start", json={"plan": "test.jmx"})
        assert r.status_code == 403

    def test_runner_stop(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/runner/stop")
        assert r.status_code == 403

    def test_runner_dry_run(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/runner/dry-run", json={"filename": "test.jmx"})
        assert r.status_code == 403

    def test_presets_save(self, viewer_client, bp):
        r = viewer_client.post(
            f"{bp}/api/runner/presets",
            json={"name": "test", "values": {}},
        )
        assert r.status_code == 403

    def test_presets_delete(self, viewer_client, bp):
        r = viewer_client.delete(f"{bp}/api/runner/presets/test")
        assert r.status_code == 403

    def test_filter_presets_save(self, viewer_client, bp):
        r = viewer_client.post(
            f"{bp}/api/runner/filter-presets",
            json={"name": "test", "pattern": "^HTTP"},
        )
        assert r.status_code == 403

    def test_filter_presets_delete(self, viewer_client, bp):
        r = viewer_client.delete(f"{bp}/api/runner/filter-presets/test")
        assert r.status_code == 403

    # -- Plans --
    def test_plans_upload(self, viewer_client, bp):
        r = viewer_client.post(
            f"{bp}/api/plans/upload",
            files={"file": ("test.jmx", b"<xml/>", "application/xml")},
        )
        assert r.status_code == 403

    # -- Results --
    def test_results_delete(self, viewer_client, bp):
        r = viewer_client.delete(f"{bp}/api/results/some_folder")
        assert r.status_code == 403

    def test_results_regenerate(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/results/some_folder/regenerate", json={})
        assert r.status_code == 403

    # -- Data --
    def test_data_delete(self, viewer_client, bp):
        r = viewer_client.delete(f"{bp}/api/data/delete/test.csv")
        assert r.status_code == 403

    def test_data_rename(self, viewer_client, bp):
        r = viewer_client.post(
            f"{bp}/api/data/rename",
            json={"old_name": "a.csv", "new_name": "b.csv"},
        )
        assert r.status_code == 403

    def test_data_build(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/data/build", json={"columns": [], "filename": "t.csv"})
        assert r.status_code == 403

    def test_data_upload(self, viewer_client, bp):
        r = viewer_client.post(
            f"{bp}/api/data/upload",
            files={"file": ("test.csv", b"a,b\n1,2\n", "text/csv")},
        )
        assert r.status_code == 403

    def test_data_distribute(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/data/distribute", json={"files": [], "mode": "copy"})
        assert r.status_code == 403

    # -- F8: Individual slave start/stop --
    def test_slave_single_start(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/start")
        assert r.status_code == 403

    def test_slave_single_stop(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/stop")
        assert r.status_code == 403

    def test_slave_single_restart(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/restart")
        assert r.status_code == 403

    # -- #27: Test SSH --
    def test_slave_test_ssh(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/test-ssh")
        assert r.status_code == 403

    # -- #28: Test RMI --
    def test_slave_test_rmi(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/test-rmi")
        assert r.status_code == 403

    # -- #17: Provision --
    def test_slave_provision(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/provision")
        assert r.status_code == 403

    # -- #18: Provision status --
    def test_slave_provision_status(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/slaves/10.0.0.1/provision-status")
        assert r.status_code == 403

    # -- F11: Bulk regenerate --
    def test_bulk_regenerate(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/results/bulk-regenerate", json={"folders": []})
        assert r.status_code == 403

    # -- #10: Bulk delete --
    def test_bulk_delete(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/results/bulk-delete", json={"folders": ["test"]})
        assert r.status_code == 403

    # -- #11: Result label --
    def test_result_label(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/results/some_folder/label", json={"label": "test"})
        assert r.status_code == 403

    # -- Config properties --
    def test_config_properties_put(self, viewer_client, bp):
        r = viewer_client.put(f"{bp}/api/config/properties", json={"properties": {}})
        assert r.status_code == 403

    # -- Plans CRUD --
    def test_plans_delete(self, viewer_client, bp):
        r = viewer_client.delete(f"{bp}/api/plans/test.jmx")
        assert r.status_code == 403

    def test_plans_duplicate(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/plans/test.jmx/duplicate")
        assert r.status_code == 403

    def test_plans_rename(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/plans/test.jmx/rename", json={"new_name": "new.jmx"})
        assert r.status_code == 403

    # -- Settings export/import --
    def test_settings_export(self, viewer_client, bp):
        r = viewer_client.get(f"{bp}/api/settings/export")
        assert r.status_code == 403

    def test_settings_import(self, viewer_client, bp):
        r = viewer_client.post(f"{bp}/api/settings/import", json={"settings": {}})
        assert r.status_code == 403


# ====================================================================
# Viewer CAN read — read-only endpoints should be accessible
# ====================================================================

class TestViewerCanRead:
    """Viewer should be able to access read-only API endpoints."""

    def test_settings_get(self, viewer_client, bp):
        r = viewer_client.get(f"{bp}/api/settings")
        assert r.status_code == 200

    def test_plans_list(self, viewer_client, bp):
        r = viewer_client.get(f"{bp}/api/plans/list")
        assert r.status_code == 200

    def test_results_list(self, viewer_client, bp):
        r = viewer_client.get(f"{bp}/api/results/list")
        assert r.status_code == 200

    def test_data_files(self, viewer_client, bp):
        r = viewer_client.get(f"{bp}/api/data/files")
        assert r.status_code == 200


# ====================================================================
# Remote admin via token — write endpoints should succeed
# ====================================================================

class TestAuthedRemoteAdmin:
    """Remote user with valid token cookie should have admin access."""

    def test_settings_get(self, authed_remote_client, bp):
        r = authed_remote_client.get(f"{bp}/api/settings")
        assert r.status_code == 200

    def test_presets_list(self, authed_remote_client, bp):
        r = authed_remote_client.get(f"{bp}/api/runner/presets")
        assert r.status_code == 200
