"""E2E tests for Installments API (/api/installments)."""

import pytest


class TestInstallmentPlans:
    def test_create_plan(self, client, auth_headers, category_id, wallet_id):
        resp = client.post("/api/installments/plans", json={
            "title": "Car Loan",
            "total_amount": 12000000,
            "installment_count": 12,
            "installment_amount": 1000000,
            "start_date": "1403-01-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Car Loan"

    def test_create_plan_missing_title(self, client, auth_headers, category_id):
        resp = client.post("/api/installments/plans", json={
            "total_amount": 1000000,
            "installment_count": 10,
            "start_date": "1403-01-01",
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_plan_invalid_amount(self, client, auth_headers, category_id):
        resp = client.post("/api/installments/plans", json={
            "title": "Bad Plan",
            "total_amount": -100,
            "installment_count": 10,
            "start_date": "1403-01-01",
            "category_id": category_id,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_plans(self, client, auth_headers, category_id, wallet_id):
        client.post("/api/installments/plans", json={
            "title": "ListedPlan",
            "total_amount": 600000,
            "installment_count": 6,
            "start_date": "1403-02-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)

        resp = client.get("/api/installments/plans", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_plans_with_status_filter(self, client, auth_headers):
        resp = client.get(
            "/api/installments/plans?status=active",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_plan(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/installments/plans", json={
            "title": "GetPlan",
            "total_amount": 300000,
            "installment_count": 3,
            "start_date": "1403-03-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        plan_id = create.get_json()["id"]

        resp = client.get(
            f"/api/installments/plans/{plan_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_get_plan_not_found(self, client, auth_headers):
        resp = client.get("/api/installments/plans/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_generate_installments(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/installments/plans", json={
            "title": "GenPlan",
            "total_amount": 500000,
            "installment_count": 5,
            "start_date": "1403-04-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        plan_id = create.get_json()["id"]

        resp = client.post(
            f"/api/installments/plans/{plan_id}/generate",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_cancel_plan(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/installments/plans", json={
            "title": "CancelPlan",
            "total_amount": 200000,
            "installment_count": 2,
            "start_date": "1403-05-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        plan_id = create.get_json()["id"]

        resp = client.post(
            f"/api/installments/plans/{plan_id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestInstallmentPayments:
    def test_pay_installment(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/installments/plans", json={
            "title": "PayPlan",
            "total_amount": 300000,
            "installment_count": 3,
            "start_date": "1403-06-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        plan_id = create.get_json()["id"]

        # Generate installments
        gen_resp = client.post(
            f"/api/installments/plans/{plan_id}/generate",
            headers=auth_headers,
        )
        installments = gen_resp.get_json()
        if installments:
            inst_id = installments[0]["id"]
            resp = client.post("/api/installments/pay", json={
                "installment_ids": [inst_id],
                "paid_date": "1403-06-05",
            }, headers=auth_headers)
            assert resp.status_code == 200

    def test_pay_installment_missing_ids(self, client, auth_headers):
        resp = client.post("/api/installments/pay", json={
            "paid_date": "1403-06-05",
        }, headers=auth_headers)
        assert resp.status_code == 400


class TestInstallmentViews:
    def test_upcoming_installments(self, client, auth_headers):
        resp = client.get(
            "/api/installments/upcoming?days=30",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_overdue_installments(self, client, auth_headers):
        resp = client.get("/api/installments/overdue", headers=auth_headers)
        assert resp.status_code == 200

    def test_remaining_debt(self, client, auth_headers):
        resp = client.get("/api/installments/debt", headers=auth_headers)
        assert resp.status_code == 200

    def test_change_due_date(self, client, auth_headers, category_id, wallet_id):
        create = client.post("/api/installments/plans", json={
            "title": "DueDatePlan",
            "total_amount": 100000,
            "installment_count": 1,
            "start_date": "1403-07-01",
            "due_day_of_month": 1,
            "category_id": category_id,
            "wallet_id": wallet_id,
        }, headers=auth_headers)
        plan_id = create.get_json()["id"]

        gen = client.post(
            f"/api/installments/plans/{plan_id}/generate",
            headers=auth_headers,
        )
        installments = gen.get_json()
        if installments:
            inst_id = installments[0]["id"]
            resp = client.put(
                f"/api/installments/{inst_id}/due-date",
                json={"due_date": "1403-07-15"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
