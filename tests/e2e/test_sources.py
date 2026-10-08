"""E2E tests for Sources (legacy) API (/api/sources)."""

import pytest


class TestSourcesCRUD:
    def test_create_source(self, client, auth_headers):
        resp = client.post("/api/sources", json={
            "name": "TestSource",
            "amount": 5000000,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "TestSource"
        assert "id" in data

    def test_create_source_duplicate_restores(self, client, auth_headers):
        resp = client.post("/api/sources", json={
            "name": "RestoreSrc",
            "amount": 1000,
        }, headers=auth_headers)
        sid = resp.get_json()["id"]
        client.delete(f"/api/sources/{sid}", headers=auth_headers)

        resp = client.post("/api/sources", json={
            "name": "RestoreSrc",
            "amount": 2000,
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_list_sources(self, client, auth_headers):
        resp = client.get("/api/sources", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data

    def test_list_sources_with_name_filter(self, client, auth_headers):
        client.post("/api/sources", json={
            "name": "FilterMeSource",
            "amount": 0,
        }, headers=auth_headers)
        resp = client.get(
            "/api/sources?name=Filter",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_source(self, client, auth_headers):
        create = client.post("/api/sources", json={
            "name": "GetSrc",
            "amount": 3000,
        }, headers=auth_headers)
        sid = create.get_json()["id"]

        resp = client.get(f"/api/sources/{sid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["id"] == sid

    def test_get_source_not_found(self, client, auth_headers):
        resp = client.get("/api/sources/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_source(self, client, auth_headers):
        create = client.post("/api/sources", json={
            "name": "UpdateSrc",
            "amount": 1000,
        }, headers=auth_headers)
        sid = create.get_json()["id"]

        resp = client.put(
            f"/api/sources/{sid}",
            json={"name": "UpdatedSrc", "amount": 5000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "UpdatedSrc"

    def test_delete_source(self, client, auth_headers):
        create = client.post("/api/sources", json={
            "name": "DelSrc",
            "amount": 0,
        }, headers=auth_headers)
        sid = create.get_json()["id"]

        resp = client.delete(f"/api/sources/{sid}", headers=auth_headers)
        assert resp.status_code == 200


class TestSourceBalance:
    def test_source_balance(self, client, auth_headers):
        create = client.post("/api/sources", json={
            "name": "BalSrc",
            "amount": 10000,
        }, headers=auth_headers)
        sid = create.get_json()["id"]

        resp = client.get(
            f"/api/sources/{sid}/balance",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_income" in data
        assert "total_cost" in data
        assert "balance" in data

    def test_source_balance_not_found(self, client, auth_headers):
        resp = client.get(
            "/api/sources/999999/balance",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestSourceTransfers:
    def test_source_transfers_empty(self, client, auth_headers):
        create = client.post("/api/sources", json={
            "name": "TransSrc",
            "amount": 0,
        }, headers=auth_headers)
        sid = create.get_json()["id"]

        resp = client.get(
            f"/api/sources/{sid}/transfers",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
