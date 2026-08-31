"""Tests for the Project Dependencies Tracker feature."""

import pytest


@pytest.fixture
def auth_headers(client):
    email = "depuser@example.com"
    password = "TestPass123!"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": "depuser",
            "password": password,
            "display_name": "Dep User",
        },
    )
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.json().get("access_token") or resp.json().get("token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(client, auth_headers):
    resp = client.post(
        "/api/projects",
        headers=auth_headers,
        json={
            "title": "Dep Test Project",
            "description": "A project for testing dependencies",
            "visibility": "public",
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


DEP_PAYLOAD = {
    "name": "fastapi",
    "current_version": "0.110.0",
    "category": "backend",
    "description": "Web framework for building APIs",
    "homepage_url": "https://fastapi.tiangolo.com",
    "is_critical": True,
}


class TestCreateDependency:
    def test_create(self, client, auth_headers, project_id):
        resp = client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "fastapi"
        assert data["category"] == "backend"
        assert data["is_critical"] is True

    def test_create_nonexistent_project(self, client, auth_headers):
        import uuid
        resp = client.post(
            f"/api/project-dependencies/project/{uuid.uuid4()}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        assert resp.status_code == 404

    def test_create_duplicate(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        resp = client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        assert resp.status_code == 409


class TestListDependencies:
    def test_list_empty(self, client, project_id):
        resp = client.get(f"/api/project-dependencies/project/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_deps(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json={**DEP_PAYLOAD, "name": "sqlalchemy", "category": "database", "is_critical": False},
        )
        resp = client.get(f"/api/project-dependencies/project/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_filter_by_category(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json={**DEP_PAYLOAD, "name": "pytest", "category": "testing"},
        )
        resp = client.get(
            f"/api/project-dependencies/project/{project_id}?category=testing"
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category"] == "testing"

    def test_search(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        resp = client.get(
            f"/api/project-dependencies/project/{project_id}?search=fastapi"
        )
        assert resp.json()["total"] == 1

    def test_filter_critical_only(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json={**DEP_PAYLOAD, "name": "pytest", "is_critical": False},
        )
        resp = client.get(
            f"/api/project-dependencies/project/{project_id}?critical_only=true"
        )
        assert resp.json()["total"] == 1


class TestUpdateDependency:
    def test_update_version(self, client, auth_headers, project_id):
        create_resp = client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        dep_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/project-dependencies/{dep_id}",
            headers=auth_headers,
            json={"current_version": "0.111.0", "latest_version": "0.111.0"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_version"] == "0.111.0"
        assert resp.json()["latest_version"] == "0.111.0"
        assert resp.json()["is_outdated"] is False


class TestDeleteDependency:
    def test_delete(self, client, auth_headers, project_id):
        create_resp = client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        dep_id = create_resp.json()["id"]
        resp = client.delete(
            f"/api/project-dependencies/{dep_id}", headers=auth_headers
        )
        assert resp.status_code == 204


class TestBulkImport:
    def test_bulk_import(self, client, auth_headers, project_id):
        deps = [
            {"name": "react", "category": "frontend", "current_version": "19.0.0"},
            {"name": "vue", "category": "frontend", "current_version": "3.5.0"},
            {"name": "express", "category": "backend", "current_version": "4.21.0"},
        ]
        resp = client.post(
            f"/api/project-dependencies/project/{project_id}/bulk-import",
            headers=auth_headers,
            json={"dependencies": deps},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] == 3

    def test_bulk_import_skips_duplicates(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        resp = client.post(
            f"/api/project-dependencies/project/{project_id}/bulk-import",
            headers=auth_headers,
            json={"dependencies": [DEP_PAYLOAD]},
        )
        assert resp.json()["created"] == 0
        assert resp.json()["skipped"] == 1


class TestAuditSummary:
    def test_audit_empty(self, client, project_id):
        resp = client.get(
            f"/api/project-dependencies/project/{project_id}/audit"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_dependencies"] == 0
        assert data["health_score"] == 100.0

    def test_audit_with_deps(self, client, auth_headers, project_id):
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json={
                **DEP_PAYLOAD,
                "name": "old-lib",
                "current_version": "1.0.0",
                "latest_version": "2.0.0",
                "is_critical": True,
            },
        )
        resp = client.get(
            f"/api/project-dependencies/project/{project_id}/audit"
        )
        data = resp.json()
        assert data["total_dependencies"] == 2
        assert data["outdated_count"] == 1
        assert data["health_score"] < 100.0


class TestVersionHistory:
    def test_version_history(self, client, auth_headers, project_id):
        create_resp = client.post(
            f"/api/project-dependencies/project/{project_id}",
            headers=auth_headers,
            json=DEP_PAYLOAD,
        )
        dep_id = create_resp.json()["id"]
        # Update version
        client.patch(
            f"/api/project-dependencies/{dep_id}",
            headers=auth_headers,
            json={"current_version": "0.111.0"},
        )
        client.patch(
            f"/api/project-dependencies/{dep_id}",
            headers=auth_headers,
            json={"current_version": "0.112.0"},
        )
        resp = client.get(
            f"/api/project-dependencies/{dep_id}/version-history"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
