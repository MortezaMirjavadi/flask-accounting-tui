"""E2E tests for Budget API (/api/budget)."""

import pytest


class TestBudgetPeriods:
    def test_create_period(self, client, auth_headers):
        resp = client.post("/api/budget/periods", json={
            "year": 1403,
            "month": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["year"] == 1403
        assert data["month"] == 1

    def test_create_period_invalid_year(self, client, auth_headers):
        resp = client.post("/api/budget/periods", json={
            "year": 9999,
            "month": 1,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_period_invalid_month(self, client, auth_headers):
        resp = client.post("/api/budget/periods", json={
            "year": 1403,
            "month": 13,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_periods(self, client, auth_headers):
        resp = client.get("/api/budget/periods", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data

    def test_list_periods_with_year_filter(self, client, auth_headers):
        client.post("/api/budget/periods", json={
            "year": 1403, "month": 6,
        }, headers=auth_headers)
        resp = client.get(
            "/api/budget/periods?year=1403",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_period(self, client, auth_headers):
        create = client.post("/api/budget/periods", json={
            "year": 1403, "month": 3,
        }, headers=auth_headers)
        pid = create.get_json()["id"]

        resp = client.get(
            f"/api/budget/periods/{pid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_update_period(self, client, auth_headers):
        create = client.post("/api/budget/periods", json={
            "year": 1403, "month": 4,
        }, headers=auth_headers)
        pid = create.get_json()["id"]

        resp = client.put(
            f"/api/budget/periods/{pid}",
            json={"year": 1403, "month": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["month"] == 5

    def test_delete_period(self, client, auth_headers):
        create = client.post("/api/budget/periods", json={
            "year": 1403, "month": 7,
        }, headers=auth_headers)
        pid = create.get_json()["id"]

        resp = client.delete(
            f"/api/budget/periods/{pid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestBudgetItems:
    def test_create_item(self, client, auth_headers, category_id):
        period = client.post("/api/budget/periods", json={
            "year": 1403, "month": 8,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        resp = client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": category_id,
            "planned_amount": 5000000,
            "notes": "Monthly food budget",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["planned_amount"] == 5000000

    def test_create_item_invalid_category(self, client, auth_headers):
        period = client.post("/api/budget/periods", json={
            "year": 1403, "month": 9,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        resp = client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": 999999,
            "planned_amount": 1000,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_items_in_period(self, client, auth_headers, category_id):
        period = client.post("/api/budget/periods", json={
            "year": 1403, "month": 10,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": category_id,
            "planned_amount": 2000000,
        }, headers=auth_headers)

        resp = client.get(
            f"/api/budget/periods/{pid}/items",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1

    def test_get_item(self, client, auth_headers, category_id):
        period = client.post("/api/budget/periods", json={
            "year": 1403, "month": 11,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        item = client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": category_id,
            "planned_amount": 3000000,
        }, headers=auth_headers)
        iid = item.get_json()["id"]

        resp = client.get(
            f"/api/budget/items/{iid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_update_item(self, client, auth_headers, category_id):
        period = client.post("/api/budget/periods", json={
            "year": 1403, "month": 12,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        item = client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": category_id,
            "planned_amount": 1000000,
        }, headers=auth_headers)
        iid = item.get_json()["id"]

        resp = client.put(
            f"/api/budget/items/{iid}",
            json={
                "category_id": category_id,
                "planned_amount": 2000000,
                "notes": "Updated",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["planned_amount"] == 2000000

    def test_delete_item(self, client, auth_headers, category_id):
        period = client.post("/api/budget/periods", json={
            "year": 1404, "month": 1,
        }, headers=auth_headers)
        pid = period.get_json()["id"]

        item = client.post("/api/budget/items", json={
            "budget_period_id": pid,
            "category_id": category_id,
            "planned_amount": 500000,
        }, headers=auth_headers)
        iid = item.get_json()["id"]

        resp = client.delete(
            f"/api/budget/items/{iid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_periods_with_items(self, client, auth_headers, category_id):
        resp = client.get(
            "/api/budget/periods/with-items",
            headers=auth_headers,
        )
        assert resp.status_code == 200
