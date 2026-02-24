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


class TestJmeterProperties:
    def test_get_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/config/jmeter-properties")
        assert r.status_code == 200
        assert isinstance(r.json()["properties"], list)

    def test_put_and_get(self, admin_client, bp):
        props = [{"key": "server.rmi.ssl.disable", "value": "true", "enabled": True}]
        r = admin_client.put(f"{bp}/api/config/jmeter-properties", json={"properties": props})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify
        r2 = admin_client.get(f"{bp}/api/config/jmeter-properties")
        saved = r2.json()["properties"]
        assert len(saved) == 1
        assert saved[0]["key"] == "server.rmi.ssl.disable"
        # Cleanup
        admin_client.put(f"{bp}/api/config/jmeter-properties", json={"properties": []})


class TestDetectJmeter:
    def test_not_found(self, admin_client, bp, monkeypatch):
        monkeypatch.setattr(
            "routers.config.detect_jmeter_path", lambda: None
        )
        r = admin_client.post(f"{bp}/api/config/detect-jmeter")
        assert r.status_code == 404
