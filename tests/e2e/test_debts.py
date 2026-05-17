"""E2E tests for Debts API (/api/debts)."""

import pytest


class TestDebtsCRUD:
    def _debt_payload(self, category_id=None, wallet_id=None):
        return {
            "type": "payable",
            "counterparty_name": "Ali",
            "counterparty_type": "person",
            "title": "Loan from Ali",
            "original_amount": 10000000,
            "issue_date": "1403-01-01",
            "due_date": "1403-06-01",
            "priority": "normal",
            "wallet_id": wallet_id,
        }

    def test_create_debt(self, client, auth_headers, wallet_id):
        resp = client.post("/api/debts", json=self._debt_payload(wallet_id=wallet_id), headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["type"] == "payable"
        assert data["counterparty_name"] == "Ali"
        assert "id" in data

    def test_create_receivable(self, client, auth_headers, wallet_id):
        payload = self._debt_payload(wallet_id=wallet_id)
        payload["type"] = "receivable"
        payload["counterparty_name"] = "Sara"
        resp = client.post("/api/debts", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["type"] == "receivable"

    def test_create_debt_missing_counterparty(self, client, auth_headers):
        resp = client.post("/api/debts", json={
            "type": "payable",
            "title": "No Counterparty",
            "original_amount": 1000,
            "issue_date": "1403-01-01",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_debt_invalid_type(self, client, auth_headers):
        resp = client.post("/api/debts", json={
            "type": "invalid",
            "counterparty_name": "X",
            "title": "Bad",
            "original_amount": 1000,
            "issue_date": "1403-01-01",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_debt_negative_amount(self, client, auth_headers):
        resp = client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "X",
            "title": "Bad Amount",
            "original_amount": -500,
            "issue_date": "1403-01-01",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_debts(self, client, auth_headers, wallet_id):
        client.post("/api/debts", json=self._debt_payload(wallet_id=wallet_id), headers=auth_headers)
        resp = client.get("/api/debts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_debts_with_type_filter(self, client, auth_headers):
        resp = client.get("/api/debts?type=payable", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_debts_with_status_filter(self, client, auth_headers):
        resp = client.get("/api/debts?status=active", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_debt(self, client, auth_headers, wallet_id):
        create = client.post("/api/debts", json=self._debt_payload(wallet_id=wallet_id), headers=auth_headers)
        debt_id = create.get_json()["id"]

        resp = client.get(f"/api/debts/{debt_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["id"] == debt_id

    def test_get_debt_not_found(self, client, auth_headers):
        resp = client.get("/api/debts/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_debt(self, client, auth_headers, wallet_id):
        create = client.post("/api/debts", json=self._debt_payload(wallet_id=wallet_id), headers=auth_headers)
        debt_id = create.get_json()["id"]

        resp = client.put(
            f"/api/debts/{debt_id}",
            json={"title": "Updated Loan"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestDebtPayments:
    def test_add_payment(self, client, auth_headers, wallet_id):
        create = client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "PayMe",
            "title": "Payable Debt",
            "original_amount": 5000000,
            "issue_date": "1403-01-01",
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        debt_id = create.get_json()["id"]

        resp = client.post(f"/api/debts/{debt_id}/payments", json={
            "amount": 1000000,
            "payment_date": "1403-02-01",
            "payment_method": "cash",
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_list_payments(self, client, auth_headers, wallet_id):
        create = client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "ListPay",
            "title": "Debt with payments",
            "original_amount": 3000000,
            "issue_date": "1403-01-01",
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        debt_id = create.get_json()["id"]

        client.post(f"/api/debts/{debt_id}/payments", json={
            "amount": 500000,
            "payment_date": "1403-02-01",
        }, headers=auth_headers)

        resp = client.get(
            f"/api/debts/{debt_id}/payments",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_reverse_payment(self, client, auth_headers, wallet_id):
        create = client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "RevPay",
            "title": "Reversible Debt",
            "original_amount": 2000000,
            "issue_date": "1403-01-01",
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        debt_id = create.get_json()["id"]

        pay_resp = client.post(f"/api/debts/{debt_id}/payments", json={
            "amount": 500000,
            "payment_date": "1403-02-01",
        }, headers=auth_headers)
        payment_id = pay_resp.get_json()["id"]

        resp = client.post(
            f"/api/debts/payments/{payment_id}/reverse",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestDebtStatusTransitions:
    def _create_debt(self, client, auth_headers, wallet_id):
        resp = client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "StatusTest",
            "title": "Status Debt",
            "original_amount": 1000000,
            "issue_date": "1403-01-01",
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        return resp.get_json()["id"]

    def test_write_off(self, client, auth_headers, wallet_id):
        debt_id = self._create_debt(client, auth_headers, wallet_id)
        resp = client.post(
            f"/api/debts/{debt_id}/write-off",
            json={"note": "Cannot collect"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_cancel_debt(self, client, auth_headers, wallet_id):
        debt_id = self._create_debt(client, auth_headers, wallet_id)
        resp = client.post(
            f"/api/debts/{debt_id}/cancel",
            json={"note": "Cancelled"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_settle_debt(self, client, auth_headers, wallet_id):
        debt_id = self._create_debt(client, auth_headers, wallet_id)
        resp = client.post(
            f"/api/debts/{debt_id}/settle",
            json={"note": "Fully paid"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_status_history(self, client, auth_headers, wallet_id):
        debt_id = self._create_debt(client, auth_headers, wallet_id)
        client.post(
            f"/api/debts/{debt_id}/settle",
            headers=auth_headers,
        )
        resp = client.get(
            f"/api/debts/{debt_id}/history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)


class TestDebtAnalytics:
    def test_summary(self, client, auth_headers):
        resp = client.get("/api/debts/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_payable" in data or "total_receivable" in data

    def test_overdue(self, client, auth_headers):
        resp = client.get("/api/debts/overdue", headers=auth_headers)
        assert resp.status_code == 200

    def test_due_soon(self, client, auth_headers):
        resp = client.get("/api/debts/due-soon?days=7", headers=auth_headers)
        assert resp.status_code == 200

    def test_aging_report(self, client, auth_headers):
        resp = client.get("/api/debts/aging", headers=auth_headers)
        assert resp.status_code == 200

    def test_monthly_repayments(self, client, auth_headers):
        resp = client.get(
            "/api/debts/repayments/monthly?months=6",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_top_counterparties(self, client, auth_headers):
        resp = client.get(
            "/api/debts/counterparties/top?limit=10",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_counterparty_balance(self, client, auth_headers, wallet_id):
        client.post("/api/debts", json={
            "type": "payable",
            "counterparty_name": "BalTest",
            "title": "Balance Debt",
            "original_amount": 1000000,
            "issue_date": "1403-01-01",
            "wallet_id": wallet_id,
        }, headers=auth_headers)

        resp = client.get(
            "/api/debts/counterparty/BalTest",
            headers=auth_headers,
        )
        assert resp.status_code == 200
