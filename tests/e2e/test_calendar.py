"""E2E tests for Calendar API (/api/calendar)."""

import pytest


class TestCalendarEvents:
    def test_create_event(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/calendar/events", json={
            "title": "Monthly Rent",
            "amount": 5000000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "monthly",
            "start_date": "1403-01-01",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "event" in data
        assert data["event"]["title"] == "Monthly Rent"

    def test_create_event_missing_title(self, client, auth_headers, category_id):
        resp = client.post("/api/calendar/events", json={
            "amount": 1000,
            "category_id": category_id,
            "frequency": "once",
            "start_date": "1403-01-01",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_events(self, client, auth_headers, category_id, wallet_id):
        client.post("/api/calendar/events", json={
            "title": "Listed Event",
            "amount": 1000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "once",
            "start_date": "1403-02-01",
        }, headers=auth_headers)

        resp = client.get("/api/calendar/events", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_events_include_inactive(self, client, auth_headers):
        resp = client.get(
            "/api/calendar/events?include_inactive=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_event(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/calendar/events", json={
            "title": "Get Event",
            "amount": 2000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "once",
            "start_date": "1403-03-01",
        }, headers=auth_headers)
        event_id = create.get_json()["event"]["id"]

        resp = client.get(
            f"/api/calendar/events/{event_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Get Event"

    def test_get_event_not_found(self, client, auth_headers):
        resp = client.get("/api/calendar/events/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_event(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/calendar/events", json={
            "title": "Update Event",
            "amount": 3000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "once",
            "start_date": "1403-04-01",
        }, headers=auth_headers)
        event_id = create.get_json()["event"]["id"]

        resp = client.put(
            f"/api/calendar/events/{event_id}",
            json={"title": "Updated Event", "amount": 4000},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete_event(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/calendar/events", json={
            "title": "Delete Event",
            "amount": 1000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "once",
            "start_date": "1403-05-01",
        }, headers=auth_headers)
        event_id = create.get_json()["event"]["id"]

        resp = client.delete(
            f"/api/calendar/events/{event_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestCalendarEventActions:
    def _create_event(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/calendar/events", json={
            "title": "Action Event",
            "amount": 1000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "frequency": "monthly",
            "start_date": "1403-01-01",
        }, headers=auth_headers)
        return resp.get_json()["event"]["id"]

    def test_cancel_event(self, client, auth_headers, category_id, wallet_id):
        event_id = self._create_event(client, auth_headers, category_id, wallet_id)
        resp = client.post(
            f"/api/calendar/events/{event_id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_pause_event(self, client, auth_headers, category_id, wallet_id):
        event_id = self._create_event(client, auth_headers, category_id, wallet_id)
        resp = client.post(
            f"/api/calendar/events/{event_id}/pause",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_resume_event(self, client, auth_headers, category_id, wallet_id):
        event_id = self._create_event(client, auth_headers, category_id, wallet_id)
        client.post(
            f"/api/calendar/events/{event_id}/pause",
            headers=auth_headers,
        )
        resp = client.post(
            f"/api/calendar/events/{event_id}/resume",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestCalendarInstances:
    def test_list_instances(self, client, auth_headers):
        resp = client.get("/api/calendar/instances", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_instances_with_date_range(self, client, auth_headers):
        resp = client.get(
            "/api/calendar/instances?start_date=1403-01-01&end_date=1403-12-29",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_instances_include_cancelled(self, client, auth_headers):
        resp = client.get(
            "/api/calendar/instances?include_cancelled=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200
