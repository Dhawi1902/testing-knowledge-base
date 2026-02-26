"""Tests for config management API — VM config, slaves, project, properties."""

import json

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
