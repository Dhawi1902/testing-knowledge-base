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
        folders = data["folders"]
        names = [f["name"] for f in folders]
        assert "20260224_1" in names

    def test_includes_total(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/list")
        data = r.json()
        assert "total" in data
        assert data["total"] >= 1

    def test_includes_metrics(self, admin_client, bp, sample_result):
        """Results list should include metrics from run_summary.json."""
        r = admin_client.get(f"{bp}/api/results/list")
        data = r.json()
        folders = data["folders"]
        folder = next(f for f in folders if f["name"] == "20260224_1")
        assert "metrics" in folder
        m = folder["metrics"]
        assert "avg" in m
        assert "p95" in m
        assert "throughput" in m
        assert "total_samples" in m
        assert m["total_samples"] == 2

    def test_pagination(self, admin_client, bp, sample_result, second_result):
        """Pagination should slice results and return total."""
        r = admin_client.get(f"{bp}/api/results/list", params={"page": 1, "per_page": 1})
        data = r.json()
        assert data["total"] >= 2
        assert len(data["folders"]) == 1

    def test_pagination_page_2(self, admin_client, bp, sample_result, second_result):
        r = admin_client.get(f"{bp}/api/results/list", params={"page": 2, "per_page": 1})
        data = r.json()
        assert len(data["folders"]) == 1

    def test_search(self, admin_client, bp, sample_result, second_result):
        """Search by folder name substring."""
        r = admin_client.get(f"{bp}/api/results/list", params={"q": "20260224_1"})
        data = r.json()
        assert data["total"] == 1
        assert data["folders"][0]["name"] == "20260224_1"

    def test_search_no_match(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/list", params={"q": "nonexistent"})
        data = r.json()
        assert data["total"] == 0
        assert data["folders"] == []


class TestBulkDelete:
    def test_bulk_delete(self, admin_client, bp, tmp_project_dir):
        results_dir = tmp_project_dir["project_root"] / "results"
        f1 = make_result_folder(results_dir, "20260224_del1")
        f2 = make_result_folder(results_dir, "20260224_del2")
        r = admin_client.post(
            f"{bp}/api/results/bulk-delete",
            json={"folders": ["20260224_del1", "20260224_del2"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) == 2
        assert all(item["ok"] for item in data["results"])
        assert not f1.exists()
        assert not f2.exists()

    def test_bulk_delete_empty(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/results/bulk-delete", json={"folders": []})
        assert r.status_code == 400

    def test_bulk_delete_not_found(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/results/bulk-delete",
            json={"folders": ["nonexistent_folder"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["results"][0]["ok"] is False
        assert "Not found" in data["results"][0]["error"]


class TestResultStats:
    def test_stats(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        assert r.status_code == 200
        data = r.json()
        assert "overall" in data
        assert "transactions" in data
        assert data["overall"]["total_samples"] == 2
        assert data["overall"]["avg"] > 0

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/results/nonexistent_folder/stats")
        assert r.status_code == 404


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
        assert r.status_code == 404


class TestFilterInfo:
    def test_defaults(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/filter-info")
        assert r.status_code == 200
        data = r.json()
        assert "filter_sub_results" in data
        assert "label_pattern" in data
        assert data["filter_sub_results"] is True
        assert data["label_pattern"] == ""


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
    """F10: Stats preview — known-data assertions from 2-row JTL fixture."""

    def test_overall_and_transactions(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        assert r.status_code == 200
        data = r.json()
        assert "overall" in data
        assert "transactions" in data
        assert len(data["transactions"]) == 2  # Login + Dashboard

    def test_known_overall_stats(self, admin_client, bp, sample_result):
        """Verify exact stats computed from the 2-row JTL fixture."""
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        o = r.json()["overall"]
        assert o["total_samples"] == 2
        assert o["avg"] == 175.0
        assert o["min"] == 150
        assert o["max"] == 200
        assert o["error_count"] == 0
        assert o["error_pct"] == 0.0
        assert o["throughput"] == 2.0
        assert o["duration_sec"] == 1.0
        assert o["peak_vus"] == 1

    def test_known_transaction_stats(self, admin_client, bp, sample_result):
        """Verify per-transaction stats from known fixture data."""
        r = admin_client.get(f"{bp}/api/results/20260224_1/stats")
        txns = {t["label"]: t for t in r.json()["transactions"]}
        # Login: 150ms
        login = txns["Login"]
        assert login["samples"] == 1
        assert login["avg"] == 150.0
        assert login["min"] == 150
        assert login["max"] == 150
        assert login["error_count"] == 0
        # Dashboard: 200ms
        dash = txns["Dashboard"]
        assert dash["samples"] == 1
        assert dash["avg"] == 200.0
        assert dash["min"] == 200
        assert dash["max"] == 200


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

    def test_compare_includes_transaction_diff(self, admin_client, bp, sample_result, second_result):
        """Compare should include per-transaction breakdown."""
        r = admin_client.get(
            f"{bp}/api/results/compare",
            params={"folder1": "20260224_1", "folder2": "20260224_3"},
        )
        data = r.json()
        assert "transaction_diff" in data
        tx = data["transaction_diff"]
        assert isinstance(tx, list)
        assert len(tx) >= 2  # Login + Dashboard
        labels = [t["label"] for t in tx]
        assert "Login" in labels
        assert "Dashboard" in labels
        # Each entry should have diff metrics
        for t in tx:
            if t.get("a") and t.get("b"):
                assert "diff" in t
                assert "avg" in t["diff"]


class TestCompareKnownData:
    """Compare two identical JTL fixtures — diff should be zero."""

    def test_identical_runs_zero_diff(self, admin_client, bp, sample_result, second_result):
        r = admin_client.get(
            f"{bp}/api/results/compare",
            params={"folder1": "20260224_1", "folder2": "20260224_3"},
        )
        data = r.json()
        diff = data["diff"]
        # Same fixture → zero change_pct
        assert diff["avg"]["change_pct"] == 0.0
        assert diff["avg"]["a"] == 175.0
        assert diff["avg"]["b"] == 175.0
        assert diff["throughput"]["change_pct"] == 0.0
        assert diff["error_pct"]["change_pct"] == 0.0

    def test_compare_known_run_a_stats(self, admin_client, bp, sample_result, second_result):
        r = admin_client.get(
            f"{bp}/api/results/compare",
            params={"folder1": "20260224_1", "folder2": "20260224_3"},
        )
        data = r.json()
        a = data["run_a"]["overall"]
        assert a["total_samples"] == 2
        assert a["avg"] == 175.0
        assert a["min"] == 150
        assert a["max"] == 200


class TestJtlParserUnit:
    """Direct unit tests for jtl_parser.parse_jtl with known data."""

    def test_parse_jtl_known_data(self, tmp_path):
        from services.jtl_parser import parse_jtl

        jtl_content = (
            "timeStamp,elapsed,label,responseCode,responseMessage,threadName,"
            "dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,"
            "URL,Latency,IdleTime,Connect\n"
            "1708764000000,100,API_Call,200,OK,T-1,text,true,,512,128,1,1,"
            "http://test/api,80,0,30\n"
            "1708764001000,300,API_Call,200,OK,T-2,text,true,,512,128,2,2,"
            "http://test/api,200,0,40\n"
            "1708764002000,500,API_Call,500,Error,T-3,text,false,timeout,0,128,3,3,"
            "http://test/api,400,0,50\n"
        )
        jtl_path = tmp_path / "test.jtl"
        jtl_path.write_text(jtl_content)
        stats = parse_jtl(jtl_path)

        o = stats["overall"]
        assert o["total_samples"] == 3
        assert o["avg"] == 300.0
        assert o["min"] == 100
        assert o["max"] == 500
        assert o["error_count"] == 1
        assert round(o["error_pct"], 2) == 33.33
        assert o["peak_vus"] == 3

    def test_parse_jtl_empty_file(self, tmp_path):
        from services.jtl_parser import parse_jtl

        jtl_path = tmp_path / "empty.jtl"
        jtl_path.write_text(
            "timeStamp,elapsed,label,responseCode,responseMessage,"
            "threadName,dataType,success,failureMessage,bytes,sentBytes,"
            "grpThreads,allThreads,URL,Latency,IdleTime,Connect\n"
        )
        stats = parse_jtl(jtl_path)
        assert stats["overall"]["total_samples"] == 0

    def test_ensure_summary_creates_file(self, tmp_path):
        """ensure_summary should create run_summary.json on first call."""
        from services.jtl_parser import ensure_summary

        folder = tmp_path / "20260225_1"
        folder.mkdir()
        jtl_content = (
            "timeStamp,elapsed,label,responseCode,responseMessage,threadName,"
            "dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,"
            "URL,Latency,IdleTime,Connect\n"
            "1708764000000,100,Req,200,OK,T-1,text,true,,512,128,1,1,"
            "http://test,80,0,30\n"
        )
        (folder / "results.jtl").write_text(jtl_content)

        summary = ensure_summary(folder)
        assert summary is not None
        assert summary["stats"]["total_samples"] == 1
        assert summary["phase"] == "complete"
        assert (folder / "run_summary.json").exists()

    def test_ensure_summary_cached(self, tmp_path):
        """Second call should use cached run_summary.json."""
        from services.jtl_parser import ensure_summary
        import json

        folder = tmp_path / "20260225_2"
        folder.mkdir()
        (folder / "results.jtl").write_text(
            "timeStamp,elapsed,label,responseCode\n1708764000000,100,Req,200\n"
        )
        # Create pre-existing complete summary (cache hit)
        cached = {"phase": "complete", "stats": {"total_samples": 99}, "transactions": []}
        (folder / "run_summary.json").write_text(json.dumps(cached))

        summary = ensure_summary(folder)
        assert summary["stats"]["total_samples"] == 99  # Used cache, not re-parsed


class TestOllamaStatus:
    def test_status(self, admin_client, bp, monkeypatch):
        async def mock_check(base_url):
            return {"available": False, "error": "Connection refused"}
        monkeypatch.setattr("routers.results.check_ollama_status", mock_check)
        r = admin_client.get(f"{bp}/api/analysis/ollama-status")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is False
        assert data["error"] == "Connection refused"
