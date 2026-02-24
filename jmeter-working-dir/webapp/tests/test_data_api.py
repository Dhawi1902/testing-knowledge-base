"""Tests for test data API — CSV CRUD: list, preview, download, delete, rename, build, upload."""

import pytest

from tests.conftest import make_csv


class TestListFiles:
    def test_empty(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/data/files")
        assert r.status_code == 200
        assert "files" in r.json()

    def test_with_csv(self, admin_client, bp, sample_csv):
        r = admin_client.get(f"{bp}/api/data/files")
        assert r.status_code == 200
        files = r.json()["files"]
        names = [f["filename"] for f in files]
        assert "test_users.csv" in names


class TestPreviewCSV:
    def test_preview(self, admin_client, bp, sample_csv):
        r = admin_client.get(f"{bp}/api/data/preview/test_users.csv")
        assert r.status_code == 200
        data = r.json()
        assert "columns" in data
        assert "username" in data["columns"]
        assert len(data["rows"]) == 2

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/data/preview/nonexistent.csv")
        assert r.status_code == 200  # returns {"error": "File not found"} with 200
        assert "error" in r.json()


class TestDownloadCSV:
    def test_download(self, admin_client, bp, sample_csv):
        r = admin_client.get(f"{bp}/api/data/download/test_users.csv")
        assert r.status_code == 200
        assert b"username" in r.content

    def test_not_found(self, admin_client, bp):
        r = admin_client.get(f"{bp}/api/data/download/missing.csv")
        assert r.status_code == 404


class TestDeleteCSV:
    def test_delete(self, admin_client, bp, tmp_project_dir):
        data_dir = tmp_project_dir["project_root"] / "test_data"
        make_csv(data_dir, "to_delete.csv")
        r = admin_client.delete(f"{bp}/api/data/delete/to_delete.csv")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert not (data_dir / "to_delete.csv").exists()

    def test_not_found(self, admin_client, bp):
        r = admin_client.delete(f"{bp}/api/data/delete/ghost.csv")
        assert r.status_code == 404


class TestRenameCSV:
    def test_rename(self, admin_client, bp, tmp_project_dir):
        data_dir = tmp_project_dir["project_root"] / "test_data"
        make_csv(data_dir, "old_name.csv")
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": "old_name.csv", "new": "new_name.csv"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert not (data_dir / "old_name.csv").exists()
        assert (data_dir / "new_name.csv").exists()
        # Cleanup
        (data_dir / "new_name.csv").unlink()

    def test_not_found(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": "nope.csv", "new": "new.csv"},
        )
        assert r.status_code == 404

    def test_already_exists(self, admin_client, bp, tmp_project_dir):
        data_dir = tmp_project_dir["project_root"] / "test_data"
        make_csv(data_dir, "a.csv")
        make_csv(data_dir, "b.csv")
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": "a.csv", "new": "b.csv"},
        )
        assert r.status_code == 400
        # Cleanup
        (data_dir / "a.csv").unlink()
        (data_dir / "b.csv").unlink()

    def test_auto_extension(self, admin_client, bp, tmp_project_dir):
        data_dir = tmp_project_dir["project_root"] / "test_data"
        make_csv(data_dir, "src.csv")
        r = admin_client.post(
            f"{bp}/api/data/rename",
            json={"old": "src.csv", "new": "dest"},
        )
        assert r.status_code == 200
        assert (data_dir / "dest.csv").exists()
        # Cleanup
        (data_dir / "dest.csv").unlink()


class TestBuildCSV:
    def test_sequential(self, admin_client, bp, tmp_project_dir):
        r = admin_client.post(
            f"{bp}/api/data/build",
            json={
                "filename": "built.csv",
                "columns": [
                    {
                        "name": "user_id",
                        "type": "sequential",
                        "ranges": [{"prefix": "USR", "start": 1, "end": 5, "width": 4}],
                    }
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["rows"] == 5
        # Cleanup
        f = tmp_project_dir["project_root"] / "test_data" / "built.csv"
        if f.exists():
            f.unlink()

    def test_mixed_types(self, admin_client, bp, tmp_project_dir):
        r = admin_client.post(
            f"{bp}/api/data/build",
            json={
                "filename": "mixed.csv",
                "columns": [
                    {
                        "name": "id",
                        "type": "sequential",
                        "ranges": [{"prefix": "", "start": 1, "end": 3, "width": 3}],
                    },
                    {"name": "status", "type": "static", "value": "active"},
                    {"name": "role", "type": "random_pick", "values": ["admin", "user"]},
                ],
            },
        )
        assert r.status_code == 200
        assert r.json()["rows"] == 3
        assert r.json()["columns"] == ["id", "status", "role"]
        # Cleanup
        f = tmp_project_dir["project_root"] / "test_data" / "mixed.csv"
        if f.exists():
            f.unlink()

    def test_no_columns_error(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/data/build",
            json={"filename": "empty.csv", "columns": []},
        )
        assert r.status_code == 400
        assert "error" in r.json()

    def test_expression_column(self, admin_client, bp, tmp_project_dir):
        r = admin_client.post(
            f"{bp}/api/data/build",
            json={
                "filename": "expr.csv",
                "columns": [
                    {
                        "name": "id",
                        "type": "sequential",
                        "ranges": [{"prefix": "U", "start": 1, "end": 2, "width": 3}],
                    },
                    {
                        "name": "email",
                        "type": "expression",
                        "template": "{id}@test.com",
                    },
                ],
            },
        )
        assert r.status_code == 200
        assert r.json()["columns"] == ["id", "email"]
        # Cleanup
        f = tmp_project_dir["project_root"] / "test_data" / "expr.csv"
        if f.exists():
            f.unlink()


class TestUploadCSV:
    def test_upload(self, admin_client, bp, tmp_project_dir):
        r = admin_client.post(
            f"{bp}/api/data/upload",
            files={"file": ("uploaded.csv", b"col1,col2\nval1,val2\n", "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Cleanup
        f = tmp_project_dir["project_root"] / "test_data" / "uploaded.csv"
        if f.exists():
            f.unlink()

    def test_wrong_extension(self, admin_client, bp):
        r = admin_client.post(
            f"{bp}/api/data/upload",
            files={"file": ("bad.txt", b"data", "text/plain")},
        )
        assert r.status_code == 400
