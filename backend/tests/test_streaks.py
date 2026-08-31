"""Tests for the Developer Streak Tracker feature."""

import pytest
from datetime import date, timedelta


@pytest.fixture
def auth_headers(client):
    email = "streakuser@example.com"
    password = "TestPass123!"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": "streakuser",
            "password": password,
            "display_name": "Streak User",
        },
    )
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.json().get("access_token") or resp.json().get("token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_auth_headers(client):
    email = "streakuser2@example.com"
    password = "TestPass123!"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": "streakuser2",
            "password": password,
            "display_name": "Streak User 2",
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
            "title": "Streak Test Project",
            "description": "A project for testing streaks",
            "visibility": "public",
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


class TestRecordActivity:
    def test_record_single_day(self, client, auth_headers, project_id):
        today = date.today().isoformat()
        resp = client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today, "activity_type": "commit"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["activity_date"] == today
        assert data["activity_type"] == "commit"

    def test_record_duplicate_day_idempotent(self, client, auth_headers, project_id):
        today = date.today().isoformat()
        resp1 = client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today},
        )
        resp2 = client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today},
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_record_nonexistent_project(self, client, auth_headers):
        import uuid
        resp = client.post(
            f"/api/streaks/project/{uuid.uuid4()}/record",
            headers=auth_headers,
            json={"activity_date": date.today().isoformat()},
        )
        assert resp.status_code == 404


class TestBulkRecord:
    def test_bulk_record(self, client, auth_headers, project_id):
        today = date.today()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(5)]
        resp = client.post(
            f"/api/streaks/project/{project_id}/bulk-record",
            headers=auth_headers,
            json={"dates": dates, "activity_type": "commit"},
        )
        assert resp.status_code == 200
        assert resp.json()["recorded"] == 5

    def test_bulk_record_partial_duplicates(self, client, auth_headers, project_id):
        today = date.today()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(3)]
        client.post(
            f"/api/streaks/project/{project_id}/bulk-record",
            headers=auth_headers,
            json={"dates": dates},
        )
        resp = client.post(
            f"/api/streaks/project/{project_id}/bulk-record",
            headers=auth_headers,
            json={"dates": dates},
        )
        assert resp.json()["recorded"] == 0


class TestStreakSummary:
    def test_empty_streak(self, client, auth_headers, project_id):
        resp = client.get(
            f"/api/streaks/project/{project_id}/me",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_streak"] == 0

    def test_streak_after_recording(self, client, auth_headers, project_id):
        today = date.today()
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            client.post(
                f"/api/streaks/project/{project_id}/record",
                headers=auth_headers,
                json={"activity_date": d},
            )
        resp = client.get(
            f"/api/streaks/project/{project_id}/me",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["current_streak"] >= 1
        assert data["total_active_days"] == 3

    def test_user_streak_public(self, client, auth_headers, project_id):
        today = date.today().isoformat()
        client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today},
        )
        import uuid
        # Use the auth user's ID (from the token)
        me = client.get("/api/users/me", headers=auth_headers)
        uid = me.json()["id"]
        resp = client.get(
            f"/api/streaks/project/{project_id}/user/{uid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total_active_days"] == 1


class TestLeaderboard:
    def test_empty_leaderboard(self, client, project_id):
        resp = client.get(
            f"/api/streaks/project/{project_id}/leaderboard",
        )
        assert resp.status_code == 200
        assert resp.json()["total_participants"] == 0
        assert resp.json()["entries"] == []

    def test_leaderboard_with_activity(
        self, client, auth_headers, second_auth_headers, project_id
    ):
        today = date.today()
        # User 1: 5-day streak
        for i in range(5):
            d = (today - timedelta(days=i)).isoformat()
            client.post(
                f"/api/streaks/project/{project_id}/record",
                headers=auth_headers,
                json={"activity_date": d},
            )
        # User 2: 2-day streak
        for i in range(2):
            d = (today - timedelta(days=i)).isoformat()
            client.post(
                f"/api/streaks/project/{project_id}/record",
                headers=second_auth_headers,
                json={"activity_date": d},
            )
        resp = client.get(
            f"/api/streaks/project/{project_id}/leaderboard",
        )
        data = resp.json()
        assert data["total_participants"] == 2
        assert data["entries"][0]["current_streak"] >= data["entries"][1]["current_streak"]


class TestHeatmap:
    def test_heatmap_returns_year(self, client, auth_headers, project_id):
        today = date.today().isoformat()
        client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today},
        )
        me = client.get("/api/users/me", headers=auth_headers)
        uid = me.json()["id"]
        year = date.today().year
        resp = client.get(
            f"/api/streaks/project/{project_id}/user/{uid}/heatmap/{year}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["weeks"]) > 0


class TestProjectStats:
    def test_stats_empty(self, client, project_id):
        resp = client.get(
            f"/api/streaks/project/{project_id}/stats",
        )
        assert resp.status_code == 200
        assert resp.json()["total_active_users"] == 0

    def test_stats_with_users(
        self, client, auth_headers, second_auth_headers, project_id
    ):
        today = date.today()
        client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=auth_headers,
            json={"activity_date": today.isoformat()},
        )
        client.post(
            f"/api/streaks/project/{project_id}/record",
            headers=second_auth_headers,
            json={"activity_date": today.isoformat()},
        )
        resp = client.get(
            f"/api/streaks/project/{project_id}/stats",
        )
        data = resp.json()
        assert data["total_active_users"] == 2
        assert data["active_last_7_days"] == 2
