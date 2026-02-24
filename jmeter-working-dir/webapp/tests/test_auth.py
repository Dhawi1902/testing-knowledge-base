"""Unit tests for services/auth.py — safe_join, token hashing, access control."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.auth import (
    safe_join,
    hash_token,
    verify_token,
    check_access,
    get_access_level,
    migrate_token_if_needed,
    _is_sha256_hex,
)


# ---- safe_join ----

class TestSafeJoin:
    def setup_method(self):
        self.base = Path(tempfile.mkdtemp())

    def test_normal_file(self):
        result = safe_join(self.base, "file.csv")
        assert result is not None
        assert result == (self.base / "file.csv").resolve()

    def test_subdirectory(self):
        result = safe_join(self.base, "sub/file.csv")
        assert result is not None
        assert str(result).startswith(str(self.base.resolve()))

    def test_rejects_parent_traversal(self):
        assert safe_join(self.base, "../../etc/passwd") is None

    def test_rejects_backslash_traversal(self):
        assert safe_join(self.base, "..\\..\\etc\\passwd") is None

    def test_rejects_dot_dot_in_middle(self):
        assert safe_join(self.base, "sub/../../etc/passwd") is None

    def test_empty_input_returns_base(self):
        result = safe_join(self.base, "")
        assert result is not None
        assert result == self.base.resolve()

    def test_dot_returns_base(self):
        result = safe_join(self.base, ".")
        assert result is not None
        assert result == self.base.resolve()

    def test_rejects_similar_prefix(self):
        """safe_join(base='/data', input) should NOT match '/data_other'."""
        base = Path(tempfile.mkdtemp(suffix="_base"))
        other = Path(str(base) + "_other")
        other.mkdir(exist_ok=True)
        # Try to access a path that starts with base but is in 'other'
        relative = os.path.relpath(other / "secret.txt", base)
        result = safe_join(base, relative)
        # Should be None since it escapes base
        assert result is None


# ---- hash_token ----

class TestHashToken:
    def test_deterministic(self):
        assert hash_token("abc") == hash_token("abc")

    def test_is_64_char_hex(self):
        h = hash_token("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs_differ(self):
        assert hash_token("token1") != hash_token("token2")


# ---- _is_sha256_hex ----

class TestIsSha256Hex:
    def test_valid(self):
        h = hash_token("test")
        assert _is_sha256_hex(h) is True

    def test_wrong_length(self):
        assert _is_sha256_hex("abcdef") is False

    def test_non_hex_chars(self):
        assert _is_sha256_hex("g" * 64) is False

    def test_empty(self):
        assert _is_sha256_hex("") is False


# ---- verify_token ----

class TestVerifyToken:
    def test_no_token_stored(self, tmp_project_dir):
        """When no token is configured, any token is accepted."""
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))
        assert verify_token("anything") is True

    def test_correct_token(self, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("my-secret")
        sp.write_text(json.dumps(settings, indent=2))
        assert verify_token("my-secret") is True

    def test_wrong_token(self, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hash_token("my-secret")
        sp.write_text(json.dumps(settings, indent=2))
        assert verify_token("wrong-token") is False

    def test_cleanup(self, tmp_project_dir):
        """Reset token to empty after tests."""
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))


# ---- migrate_token_if_needed ----

class TestMigrateToken:
    def test_plain_text_gets_hashed(self, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = "plain-text-token"
        sp.write_text(json.dumps(settings, indent=2))

        migrate_token_if_needed()

        settings = json.loads(sp.read_text())
        token = settings["auth"]["token"]
        assert _is_sha256_hex(token)
        assert token == hash_token("plain-text-token")

    def test_already_hashed_unchanged(self, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        hashed = hash_token("some-token")
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = hashed
        sp.write_text(json.dumps(settings, indent=2))

        migrate_token_if_needed()

        settings = json.loads(sp.read_text())
        assert settings["auth"]["token"] == hashed

    def test_empty_token_unchanged(self, tmp_project_dir):
        sp = tmp_project_dir["settings_path"]
        settings = json.loads(sp.read_text())
        settings["auth"]["token"] = ""
        sp.write_text(json.dumps(settings, indent=2))

        migrate_token_if_needed()

        settings = json.loads(sp.read_text())
        assert settings["auth"]["token"] == ""


# ---- check_access ----

class TestCheckAccess:
    def _make_request(self, access_level: str):
        req = MagicMock()
        req.state.access_level = access_level
        return req

    def test_admin_returns_none(self):
        result = check_access(self._make_request("admin"))
        assert result is None

    def test_viewer_returns_403(self):
        result = check_access(self._make_request("viewer"))
        assert result is not None
        assert result.status_code == 403
