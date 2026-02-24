"""Tests for dashboard API — stats, last run with JTL stats, recent runs, disk usage, caching."""

import json

import pytest

from tests.conftest import make_jmx, make_result_folder


class TestDashboardStats:
    def test_returns_stats(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "jmx_count" in data
        assert "results_count" in data
        assert "slaves_count" in data
        assert "mode" in data
        assert data["mode"] in ("local", "distributed")

    def test_runner_fields(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/stats")
        data = r.json()
        assert "runner_active" in data
        assert "runner_label" in data

    def test_monitoring_urls(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/stats")
        data = r.json()
        assert "grafana_url" in data
        assert "influxdb_url" in data


class TestLastRun:
    def test_no_results(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/last-run")
        assert r.status_code == 200
        assert r.json()["last_run"] is None

    def test_with_result(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/last-run")
        assert r.status_code == 200
        lr = r.json()["last_run"]
        assert lr is not None
        assert lr["name"] == sample_result.name

    def test_includes_stats_when_jtl_exists(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/last-run")
        assert r.status_code == 200
        lr = r.json()["last_run"]
        assert lr is not None
        assert "stats" in lr
        stats = lr["stats"]
        assert "avg" in stats
        assert "p95" in stats
        assert "error_pct" in stats
        assert "throughput" in stats
        assert "total_samples" in stats
        assert stats["total_samples"] == 2  # 2 rows in sample JTL

    def test_stats_include_start_end_time(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/last-run")
        stats = r.json()["last_run"]["stats"]
        assert "start_time" in stats
        assert "end_time" in stats
        assert stats["start_time"] == 1708764000000
        assert stats["end_time"] == 1708764001000


class TestRecentRuns:
    def test_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/recent-runs")
        assert r.status_code == 200
        assert r.json()["runs"] == []

    def test_with_results(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/recent-runs")
        assert r.status_code == 200
        runs = r.json()["runs"]
        assert len(runs) >= 1
        run = runs[0]
        assert "name" in run
        assert "date" in run
        assert "has_jtl" in run

    def test_includes_stats(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/recent-runs")
        runs = r.json()["runs"]
        run = runs[0]
        assert "stats" in run
        stats = run["stats"]
        assert "total_samples" in stats
        assert "avg" in stats
        assert "p95" in stats
        assert "error_pct" in stats
        assert "throughput" in stats


class TestDiskUsage:
    def test_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/disk-usage")
        assert r.status_code == 200
        data = r.json()
        assert "total_bytes" in data
        assert "file_count" in data
        assert "folder_count" in data
        assert data["total_bytes"] >= 0

    def test_with_results(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/disk-usage")
        assert r.status_code == 200
        data = r.json()
        assert data["total_bytes"] > 0
        assert data["file_count"] > 0
        assert data["folder_count"] >= 1


class TestJtlCache:
    def test_cache_file_created(self, admin_client, bp, sample_result):
        """parse_jtl() should create a .summary.json cache file."""
        admin_client.get(f"{bp}/api/dashboard/last-run")
        cache = sample_result / "results.jtl.summary.json"
        assert cache.exists()
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert "overall" in data
        assert "transactions" in data
        assert "_jtl_mtime" in data  # internal cache key

    def test_cache_hit(self, admin_client, bp, sample_result):
        """Second call should use cache (returns same data)."""
        r1 = admin_client.get(f"{bp}/api/dashboard/last-run")
        r2 = admin_client.get(f"{bp}/api/dashboard/last-run")
        assert r1.json()["last_run"]["stats"] == r2.json()["last_run"]["stats"]

    def test_date_uses_jtl_timestamp(self, admin_client, bp, sample_result):
        """After cache is created, folder date should reflect JTL start time."""
        # First call creates the cache
        admin_client.get(f"{bp}/api/dashboard/last-run")
        # recent-runs reads _folder_info which checks cache for start_time
        r = admin_client.get(f"{bp}/api/dashboard/recent-runs")
        runs = r.json()["runs"]
        assert len(runs) >= 1
        # The date should be based on epoch 1708764000000 (from sample JTL)
        assert "2024-02-24" in runs[0]["date"]  # 1708764000000 = 2024-02-24


class TestAlerts:
    def test_no_alerts_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/dashboard/alerts")
        assert r.status_code == 200
        assert "alerts" in r.json()
        assert isinstance(r.json()["alerts"], list)

    def test_no_report_alert(self, admin_client, bp, tmp_project_dir):
        """Result with JTL but no report should trigger a warning."""
        import shutil
        results_dir = tmp_project_dir["project_root"] / "results"
        date_dir = results_dir / "20260225"
        date_dir.mkdir(parents=True, exist_ok=True)
        folder = date_dir / "20260225_1"
        folder.mkdir(exist_ok=True)
        jtl = (
            "timeStamp,elapsed,label,responseCode,responseMessage,threadName,"
            "dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,"
            "URL,Latency,IdleTime,Connect\n"
            "1708764000000,150,Login,200,OK,Thread-1,text,true,,1024,256,1,1,"
            "http://test/login,100,0,50\n"
        )
        (folder / "results.jtl").write_text(jtl, encoding="utf-8")
        try:
            r = admin_client.get(f"{bp}/api/dashboard/alerts")
            alerts = r.json()["alerts"]
            warnings = [a for a in alerts if "missing HTML report" in a["message"]]
            assert len(warnings) >= 1
        finally:
            shutil.rmtree(str(folder))
            if date_dir.exists() and not any(date_dir.iterdir()):
                date_dir.rmdir()

    def test_alerts_returns_list(self, admin_client, bp, sample_result):
        r = admin_client.get(f"{bp}/api/dashboard/alerts")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        # sample_result has both JTL and report, so no missing-report alert
        for a in data["alerts"]:
            assert "level" in a
            assert "message" in a


class TestSlaveHealth:
    def test_empty_cache(self, admin_client, bp):
        """Before any status check, slave health returns empty list."""
        r = admin_client.get(f"{bp}/api/dashboard/slave-health")
        assert r.status_code == 200
        assert "slaves" in r.json()
        assert isinstance(r.json()["slaves"], list)

    def test_cache_updates_after_status_check(self, admin_client, bp, monkeypatch, tmp_project_dir):
        """After calling slave status, health cache should be populated."""
        import routers.config as config_mod
        # Reset cache
        config_mod._last_slave_status = []

        # Mock check_all_slaves to return test data
        async def mock_check(ips, configs):
            return [{"ip": ip, "status": "up", "error": None} for ip in ips]

        monkeypatch.setattr("routers.config.check_all_slaves", mock_check)

        # Write a slave to slaves.txt
        slaves_path = tmp_project_dir["project_root"] / "slaves.txt"
        slaves_path.write_text(json.dumps([{"ip": "10.0.0.1", "enabled": True}]))

        r = admin_client.get(f"{bp}/api/slaves/status")
        assert r.status_code == 200

        # Now check cached health
        r2 = admin_client.get(f"{bp}/api/dashboard/slave-health")
        slaves = r2.json()["slaves"]
        assert len(slaves) >= 1
        assert slaves[0]["ip"] == "10.0.0.1"

        # Cleanup
        slaves_path.write_text("[]")
        config_mod._last_slave_status = []
