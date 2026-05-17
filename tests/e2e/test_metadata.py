"""E2E tests for Metadata API (/api/metadata) — contacts, tags, labels."""

import pytest


# ── Contacts ──────────────────────────────────────────────────────


class TestContactsCRUD:
    def test_create_contact(self, client, auth_headers):
        resp = client.post("/api/metadata/contacts", json={
            "name": "John Doe",
            "phone": "09121234567",
            "email": "john@example.com",
            "address": "Tehran",
            "notes": "Friend",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "John Doe"

    def test_create_contact_missing_name(self, client, auth_headers):
        resp = client.post("/api/metadata/contacts", json={
            "phone": "09121234567",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_contacts(self, client, auth_headers):
        client.post("/api/metadata/contacts", json={
            "name": "ListContact",
        }, headers=auth_headers)
        resp = client.get("/api/metadata/contacts", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_contacts_with_search(self, client, auth_headers):
        client.post("/api/metadata/contacts", json={
            "name": "Searchable Person",
        }, headers=auth_headers)
        resp = client.get(
            "/api/metadata/contacts?q=Search",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_contact(self, client, auth_headers):
        create = client.post("/api/metadata/contacts", json={
            "name": "GetContact",
        }, headers=auth_headers)
        cid = create.get_json()["id"]

        resp = client.get(f"/api/metadata/contacts/{cid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "GetContact"

    def test_get_contact_not_found(self, client, auth_headers):
        resp = client.get("/api/metadata/contacts/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_contact(self, client, auth_headers):
        create = client.post("/api/metadata/contacts", json={
            "name": "UpdateContact",
        }, headers=auth_headers)
        cid = create.get_json()["id"]

        resp = client.put(
            f"/api/metadata/contacts/{cid}",
            json={"name": "Updated Contact", "phone": "09199999999"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete_contact(self, client, auth_headers):
        create = client.post("/api/metadata/contacts", json={
            "name": "DeleteContact",
        }, headers=auth_headers)
        cid = create.get_json()["id"]

        resp = client.delete(f"/api/metadata/contacts/{cid}", headers=auth_headers)
        assert resp.status_code == 200


# ── Tags ──────────────────────────────────────────────────────────


class TestTagsCRUD:
    def test_create_tag(self, client, auth_headers):
        resp = client.post("/api/metadata/tags", json={
            "name": "urgent",
            "color": "#FF0000",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "urgent"

    def test_create_tag_missing_name(self, client, auth_headers):
        resp = client.post("/api/metadata/tags", json={
            "color": "#FF0000",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_tags(self, client, auth_headers):
        client.post("/api/metadata/tags", json={"name": "listable"}, headers=auth_headers)
        resp = client.get("/api/metadata/tags", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_tag(self, client, auth_headers):
        create = client.post("/api/metadata/tags", json={"name": "getme"}, headers=auth_headers)
        tid = create.get_json()["id"]
        resp = client.get(f"/api/metadata/tags/{tid}", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_tag_not_found(self, client, auth_headers):
        resp = client.get("/api/metadata/tags/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_tag(self, client, auth_headers):
        create = client.post("/api/metadata/tags", json={"name": "updateme"}, headers=auth_headers)
        tid = create.get_json()["id"]
        resp = client.put(
            f"/api/metadata/tags/{tid}",
            json={"name": "updated_tag", "color": "#00FF00"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete_tag(self, client, auth_headers):
        create = client.post("/api/metadata/tags", json={"name": "delme"}, headers=auth_headers)
        tid = create.get_json()["id"]
        resp = client.delete(f"/api/metadata/tags/{tid}", headers=auth_headers)
        assert resp.status_code == 200


class TestTransactionTags:
    def test_set_and_get_transaction_tags(self, client, auth_headers, category_id):
        # Create a transaction
        tx = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 500,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = tx.get_json()["id"]

        # Create a tag
        tag = client.post("/api/metadata/tags", json={"name": "tx_tag"}, headers=auth_headers)
        tag_id = tag.get_json()["id"]

        # Set tags
        resp = client.put(
            f"/api/metadata/transactions/{tx_id}/tags",
            json={"tag_ids": [tag_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Get tags
        resp = client.get(
            f"/api/metadata/transactions/{tx_id}/tags",
            headers=auth_headers,
        )
        assert resp.status_code == 200


# ── Labels ────────────────────────────────────────────────────────


class TestLabelsCRUD:
    def test_create_label(self, client, auth_headers):
        resp = client.post("/api/metadata/labels", json={
            "name": "important",
            "color": "#0000FF",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "important"

    def test_create_label_missing_name(self, client, auth_headers):
        resp = client.post("/api/metadata/labels", json={
            "color": "#0000FF",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_labels(self, client, auth_headers):
        client.post("/api/metadata/labels", json={"name": "listable_label"}, headers=auth_headers)
        resp = client.get("/api/metadata/labels", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_label(self, client, auth_headers):
        create = client.post("/api/metadata/labels", json={"name": "get_label"}, headers=auth_headers)
        lid = create.get_json()["id"]
        resp = client.get(f"/api/metadata/labels/{lid}", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_label_not_found(self, client, auth_headers):
        resp = client.get("/api/metadata/labels/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_label(self, client, auth_headers):
        create = client.post("/api/metadata/labels", json={"name": "upd_label"}, headers=auth_headers)
        lid = create.get_json()["id"]
        resp = client.put(
            f"/api/metadata/labels/{lid}",
            json={"name": "updated_label", "color": "#FFFF00"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete_label(self, client, auth_headers):
        create = client.post("/api/metadata/labels", json={"name": "del_label"}, headers=auth_headers)
        lid = create.get_json()["id"]
        resp = client.delete(f"/api/metadata/labels/{lid}", headers=auth_headers)
        assert resp.status_code == 200


class TestTransactionLabels:
    def test_set_and_get_transaction_labels(self, client, auth_headers, category_id):
        tx = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 700,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = tx.get_json()["id"]

        label = client.post("/api/metadata/labels", json={"name": "tx_label"}, headers=auth_headers)
        label_id = label.get_json()["id"]

        resp = client.put(
            f"/api/metadata/transactions/{tx_id}/labels",
            json={"label_ids": [label_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.get(
            f"/api/metadata/transactions/{tx_id}/labels",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestWalletLabels:
    def test_set_and_get_wallet_labels(self, client, auth_headers, wallet_id):
        label = client.post("/api/metadata/labels", json={"name": "w_label"}, headers=auth_headers)
        label_id = label.get_json()["id"]

        resp = client.put(
            f"/api/metadata/wallets/{wallet_id}/labels",
            json={"label_ids": [label_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.get(
            f"/api/metadata/wallets/{wallet_id}/labels",
            headers=auth_headers,
        )
        assert resp.status_code == 200
