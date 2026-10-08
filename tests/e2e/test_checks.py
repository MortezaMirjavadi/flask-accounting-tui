"""E2E tests for Checks API (/api/checks)."""

import pytest


class TestChecksCRUD:
    def test_create_check(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/checks", json={
            "type": "issued",
            "check_number": "123456",
            "bank_name": "Mellat",
            "amount": 5000000,
            "issue_date": "1403-01-01",
            "due_date": "1403-04-01",
            "category_id": category_id,
            "wallet_id": wallet_id,
            "description": "Rent check",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["type"] == "issued"
        assert "id" in data

    def test_create_received_check(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/checks", json={
            "type": "received",
            "amount": 2000000,
            "issue_date": "1403-02-01",
            "due_date": "1403-05-01",
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_check_invalid_type(self, client, auth_headers, category_id):
        resp = client.post("/api/checks", json={
            "type": "invalid",
            "amount": 1000,
            "issue_date": "1403-01-01",
            "due_date": "1403-02-01",
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_check_missing_dates(self, client, auth_headers, category_id):
        resp = client.post("/api/checks", json={
            "type": "issued",
            "amount": 1000,
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_check_due_before_issue(self, client, auth_headers, category_id):
        resp = client.post("/api/checks", json={
            "type": "issued",
            "amount": 1000,
            "issue_date": "1403-06-01",
            "due_date": "1403-01-01",
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_checks(self, client, auth_headers, category_id, wallet_id):
        client.post("/api/checks", json={
            "type": "issued",
            "amount": 1000000,
            "issue_date": "1403-01-01",
            "due_date": "1403-03-01",
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)

        resp = client.get("/api/checks", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_checks_with_filters(self, client, auth_headers):
        resp = client.get(
            "/api/checks?status=pending&type=issued",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_check(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/checks", json={
            "type": "issued",
            "amount": 3000000,
            "issue_date": "1403-01-01",
            "due_date": "1403-04-01",
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        check_id = create.get_json()["id"]

        resp = client.get(
            f"/api/checks/{check_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_check_not_found(self, client, auth_headers):
        resp = client.get("/api/checks/999999", headers=auth_headers)
        assert resp.status_code == 404


class TestCheckActions:
    def _create_check(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/checks", json={
            "type": "issued",
            "amount": 1000000,
            "issue_date": "1403-01-01",
            "due_date": "1403-04-01",
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        return resp.get_json()["id"]

    def test_clear_check(self, client, auth_headers, category_id, wallet_id):
        check_id = self._create_check(client, auth_headers, category_id, wallet_id)
        resp = client.post(
            f"/api/checks/{check_id}/clear",
            json={"cleared_date": "1403-04-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_bounce_check(self, client, auth_headers, category_id, wallet_id):
        check_id = self._create_check(client, auth_headers, category_id, wallet_id)
        resp = client.post(
            f"/api/checks/{check_id}/bounce",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_cancel_check(self, client, auth_headers, category_id, wallet_id):
        check_id = self._create_check(client, auth_headers, category_id, wallet_id)
        resp = client.post(
            f"/api/checks/{check_id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_change_due_date(self, client, auth_headers, category_id, wallet_id):
        check_id = self._create_check(client, auth_headers, category_id, wallet_id)
        resp = client.put(
            f"/api/checks/{check_id}/due-date",
            json={"due_date": "1403-06-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_change_due_date_missing(self, client, auth_headers, category_id, wallet_id):
        check_id = self._create_check(client, auth_headers, category_id, wallet_id)
        resp = client.put(
            f"/api/checks/{check_id}/due-date",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestCheckViews:
    def test_upcoming_checks(self, client, auth_headers):
        resp = client.get(
            "/api/checks/upcoming?days=30",
            headers=auth_headers,
        )
        assert resp.status_code == 200
