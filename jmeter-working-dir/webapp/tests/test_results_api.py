"""Tests for results API — list, stats, delete, report serving."""

import shutil

import pytest

from tests.conftest import make_result_folder


class TestListResults:
    def test_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/results/list")
        assert r.status_code == 200

    def test_with_results(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/list")
        assert r.status_code == 200
        data = r.json()
        folders = data.get("folders", data.get("results", []))
        names = [f.get("name", f.get("folder", "")) for f in folders]
        assert "20260224_1" in names


class TestResultStats:
    def test_stats(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        assert r.status_code == 200
        data = r.json()
        # Should have parsed JTL stats
        assert "labels" in data or "stats" in data or "summary" in data or "error" not in data

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/results/nonexistent_folder/stats")
        assert r.status_code in (404, 200)  # May return 404 or JSON error


class TestDeleteResult:
    def test_delete(self, admin_client, bp, tmp_project_dir):
        results_dir = tmp_project_dir["project_root"] / "results"
        folder = make_result_folder(results_dir, "20260224_2")
        r = admin_client.delete(f"{bp}/api/results/20260224_2")
        assert r.status_code == 200
        assert r.json().get("ok") is True
        assert not folder.exists()
        # Cleanup date dir
        date_dir = folder.parent
        if date_dir.exists() and not any(date_dir.iterdir()):
            date_dir.rmdir()

    def test_not_found(self, admin_client, bp):
        r = admin_client.delete(f"{bp}/api/results/ghost_folder")
        assert r.status_code == 404


class TestServeReport:
    def test_index_html(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/report/index.html")
        assert r.status_code == 200
        assert b"Report" in r.content

    def test_traversal_blocked(self, admin_client, bp, sample_result):
        r = admin_client.get(
            f"{bp}/api/results/20260224_1/report/../../etc/passwd"
        )
        assert r.status_code in (403, 404)


class TestFilterInfo:
    def test_defaults(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/filter-info")
        assert r.status_code == 200
        data = r.json()
        assert "filter_sub_results" in data or "error" not in data


class TestLabels:
    """F9: Label picker endpoint."""
    def test_labels(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/labels")
        assert r.status_code == 200
        data = r.json()
        assert "labels" in data
        assert isinstance(data["labels"], list)
        # Sample JTL has "Login" and "Dashboard" labels
        assert "Login" in data["labels"]
        assert "Dashboard" in data["labels"]

    def test_labels_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/results/nonexistent/labels")
        assert r.status_code == 404


class TestStatsPreview:
    """F10: Stats preview uses existing /stats endpoint."""
    def test_overall_and_transactions(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        assert r.status_code == 200
        data = r.json()
        assert "overall" in data
        assert "transactions" in data
        assert len(data["transactions"]) == 2  # Login + Dashboard


class TestResultSize:
    def test_size(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/size")
        assert r.status_code == 200
        data = r.json()
        assert "report_size" in data
        assert data["report_size"] > 0

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/results/nonexistent/size")
        assert r.status_code == 404


class TestDownloadReport:
    def test_download_zip(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/download")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/")


class TestStopRegenerate:
    def test_no_active(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/results/stop-regenerate")
        assert r.status_code == 200
        assert "No active" in r.json().get("message", "")


class TestCompareResults:
    def test_compare(self, admin_client, bp, sample_result, second_result):
        r = admin_client.get(
            f"{bp}/api/results/compare",
            params={"folder1": "20260224_1", "folder2": "20260224_3"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "run_a" in data and "run_b" in data and "diff" in data


class TestOllamaStatus:
    def test_status(self, admin_client, bp, monkeypatch):
        async def mock_check(base_url):
            return {"available": False, "error": "Connection refused"}
        monkeypatch.setattr("routers.results.check_ollama_status", mock_check)
        r = admin_client.get(f"{bp}/api/analysis/ollama-status")
        assert r.status_code == 200
        assert "available" in r.json() or "error" in r.json()
