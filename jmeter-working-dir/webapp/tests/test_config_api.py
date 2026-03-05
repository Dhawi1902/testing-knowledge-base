"""Tests for config management API — VM config, slaves, project, properties."""

import json
from pathlib import Path

import pytest


class TestVmConfig:
    def test_get(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/config/vm")
        assert r.status_code == 200
        data = r.json()
        assert "config" in data
        assert "path" in data

    def test_put(self, admin_client, bp):
        new_config = {"ssh_config": {"user": "testuser", "password": "pass"}}
        r = admin_client.put(f"{bp}/api/config/vm", json={"config": new_config})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify it persisted
        r2 = admin_client.get(f"{bp}/api/config/vm")
        assert r2.json()["config"]["ssh_config"]["user"] == "testuser"
        # Cleanup — restore empty config
        admin_client.put(f"{bp}/api/config/vm", json={"config": {}})


class TestSlaves:
    def test_get(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/config/slaves")
        assert r.status_code == 200
        data = r.json()
        assert "slaves" in data
        assert isinstance(data["slaves"], list)

    def test_put(self, admin_client, bp):
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        r = admin_client.put(f"{bp}/api/config/slaves", json={"slaves": slaves})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify
        r2 = admin_client.get(f"{bp}/api/config/slaves")
        assert len(r2.json()["slaves"]) == 1
        # Cleanup
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestProject:
    def test_get(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/config/project")
        assert r.status_code == 200
        data = r.json()
        assert "config" in data
        assert data["config"]["name"] == "TestProject"


class TestProperties:
    def test_get(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/config/properties")
        assert r.status_code == 200
        data = r.json()
        assert "properties" in data
        assert isinstance(data["properties"], dict)
        # Fixture writes test_plan=test.jmx and student=10
        assert data["properties"]["test_plan"] == "test.jmx"
        assert data["properties"]["student"] == "10"

    def test_put(self, admin_client, bp):
        new_props = {"test_plan": "updated.jmx", "rampUp": "60", "loop": "3"}
        r = admin_client.put(f"{bp}/api/config/properties", json={"properties": new_props})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify persisted
        r2 = admin_client.get(f"{bp}/api/config/properties")
        saved = r2.json()["properties"]
        assert saved["test_plan"] == "updated.jmx"
        assert saved["rampUp"] == "60"
        assert saved["loop"] == "3"
        # Key from original fixture (student) should be gone since PUT replaces all
        assert "student" not in saved
        # Cleanup — restore original
        admin_client.put(f"{bp}/api/config/properties", json={"properties": {"test_plan": "test.jmx", "student": "10"}})


class TestDetectJmeter:
    def test_not_found(self, admin_client, bp, monkeypatch):
        monkeypatch.setattr(
            "routers.config.detect_jmeter_path", lambda: None
        )
        r = admin_client.post(f"{bp}/api/config/detect-jmeter")
        assert r.status_code == 404


class TestBuildSshConfigs:
    """Unit tests for build_ssh_configs() — slave_dir, heap, overrides."""

    def test_default_slave_dir(self):
        from services.slaves import build_ssh_configs
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        vm_config = {}
        configs = build_ssh_configs(slaves, vm_config)
        cfg = configs["10.0.0.1"]
        assert cfg["slave_dir"] == "~/jmeter-slave"
        assert cfg["dest_path"] == "~/jmeter-slave/test_data/"
        assert cfg["jmeter_scripts"]["start"] == "~/jmeter-slave/start-slave.sh"
        assert cfg["jmeter_scripts"]["stop"] == "~/jmeter-slave/stop-slave.sh"

    def test_custom_slave_dir(self):
        from services.slaves import build_ssh_configs
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        vm_config = {"slave_dir": "~/custom-dir"}
        configs = build_ssh_configs(slaves, vm_config)
        cfg = configs["10.0.0.1"]
        assert cfg["slave_dir"] == "~/custom-dir"
        assert cfg["dest_path"] == "~/custom-dir/test_data/"

    def test_per_slave_slave_dir_override(self):
        from services.slaves import build_ssh_configs
        slaves = [
            {"ip": "10.0.0.1", "enabled": True, "overrides": {"slave_dir": "~/override-dir"}},
            {"ip": "10.0.0.2", "enabled": True},
        ]
        vm_config = {"slave_dir": "~/jmeter-slave"}
        configs = build_ssh_configs(slaves, vm_config)
        assert configs["10.0.0.1"]["slave_dir"] == "~/override-dir"
        assert configs["10.0.0.1"]["dest_path"] == "~/override-dir/test_data/"
        assert configs["10.0.0.2"]["slave_dir"] == "~/jmeter-slave"

    def test_explicit_dest_path_not_overridden(self):
        """If dest_path is explicitly set in ssh_config, slave_dir should not override it."""
        from services.slaves import build_ssh_configs
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        vm_config = {
            "ssh_config": {"dest_path": "/custom/explicit/path/"},
            "slave_dir": "~/jmeter-slave",
        }
        configs = build_ssh_configs(slaves, vm_config)
        assert configs["10.0.0.1"]["dest_path"] == "/custom/explicit/path/"

    def test_explicit_scripts_preserved(self):
        """If jmeter_scripts is explicitly set, slave_dir should not override it."""
        from services.slaves import build_ssh_configs
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        vm_config = {
            "jmeter_scripts": {"start": "/custom/start.sh", "stop": "/custom/stop.sh"},
        }
        configs = build_ssh_configs(slaves, vm_config)
        assert configs["10.0.0.1"]["jmeter_scripts"]["start"] == "/custom/start.sh"

    def test_heap_settings_merged(self):
        from services.slaves import build_ssh_configs
        slaves = [{"ip": "10.0.0.1", "enabled": True}]
        vm_config = {"jmeter_heap": {"xms": "512m", "xmx": "2g", "gc_algo": "-XX:+UseG1GC"}}
        configs = build_ssh_configs(slaves, vm_config)
        assert configs["10.0.0.1"]["jmeter_heap"]["xms"] == "512m"
        assert configs["10.0.0.1"]["jmeter_heap"]["xmx"] == "2g"

    def test_per_slave_heap_override(self):
        from services.slaves import build_ssh_configs
        slaves = [
            {"ip": "10.0.0.1", "enabled": True, "overrides": {"jmeter_heap": {"xmx": "4g"}}},
        ]
        vm_config = {"jmeter_heap": {"xms": "512m", "xmx": "2g"}}
        configs = build_ssh_configs(slaves, vm_config)
        assert configs["10.0.0.1"]["jmeter_heap"]["xms"] == "512m"
        assert configs["10.0.0.1"]["jmeter_heap"]["xmx"] == "4g"


class TestGenerateScripts:
    """Unit tests for script generation (#20)."""

    def test_start_script_default_heap(self):
        from services.slaves import generate_start_script
        ssh_config = {"slave_dir": "~/jmeter-slave"}
        script = generate_start_script(ssh_config)
        assert "#!/bin/bash" in script
        assert "JMETER_HOME=" in script
        assert "-Xms512m" in script
        assert "-Xmx1g" in script
        assert "~/jmeter-slave/jmeter-slave.log" in script
        assert "jmeter-server" in script

    def test_start_script_custom_heap(self):
        from services.slaves import generate_start_script
        ssh_config = {
            "slave_dir": "~/custom-dir",
            "jmeter_heap": {"xms": "1g", "xmx": "4g", "gc_algo": "-XX:+UseZGC"},
        }
        script = generate_start_script(ssh_config)
        assert "-Xms1g" in script
        assert "-Xmx4g" in script
        assert "-XX:+UseZGC" in script
        assert "~/custom-dir/jmeter-slave.log" in script

    def test_stop_script(self):
        from services.slaves import generate_stop_script
        script = generate_stop_script()
        assert "#!/bin/bash" in script
        assert "pkill -f" in script
        assert "jmeter-server" in script


class TestTestSshEndpoint:
    """API tests for test-ssh endpoint (#27)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/test-ssh")
        assert r.status_code == 404

    def test_with_slave(self, admin_client, bp, monkeypatch):
        """Mock SSH test to verify endpoint wiring."""
        import asyncio
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.test_ssh_connection",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "message": "SSH connection successful"}),
        )
        # Add a slave first
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/test-ssh")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True
        # Cleanup
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestTestRmiEndpoint:
    """API tests for test-rmi endpoint (#28)."""

    def test_rmi_mock(self, admin_client, bp, monkeypatch):
        """Mock RMI port test to verify endpoint wiring."""
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.test_rmi_port",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "message": "Port 1099 is open"}),
        )
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/test-rmi")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True


class TestRmiPortUnit:
    """Unit test for _test_rmi_port function (#28)."""

    def test_closed_port(self):
        from services.slaves import _test_rmi_port
        # 10.255.255.1 is non-routable, so port should be unreachable
        result = _test_rmi_port("10.255.255.1", 1099, timeout=1)
        assert result["ok"] is False
        assert result["ip"] == "10.255.255.1"


class TestProvisionEndpoint:
    """API tests for provision endpoint (#17)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/provision")
        assert r.status_code == 404

    def test_with_slave_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        mock_result = {
            "ip": "10.0.0.1", "ok": True,
            "steps": [{"name": "Java 17", "ok": True, "detail": "Already installed"}],
            "status": {"java": True, "jmeter": True, "scripts": True, "firewall": True},
        }
        monkeypatch.setattr(
            "routers.config.provision_slave",
            AsyncMock(return_value=mock_result),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/provision")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True
        assert r.json()["result"]["status"]["java"] is True
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestProvisionStatusEndpoint:
    """API tests for provision-status endpoint (#18)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/provision-status")
        assert r.status_code == 404

    def test_with_slave_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        mock_result = {
            "ip": "10.0.0.1", "ok": True,
            "status": {"java": True, "jmeter": False, "scripts": False, "firewall": True},
        }
        monkeypatch.setattr(
            "routers.config.check_provision_status",
            AsyncMock(return_value=mock_result),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/provision-status")
        assert r.status_code == 200
        status = r.json()["result"]["status"]
        assert status["java"] is True
        assert status["jmeter"] is False
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestSyncDataEndpoint:
    """API tests for sync data endpoint (#29)."""

    def test_preview(self, admin_client, bp, sample_csv):
        """Preview shows CSV files and active slaves."""
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.get(f"{bp}/api/slaves/sync-data/preview")
        assert r.status_code == 200
        data = r.json()
        assert "files" in data
        assert "slaves" in data
        assert len(data["files"]) >= 1
        assert "10.0.0.1" in data["slaves"]
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_preview_no_slaves(self, admin_client, bp, sample_csv):
        """Preview with no active slaves returns empty slave list."""
        r = admin_client.get(f"{bp}/api/slaves/sync-data/preview")
        assert r.status_code == 200
        assert r.json()["slaves"] == []

    def test_sync_no_files(self, admin_client, bp):
        """Sync with no CSV files returns 400."""
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/sync-data")
        assert r.status_code == 400
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_sync_no_slaves(self, admin_client, bp, sample_csv):
        """Sync with no active slaves returns 400."""
        r = admin_client.post(f"{bp}/api/slaves/sync-data")
        assert r.status_code == 400
        assert "No active slaves" in r.json()["error"]

    def test_sync_mock(self, admin_client, bp, sample_csv, monkeypatch):
        """Mock distribute to verify endpoint wiring."""
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.distribute_files",
            AsyncMock(return_value=[{"ip": "10.0.0.1", "file": "test_users.csv", "ok": True, "detail": "uploaded"}]),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/sync-data")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert "1/1" in r.json()["summary"]
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestSlaveLogEndpoint:
    """API tests for slave log endpoint (#22)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/slaves/10.99.99.99/log")
        assert r.status_code == 404

    def test_with_slave_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.fetch_slave_log",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "log": "log content here\n", "path": "~/jmeter-slave/jmeter-slave.log"}),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.get(f"{bp}/api/slaves/10.0.0.1/log")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True
        assert "log content" in r.json()["result"]["log"]
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})


class TestCleanDataEndpoint:
    """API tests for clean data endpoint (#32)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/clean-data")
        assert r.status_code == 404

    def test_with_slave_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.clean_slave_data",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "files_removed": 3}),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/clean-data")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True
        assert r.json()["result"]["files_removed"] == 3
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_bulk(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.clean_slave_data",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "files_removed": 2}),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/bulk-clean-data", json={"ips": ["10.0.0.1"]})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_bulk_no_ips(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/bulk-clean-data", json={"ips": []})
        assert r.status_code == 400


class TestCleanLogEndpoint:
    """API tests for clean log endpoint (#33)."""

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/clean-log")
        assert r.status_code == 404

    def test_with_slave_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.clean_slave_log",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "bytes_cleared": 10240}),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/10.0.0.1/clean-log")
        assert r.status_code == 200
        assert r.json()["result"]["ok"] is True
        assert r.json()["result"]["bytes_cleared"] == 10240
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_bulk(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.clean_slave_log",
            AsyncMock(return_value={"ip": "10.0.0.1", "ok": True, "bytes_cleared": 5000}),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.post(f"{bp}/api/slaves/bulk-clean-logs", json={"ips": ["10.0.0.1"]})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_bulk_no_ips(self, admin_client, bp):
        r = admin_client.post(f"{bp}/api/slaves/bulk-clean-logs", json={"ips": []})
        assert r.status_code == 400


class TestHealthHistoryService:
    """Unit tests for health history persistence (#31)."""

    def test_load_empty(self, tmp_project_dir):
        from services.health_history import load_health_history
        config_dir = tmp_project_dir["project_root"] / "config"
        # Remove if exists
        hist_path = config_dir / "health_history.json"
        if hist_path.exists():
            hist_path.unlink()
        history = load_health_history(config_dir)
        assert history == {}

    def test_record_and_load(self, tmp_project_dir):
        from services.health_history import record_status_check, load_health_history
        config_dir = tmp_project_dir["project_root"] / "config"
        status_results = [
            {"ip": "10.0.0.1", "status": "up"},
            {"ip": "10.0.0.2", "status": "down"},
        ]
        history = record_status_check(config_dir, status_results)
        assert "10.0.0.1" in history
        assert "10.0.0.2" in history
        assert history["10.0.0.1"][-1]["status"] == "up"
        assert history["10.0.0.2"][-1]["status"] == "down"
        assert "timestamp" in history["10.0.0.1"][-1]
        # Verify persistence
        loaded = load_health_history(config_dir)
        assert len(loaded["10.0.0.1"]) == len(history["10.0.0.1"])
        # Cleanup
        (config_dir / "health_history.json").unlink(missing_ok=True)

    def test_record_with_resources(self, tmp_project_dir):
        from services.health_history import record_status_check, load_health_history
        config_dir = tmp_project_dir["project_root"] / "config"
        status_results = [{"ip": "10.0.0.1", "status": "up"}]
        resource_data = {"10.0.0.1": {"ok": True, "cpu_percent": 55.0, "ram_percent": 72.3}}
        history = record_status_check(config_dir, status_results, resource_data)
        entry = history["10.0.0.1"][-1]
        assert entry["cpu_percent"] == 55.0
        assert entry["ram_percent"] == 72.3
        # Cleanup
        (config_dir / "health_history.json").unlink(missing_ok=True)

    def test_max_entries(self, tmp_project_dir):
        from services.health_history import record_status_check, load_health_history, MAX_ENTRIES
        config_dir = tmp_project_dir["project_root"] / "config"
        # Record more than MAX_ENTRIES
        for i in range(MAX_ENTRIES + 10):
            record_status_check(config_dir, [{"ip": "10.0.0.1", "status": "up"}])
        loaded = load_health_history(config_dir)
        assert len(loaded["10.0.0.1"]) == MAX_ENTRIES
        # Cleanup
        (config_dir / "health_history.json").unlink(missing_ok=True)


class TestHealthHistoryEndpoint:
    """API tests for health history endpoints (#31)."""

    def test_get_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/slaves/health-history")
        assert r.status_code == 200
        assert isinstance(r.json()["history"], dict)

    def test_clear(self, admin_client, bp):
        r = admin_client.delete(f"{bp}/api/slaves/health-history")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_status_check_records_history(self, admin_client, bp, monkeypatch):
        """Verify status check records to health history."""
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.check_all_slaves",
            AsyncMock(return_value=[{"ip": "10.0.0.1", "status": "up"}]),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        # Trigger status check
        r = admin_client.get(f"{bp}/api/slaves/status")
        assert r.status_code == 200
        # Check history was recorded
        r2 = admin_client.get(f"{bp}/api/slaves/health-history")
        history = r2.json()["history"]
        assert "10.0.0.1" in history
        assert len(history["10.0.0.1"]) >= 1
        assert history["10.0.0.1"][-1]["status"] == "up"
        # Cleanup
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})
        admin_client.delete(f"{bp}/api/slaves/health-history")


class TestJmeterPropertiesCatalog:
    """Tests for the static JMeter properties catalog JSON."""

    def test_catalog_json_loads(self):
        """Static catalog JSON file loads and contains entries."""
        import json
        catalog_path = Path(__file__).resolve().parent.parent / "static" / "data" / "jmeter_properties_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        assert isinstance(catalog, list)
        assert len(catalog) > 200  # official docs have ~260 properties

    def test_catalog_entry_structure(self):
        """Each catalog entry has required keys."""
        import json
        catalog_path = Path(__file__).resolve().parent.parent / "static" / "data" / "jmeter_properties_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        for entry in catalog:
            assert "key" in entry
            assert "default" in entry
            assert "description" in entry
            assert "category" in entry

    def test_catalog_has_known_properties(self):
        """Catalog contains well-known JMeter properties."""
        import json
        catalog_path = Path(__file__).resolve().parent.parent / "static" / "data" / "jmeter_properties_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        keys = {e["key"] for e in catalog}
        assert "remote_hosts" in keys
        assert "server.rmi.ssl.disable" in keys
        assert "jmeter.save.saveservice.output_format" in keys

    def test_catalog_no_duplicates(self):
        """Catalog has no duplicate keys."""
        import json
        catalog_path = Path(__file__).resolve().parent.parent / "static" / "data" / "jmeter_properties_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        keys = [e["key"] for e in catalog]
        assert len(keys) == len(set(keys))


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

        try:
            r = admin_client.get(f"{bp}/api/config/jmeter-properties/master")
            assert r.status_code == 200
            data = r.json()
            assert "properties" in data
            assert data["properties"].get("server.rmi.ssl.disable") == "true"
        finally:
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

        try:
            new_props = {"server.rmi.ssl.disable": "true", "remote_hosts": "10.0.0.1,10.0.0.2"}
            r = admin_client.put(f"{bp}/api/config/jmeter-properties/master", json={"properties": new_props})
            assert r.status_code == 200
            assert r.json()["ok"] is True
            # Verify persisted
            r2 = admin_client.get(f"{bp}/api/config/jmeter-properties/master")
            saved = r2.json()["properties"]
            assert saved["server.rmi.ssl.disable"] == "true"
            assert saved["remote_hosts"] == "10.0.0.1,10.0.0.2"
        finally:
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
        assert isinstance(r.json()["properties"], dict)

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

    def test_catalog_returns_list(self, admin_client, bp):
        """GET catalog returns the static property catalog."""
        r = admin_client.get(f"{bp}/api/config/jmeter-properties/catalog")
        assert r.status_code == 200
        data = r.json()
        assert "catalog" in data
        assert isinstance(data["catalog"], list)
        assert len(data["catalog"]) > 200

    def test_catalog_has_expected_keys(self, admin_client, bp):
        """Catalog entries have correct structure."""
        r = admin_client.get(f"{bp}/api/config/jmeter-properties/catalog")
        catalog = r.json()["catalog"]
        entry = catalog[0]
        assert "key" in entry
        assert "default" in entry
        assert "description" in entry
        assert "category" in entry


class TestSlaveIPValidation:
    """All slave endpoints must reject invalid IP addresses (#14)."""

    INVALID_IPS = ["not-an-ip", "999.999.999.999", "abc", "10.0.0"]
    INJECTION_IPS = [";rm%20-rf", "$(whoami)", "10.0.0.1;ls"]

    # Every {ip}-parameterized endpoint and its HTTP method
    ENDPOINTS = [
        ("post", "/api/slaves/{ip}/start"),
        ("post", "/api/slaves/{ip}/stop"),
        ("post", "/api/slaves/{ip}/restart"),
        ("post", "/api/slaves/{ip}/test-ssh"),
        ("post", "/api/slaves/{ip}/test-rmi"),
        ("post", "/api/slaves/{ip}/provision"),
        ("post", "/api/slaves/{ip}/provision-status"),
        ("get",  "/api/slaves/{ip}/log"),
        ("post", "/api/slaves/{ip}/clean-data"),
        ("post", "/api/slaves/{ip}/clean-log"),
        ("get",  "/api/slaves/{ip}/resources"),
    ]

    def test_invalid_ip_rejected(self, admin_client, bp):
        """Non-IP strings are rejected with 400."""
        r = admin_client.post(f"{bp}/api/slaves/not-an-ip/start")
        assert r.status_code == 400
        assert "Invalid IP" in r.json()["error"]

    def test_injection_ip_rejected(self, admin_client, bp):
        """Shell injection attempts are rejected."""
        r = admin_client.post(f"{bp}/api/slaves/;rm%20-rf/start")
        assert r.status_code in (400, 404, 422)

    def test_all_endpoints_reject_invalid_ip(self, admin_client, bp):
        """Every {ip}-parameterized endpoint rejects an invalid IP with 400."""
        bad_ip = "not-an-ip"
        for method, path in self.ENDPOINTS:
            url = f"{bp}{path.replace('{ip}', bad_ip)}"
            r = getattr(admin_client, method)(url)
            assert r.status_code == 400, f"{method.upper()} {path} accepted invalid IP (got {r.status_code})"

    def test_valid_ip_passes_validation(self, admin_client, bp):
        """A valid IP passes validation (may 404 if slave not configured, but not 400)."""
        r = admin_client.post(f"{bp}/api/slaves/10.99.99.99/start")
        assert r.status_code != 400  # should be 404 (slave not found), not 400


class TestResourceMonitoringEndpoint:
    """API tests for resource monitoring endpoint (#30)."""

    def test_single_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/slaves/10.99.99.99/resources")
        assert r.status_code == 404

    def test_single_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.get_slave_resources",
            AsyncMock(return_value={
                "ip": "10.0.0.1", "ok": True,
                "cpu_percent": 45.2, "ram_percent": 62.1,
                "ram_used_mb": 1200, "ram_total_mb": 1932,
            }),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.get(f"{bp}/api/slaves/10.0.0.1/resources")
        assert r.status_code == 200
        result = r.json()["result"]
        assert result["ok"] is True
        assert result["cpu_percent"] == 45.2
        assert result["ram_percent"] == 62.1
        assert result["ram_used_mb"] == 1200
        assert result["ram_total_mb"] == 1932
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})

    def test_all_no_slaves(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/slaves/resources")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_all_mock(self, admin_client, bp, monkeypatch):
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "routers.config.get_all_slave_resources",
            AsyncMock(return_value=[
                {"ip": "10.0.0.1", "ok": True, "cpu_percent": 30.0, "ram_percent": 50.0,
                 "ram_used_mb": 512, "ram_total_mb": 1024},
            ]),
        )
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": [{"ip": "10.0.0.1", "enabled": True}]})
        r = admin_client.get(f"{bp}/api/slaves/resources")
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["cpu_percent"] == 30.0
        admin_client.put(f"{bp}/api/config/slaves", json={"slaves": []})
