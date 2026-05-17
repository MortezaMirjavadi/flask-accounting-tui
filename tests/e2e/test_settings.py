"""E2E tests for Settings API (/api/settings)."""

import pytest


class TestSettings:
    def test_reset_all_data(self, client, auth_headers):
        resp = client.post("/api/settings/reset", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data

    def test_reset_without_auth(self, client):
        resp = client.post("/api/settings/reset")
        assert resp.status_code == 400
