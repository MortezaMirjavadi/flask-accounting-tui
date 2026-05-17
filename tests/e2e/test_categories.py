"""E2E tests for Categories API (/api/categories)."""

import pytest


class TestCategoriesCRUD:
    def test_create_category(self, client, auth_headers):
        resp = client.post("/api/categories", json={
            "name": "Food",
            "type": "cost",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Food"
        assert data["type"] == "cost"
        assert "id" in data

    def test_create_income_category(self, client, auth_headers):
        resp = client.post("/api/categories", json={
            "name": "Salary",
            "type": "income",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["type"] == "income"

    def test_create_category_invalid_type(self, client, auth_headers):
        resp = client.post("/api/categories", json={
            "name": "Bad",
            "type": "invalid",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_category_missing_name(self, client, auth_headers):
        resp = client.post("/api/categories", json={
            "type": "cost",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_categories(self, client, auth_headers, category_id):
        resp = client.get("/api/categories", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_categories_with_type_filter(self, client, auth_headers, category_id):
        resp = client.get(
            "/api/categories?type=cost",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for item in resp.get_json()["items"]:
            assert item["type"] == "cost"

    def test_get_category(self, client, auth_headers, category_id):
        resp = client.get(
            f"/api/categories/{category_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["id"] == category_id

    def test_get_category_not_found(self, client, auth_headers):
        resp = client.get("/api/categories/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_category(self, client, auth_headers, category_id):
        resp = client.put(
            f"/api/categories/{category_id}",
            json={"name": "UpdatedFood", "type": "cost"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "UpdatedFood"

    def test_update_category_not_found(self, client, auth_headers):
        resp = client.put(
            "/api/categories/999999",
            json={"name": "X", "type": "cost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_category(self, client, auth_headers, category_id):
        resp = client.delete(
            f"/api/categories/{category_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Verify it's gone
        resp = client.get(
            f"/api/categories/{category_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_category_not_found(self, client, auth_headers):
        resp = client.delete("/api/categories/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_create_duplicate_restores_archived(self, client, auth_headers):
        """Creating a category with the same name as an archived one should restore it."""
        resp = client.post("/api/categories", json={
            "name": "RestorableCat",
            "type": "cost",
        }, headers=auth_headers)
        cat_id = resp.get_json()["id"]

        client.delete(f"/api/categories/{cat_id}", headers=auth_headers)

        resp = client.post("/api/categories", json={
            "name": "RestorableCat",
            "type": "income",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["id"] == cat_id
