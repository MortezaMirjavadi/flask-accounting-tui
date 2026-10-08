"""E2E tests for Alerts API (/api/alerts)."""

import pytest


class TestAlerts:
    def test_get_alerts(self, client, auth_headers):
        resp = client.get("/api/alerts/", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_alerts_without_auth(self, client):
        resp = client.get("/api/alerts/")
        assert resp.status_code == 400
