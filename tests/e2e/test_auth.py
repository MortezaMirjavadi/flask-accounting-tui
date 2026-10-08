"""E2E tests for Auth API (/api/auth)."""

import pytest


class TestAuthRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "reg_user_ok",
            "password": "pass123456",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "reg_user_ok"
        assert "id" in data

    def test_register_duplicate_username(self, client):
        client.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "pass123456",
        })
        resp = client.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "pass123456",
        })
        assert resp.status_code == 400

    def test_register_short_username(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "ab",
            "password": "pass123456",
        })
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "validname",
            "password": "123",
        })
        assert resp.status_code == 400

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 400


class TestAuthLogin:
    def test_login_success(self, client, approved_user):
        resp = client.post("/api/auth/login", json={
            "username": approved_user["username"],
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == approved_user["username"]

    def test_login_wrong_password(self, client, approved_user):
        resp = client.post("/api/auth/login", json={
            "username": approved_user["username"],
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "nobody_here",
            "password": "pass123456",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={"username": "x"})
        assert resp.status_code == 400


class TestAuthMe:
    def test_me_success(self, client, approved_user):
        resp = client.get(
            "/api/auth/me",
            headers={"X-Username": approved_user["username"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == approved_user["username"]

    def test_me_no_header(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 400


class TestAuthAdmin:
    def test_pending_users_requires_admin(self, client, approved_user):
        resp = client.get(
            "/api/auth/pending-users",
            headers={"X-Username": approved_user["username"]},
        )
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client, admin_headers):
        resp = client.get("/api/auth/users", headers=admin_headers)
        assert resp.status_code == 200

    def test_admin_can_approve_user(self, client, admin_headers, username):
        reg = client.post("/api/auth/register", json={
            "username": username,
            "password": "pass123456",
        })
        uid = reg.get_json()["id"]
        resp = client.post(
            f"/api/auth/approve-user/{uid}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_admin_can_reject_user(self, client, admin_headers):
        uname = "reject_me_user"
        reg = client.post("/api/auth/register", json={
            "username": uname,
            "password": "pass123456",
        })
        uid = reg.get_json()["id"]
        resp = client.post(
            f"/api/auth/reject-user/{uid}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_admin_create_user(self, client, admin_headers):
        resp = client.post("/api/auth/users", json={
            "username": "admin_created",
            "password": "pass123456",
            "is_active": True,
        }, headers=admin_headers)
        assert resp.status_code == 201

    def test_admin_get_user(self, client, admin_headers, approved_user):
        resp = client.get(
            f"/api/auth/users/{approved_user['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_admin_update_user(self, client, admin_headers, approved_user):
        resp = client.put(
            f"/api/auth/users/{approved_user['id']}",
            json={"display_name": "Updated Name"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_admin_activate_deactivate(self, client, admin_headers, approved_user):
        resp = client.post(
            f"/api/auth/deactivate-user/{approved_user['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        resp = client.post(
            f"/api/auth/activate-user/{approved_user['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_non_admin_cannot_create_user(self, client, approved_user):
        resp = client.post("/api/auth/users", json={
            "username": "hack_created",
            "password": "pass123456",
        }, headers={"X-Username": approved_user["username"]})
        assert resp.status_code == 403
