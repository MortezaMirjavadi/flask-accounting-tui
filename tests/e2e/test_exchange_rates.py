"""E2E tests for Exchange Rates API (/api/exchange-rates)."""

import pytest


class TestExchangeRatesCRUD:
    def test_create_rate(self, client, auth_headers):
        resp = client.post("/api/exchange-rates", json={
            "from_currency": "USD",
            "to_currency": "IRR",
            "rate": 500000,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "IRR"
        assert data["rate"] == 500000
        assert "reverse_rate" in data

    def test_create_rate_same_currency(self, client, auth_headers):
        resp = client.post("/api/exchange-rates", json={
            "from_currency": "USD",
            "to_currency": "USD",
            "rate": 1,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_rate_invalid_currency(self, client, auth_headers):
        resp = client.post("/api/exchange-rates", json={
            "from_currency": "XYZ",
            "to_currency": "IRR",
            "rate": 100,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_rate_negative(self, client, auth_headers):
        resp = client.post("/api/exchange-rates", json={
            "from_currency": "EUR",
            "to_currency": "IRR",
            "rate": -10,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_rate_missing_fields(self, client, auth_headers):
        resp = client.post("/api/exchange-rates", json={
            "from_currency": "USD",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_rates(self, client, auth_headers):
        client.post("/api/exchange-rates", json={
            "from_currency": "GBP",
            "to_currency": "IRR",
            "rate": 600000,
        }, headers=auth_headers)

        resp = client.get("/api/exchange-rates", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data

    def test_update_rate(self, client, auth_headers):
        create = client.post("/api/exchange-rates", json={
            "from_currency": "AED",
            "to_currency": "IRR",
            "rate": 140000,
        }, headers=auth_headers)
        rate_id = create.get_json()["id"]

        resp = client.put(
            f"/api/exchange-rates/{rate_id}",
            json={"rate": 145000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["rate"] == 145000

    def test_update_rate_invalid(self, client, auth_headers):
        resp = client.put(
            "/api/exchange-rates/999999",
            json={"rate": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_rate(self, client, auth_headers):
        create = client.post("/api/exchange-rates", json={
            "from_currency": "EUR",
            "to_currency": "USD",
            "rate": 1.1,
        }, headers=auth_headers)
        rate_id = create.get_json()["id"]

        resp = client.delete(
            f"/api/exchange-rates/{rate_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete_rate_not_found(self, client, auth_headers):
        resp = client.delete("/api/exchange-rates/999999", headers=auth_headers)
        assert resp.status_code == 404


class TestCurrencies:
    def test_list_currencies(self, client):
        resp = client.get("/api/exchange-rates/currencies")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert "IRR" in data
        assert "USD" in data
