"""E2E tests for Transactions API (/api/transactions)."""

import pytest


class TestTransactionsCRUD:
    def test_create_transaction(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/transactions", json={
            "date": "1403-02-15",
            "amount": 500000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "description": "Grocery shopping",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["amount"] == 500000
        assert data["record_type"] == "transaction"
        assert "id" in data

    def test_create_transaction_with_account(self, client, auth_headers, category_id, wallet_id):
        # Get default account
        resp = client.get(
            f"/api/wallets/{wallet_id}/accounts",
            headers=auth_headers,
        )
        accounts = resp.get_json()
        acc_id = accounts[0]["id"] if accounts else None

        resp = client.post("/api/transactions", json={
            "date": "1403-02-15",
            "amount": 100000,
            "category_id": category_id,
            "wallet_id": wallet_id,
            "account_id": acc_id,
            "description": "With account",
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_transaction_missing_date(self, client, auth_headers, category_id):
        resp = client.post("/api/transactions", json={
            "amount": 100,
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_transaction_negative_amount(self, client, auth_headers, category_id):
        resp = client.post("/api/transactions", json={
            "date": "1403-02-15",
            "amount": -500,
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_transaction_invalid_category(self, client, auth_headers):
        resp = client.post("/api/transactions", json={
            "date": "1403-02-15",
            "amount": 100,
            "category_id": 999999,
        }, headers=auth_headers)
        assert resp.status_code in (400, 404)

    def test_list_transactions(self, client, auth_headers, category_id):
        # Create one first
        client.post("/api/transactions", json={
            "date": "1403-02-15",
            "amount": 200,
            "category_id": category_id,
        }, headers=auth_headers)

        resp = client.get("/api/transactions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_transactions_with_filters(self, client, auth_headers, category_id):
        client.post("/api/transactions", json={
            "date": "1403-03-01",
            "amount": 300,
            "category_id": category_id,
        }, headers=auth_headers)

        resp = client.get(
            "/api/transactions?min_amount=200&max_amount=400",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_transactions_by_category_type(self, client, auth_headers, category_id):
        resp = client.get(
            "/api/transactions?category_type=cost",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_transaction(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 750,
            "category_id": category_id,
            "description": "Find me",
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        resp = client.get(
            f"/api/transactions/{tx_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["id"] == tx_id

    def test_get_transaction_not_found(self, client, auth_headers):
        resp = client.get("/api/transactions/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_transaction(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 1000,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        resp = client.put(
            f"/api/transactions/{tx_id}",
            json={
                "date": "1403-02-21",
                "amount": 1500,
                "category_id": category_id,
                "description": "Updated tx",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["amount"] == 1500

    def test_delete_transaction(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 500,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        resp = client.delete(
            f"/api/transactions/{tx_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTransactionItems:
    def test_add_item_to_transaction(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 300,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        resp = client.post(
            f"/api/transactions/{tx_id}/items",
            json={
                "name": "Milk",
                "quantity": 2,
                "unit": "liters",
                "unit_price": 150,
                "total_price": 300,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Milk"

    def test_list_transaction_items(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 300,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "Bread", "quantity": 1, "total_price": 300},
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/transactions/{tx_id}/items",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_update_transaction_item(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 500,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        item_resp = client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "Item", "quantity": 1, "total_price": 500},
            headers=auth_headers,
        )
        item_id = item_resp.get_json()["id"]

        resp = client.put(
            f"/api/transactions/{tx_id}/items/{item_id}",
            json={"name": "UpdatedItem", "quantity": 1, "total_price": 500},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "UpdatedItem"

    def test_delete_transaction_item(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 200,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]

        item_resp = client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "ToDelete", "quantity": 1, "total_price": 200},
            headers=auth_headers,
        )
        item_id = item_resp.get_json()["id"]

        resp = client.delete(
            f"/api/transactions/{tx_id}/items/{item_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTransactionItemReporting:
    def test_most_purchased_items(self, client, auth_headers, category_id):
        # Create a transaction with an item first
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 100,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]
        client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "FrequentItem", "quantity": 1, "total_price": 100},
            headers=auth_headers,
        )

        resp = client.get("/api/transactions/items/most-purchased", headers=auth_headers)
        assert resp.status_code == 200

    def test_search_items(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 100,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]
        client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "SearchableItem", "quantity": 1, "total_price": 100},
            headers=auth_headers,
        )

        resp = client.get(
            "/api/transactions/items/search?q=Searchable",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_search_items_missing_query(self, client, auth_headers):
        resp = client.get("/api/transactions/items/search", headers=auth_headers)
        assert resp.status_code == 400

    def test_item_stats(self, client, auth_headers, category_id):
        create = client.post("/api/transactions", json={
            "date": "1403-02-20",
            "amount": 100,
            "category_id": category_id,
        }, headers=auth_headers)
        tx_id = create.get_json()["id"]
        client.post(
            f"/api/transactions/{tx_id}/items",
            json={"name": "StatsItem", "quantity": 1, "total_price": 100},
            headers=auth_headers,
        )

        resp = client.get(
            "/api/transactions/items/stats?name=StatsItem",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTransactionTransfers:
    def test_create_transfer(self, client, auth_headers, wallet_id):
        # Get accounts
        resp = client.get(
            f"/api/wallets/{wallet_id}/accounts",
            headers=auth_headers,
        )
        accounts = resp.get_json()
        if len(accounts) < 2:
            # Create a second account
            client.post(
                f"/api/wallets/{wallet_id}/accounts",
                json={"name": "SecondAcc", "account_type": "bank", "amount": 5000000},
                headers=auth_headers,
            )
            resp = client.get(
                f"/api/wallets/{wallet_id}/accounts",
                headers=auth_headers,
            )
            accounts = resp.get_json()

        from_acc = accounts[0]["id"]
        to_acc = accounts[1]["id"]

        resp = client.post("/api/transactions", json={
            "is_transfer": True,
            "date": "1403-02-20",
            "amount": 100000,
            "from_account_id": from_acc,
            "to_account_id": to_acc,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["record_type"] == "transfer"
        assert data["is_transfer"] is True

    def test_create_transfer_same_account(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/accounts",
            headers=auth_headers,
        )
        accounts = resp.get_json()
        acc_id = accounts[0]["id"]

        resp = client.post("/api/transactions", json={
            "is_transfer": True,
            "date": "1403-02-20",
            "amount": 100,
            "from_account_id": acc_id,
            "to_account_id": acc_id,
        }, headers=auth_headers)
        assert resp.status_code == 400
