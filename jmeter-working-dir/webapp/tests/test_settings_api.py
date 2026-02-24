"""Tests for settings API — GET/PUT, token hashing, redaction, system info."""

import json

import pytest

from services.auth import hash_token


class TestGetSettings:
    def test_returns_200(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert "settings" in data

    def test_has_defaults(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings")
        s = r.json()["settings"]
        assert "theme" in s
        assert "server" in s
        assert "auth" in s

    def test_token_redacted_when_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings")
        auth = r.json()["settings"]["auth"]
        assert "token" not in auth
        assert "token_set" in auth
        assert auth["token_set"] is False

    def test_token_redacted_when_set(self, admin_client, bp, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("secret")
        sp.write_text(json.dumps(settings, indent=2))

        r = admin_client.get(f"{bp}/api/settings")
        auth = r.json()["settings"]["auth"]
        assert "token" not in auth
        assert auth["token_set"] is True

        # Cleanup
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))


class TestPutSettings:
    def test_save_theme(self, admin_client, bp, tmp_project_dir):
        r = admin_client.put(
            f"{bp}/api/settings",
            json={"settings": {"theme": "light"}},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

        saved = json.loads(tmp_project_dir["settings_path"].read_text())
        assert saved["theme"] == "light"

    def test_new_token_is_hashed(self, admin_client, bp, tmp_project_dir):
        r = admin_client.put(
            f"{bp}/api/settings",
            json={"settings": {"auth": {"token": "my-new-token"}}},
        )
        assert r.status_code == 200

        saved = json.loads(tmp_project_dir["settings_path"].read_text())
        stored = saved["auth"]["token"]
        assert stored == hash_token("my-new-token")
        assert len(stored) == 64

        # Cleanup
        saved["auth"]["token"] = ""
        tmp_project_dir["settings_path"].write_text(json.dumps(saved, indent=2))

    def test_empty_token_preserves_existing(self, admin_client, bp, tmp_project_dir):
        # Set a token first
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("existing-token")
        sp.write_text(json.dumps(settings, indent=2))

        # PUT with empty token — should preserve
        r = admin_client.put(
            f"{bp}/api/settings",
            json={"settings": {"auth": {"token": ""}}},
        )
        assert r.status_code == 200

        saved = json.loads(sp.read_text())
        assert saved["auth"]["token"] == hash_token("existing-token")

        # Cleanup
        saved["auth"]["token"] = ""
        sp.write_text(json.dumps(saved, indent=2))

    def test_clear_token(self, admin_client, bp, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("some-token")
        sp.write_text(json.dumps(settings, indent=2))

        r = admin_client.put(
            f"{bp}/api/settings",
            json={"settings": {"auth": {"token": "", "clear_token": True}}},
        )
        assert r.status_code == 200

        saved = json.loads(sp.read_text())
        assert saved["auth"]["token"] == ""


class TestSystemInfo:
    def test_returns_system_info(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings/system-info")
        assert r.status_code == 200
        data = r.json()
        assert "python" in data
        assert "os" in data
        assert "disk" in data


class TestExportSettings:
    def test_export(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings/export")
        assert r.status_code == 200
        data = r.json()
        # Token should be redacted from export
        assert "token" not in data.get("auth", {})
        assert "theme" in data


class TestImportSettings:
    def test_import(self, admin_client, bp, tmp_project_dir):
        imported = {"theme": "dark", "server": {"port": 9090}}
        r = admin_client.post(
            f"{bp}/api/settings/import",
            json={"settings": imported},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Restore
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["server"]["port"] = 8080
        sp.write_text(json.dumps(settings, indent=2))

    def test_invalid(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/settings/import",
            json={"settings": {"server": {"port": 99999}}},
        )
        assert r.status_code == 400


class TestReportSettings:
    def test_get(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/settings/report")
        assert r.status_code == 200
        data = r.json()
        assert "settings" in data or "graphs" in data


class TestTokenVerify:
    def test_correct_token(self, admin_client, bp, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("login-token")
        sp.write_text(json.dumps(settings, indent=2))

        r = admin_client.post(
            f"{bp}/api/auth/verify",
            json={"token": "login-token"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Cookie should be set
        assert "jmeter_token" in r.cookies

        # Cleanup
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))

    def test_wrong_token(self, admin_client, bp, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("correct-token")
        sp.write_text(json.dumps(settings, indent=2))

        r = admin_client.post(
            f"{bp}/api/auth/verify",
            json={"token": "wrong-token"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is False

        # Cleanup
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))
