"""E2E tests for Wallets API (/api/wallets)."""

import pytest


class TestWalletsCRUD:
    def test_create_wallet(self, client, auth_headers):
        resp = client.post("/api/wallets", json={
            "name": "MyWallet",
            "currency": "IRR",
            "wallet_type": "personal",
            "amount": 5000000,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "MyWallet"
        assert data["currency"] == "IRR"
        assert "default_account_id" in data

    def test_create_wallet_missing_name(self, client, auth_headers):
        resp = client.post("/api/wallets", json={
            "currency": "IRR",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_wallet_invalid_currency(self, client, auth_headers):
        resp = client.post("/api/wallets", json={
            "name": "BadCurr",
            "currency": "XYZ",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_shared_wallet(self, client, auth_headers):
        resp = client.post("/api/wallets", json={
            "name": "SharedWallet",
            "wallet_type": "shared",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["wallet_type"] == "shared"

    def test_list_wallets(self, client, auth_headers, wallet_id):
        resp = client.get("/api/wallets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert data["total"] >= 1

    def test_get_wallet(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == wallet_id
        assert "accounts" in data
        assert "total_balance" in data

    def test_get_wallet_not_found(self, client, auth_headers):
        resp = client.get("/api/wallets/999999", headers=auth_headers)
        assert resp.status_code in (403, 404)

    def test_update_wallet(self, client, auth_headers, wallet_id):
        resp = client.put(
            f"/api/wallets/{wallet_id}",
            json={"name": "RenamedWallet", "currency": "IRR"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "RenamedWallet"

    def test_delete_wallet(self, client, auth_headers):
        # Create a wallet just for deletion
        resp = client.post("/api/wallets", json={
            "name": "ToDelete",
            "currency": "IRR",
        }, headers=auth_headers)
        wid = resp.get_json()["id"]
        resp = client.delete(f"/api/wallets/{wid}", headers=auth_headers)
        assert resp.status_code == 200


class TestWalletAccounts:
    def test_list_accounts(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/accounts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_create_account(self, client, auth_headers, wallet_id):
        resp = client.post(
            f"/api/wallets/{wallet_id}/accounts",
            json={
                "name": "BankAccount",
                "account_type": "bank",
                "bank_type": "mellat",
                "amount": 1000000,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "BankAccount"
        assert data["account_type"] == "bank"

    def test_create_account_missing_name(self, client, auth_headers, wallet_id):
        resp = client.post(
            f"/api/wallets/{wallet_id}/accounts",
            json={"account_type": "bank"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_get_account(self, client, auth_headers, wallet_id):
        # Create first
        resp = client.post(
            f"/api/wallets/{wallet_id}/accounts",
            json={"name": "GetMe", "account_type": "cash", "amount": 0},
            headers=auth_headers,
        )
        acc_id = resp.get_json()["id"]
        resp = client.get(
            f"/api/wallets/{wallet_id}/accounts/{acc_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["id"] == acc_id

    def test_update_account(self, client, auth_headers, wallet_id):
        resp = client.post(
            f"/api/wallets/{wallet_id}/accounts",
            json={"name": "UpdateMe", "account_type": "cash", "amount": 0},
            headers=auth_headers,
        )
        acc_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/wallets/{wallet_id}/accounts/{acc_id}",
            json={"name": "Updated", "account_type": "bank", "bank_type": "saman"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Updated"

    def test_delete_account(self, client, auth_headers, wallet_id):
        resp = client.post(
            f"/api/wallets/{wallet_id}/accounts",
            json={"name": "DeleteMe", "account_type": "cash", "amount": 0},
            headers=auth_headers,
        )
        acc_id = resp.get_json()["id"]
        resp = client.delete(
            f"/api/wallets/{wallet_id}/accounts/{acc_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestWalletBalance:
    def test_wallet_balance(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/balance",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_balance" in data
        assert "total_income" in data
        assert "total_cost" in data
        assert "accounts" in data

    def test_wallet_summary(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_balance" in data
        assert "transaction_count" in data


class TestWalletTransfers:
    def test_wallet_transfers_empty(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/transfers",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0


class TestWalletMembers:
    def test_list_members(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/members",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1  # At least the owner


class TestWalletInvitations:
    def test_list_invitations_empty(self, client, auth_headers):
        resp = client.get("/api/wallets/invitations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 0


class TestWalletActivity:
    def test_wallet_activity(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/wallets/{wallet_id}/activity",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data


class TestConsolidatedBalance:
    def test_consolidated_balance(self, client, auth_headers):
        resp = client.get("/api/wallets/consolidated", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "preferred_currency" in data
        assert "wallets" in data
