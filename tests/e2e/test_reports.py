"""E2E tests for Reports API (/api/reports)."""

import pytest


class TestDailyReport:
    def test_daily_report_default_date(self, client, auth_headers):
        resp = client.get("/api/reports/daily", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_income" in data or "summary" in data

    def test_daily_report_with_date(self, client, auth_headers):
        resp = client.get(
            "/api/reports/daily?date=1403-02-15",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_daily_report_with_wallet(self, client, auth_headers, wallet_id):
        resp = client.get(
            f"/api/reports/daily?wallet_id={wallet_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestWeeklyReport:
    def test_weekly_report(self, client, auth_headers):
        resp = client.get("/api/reports/weekly", headers=auth_headers)
        assert resp.status_code == 200

    def test_weekly_report_with_start_date(self, client, auth_headers):
        resp = client.get(
            "/api/reports/weekly?start_date=1403-02-10",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestMonthlyReport:
    def test_monthly_report(self, client, auth_headers):
        resp = client.get("/api/reports/monthly", headers=auth_headers)
        assert resp.status_code == 200

    def test_monthly_report_with_params(self, client, auth_headers):
        resp = client.get(
            "/api/reports/monthly?year=1403&month=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTransactionReports:
    def test_transactions_summary(self, client, auth_headers):
        resp = client.get(
            "/api/reports/transactions/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_income" in data
        assert "total_cost" in data

    def test_transactions_by_category(self, client, auth_headers):
        resp = client.get(
            "/api/reports/transactions/category",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_transactions_by_month(self, client, auth_headers):
        resp = client.get(
            "/api/reports/transactions/monthly",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 6

    def test_category_chart(self, client, auth_headers):
        resp = client.get(
            "/api/reports/transactions/category-chart",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestBudgetReport:
    def test_budget_report(self, client, auth_headers):
        resp = client.get("/api/reports/budget", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "period" in data
        assert "categories" in data


class TestItemReports:
    def test_top_items(self, client, auth_headers):
        resp = client.get("/api/reports/items/top", headers=auth_headers)
        assert resp.status_code == 200

    def test_price_history_missing_name(self, client, auth_headers):
        resp = client.get(
            "/api/reports/items/price-history",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_monthly_basket(self, client, auth_headers):
        resp = client.get("/api/reports/items/monthly-basket", headers=auth_headers)
        assert resp.status_code == 200

    def test_items_by_category(self, client, auth_headers):
        resp = client.get("/api/reports/items/by-category", headers=auth_headers)
        assert resp.status_code == 200

    def test_velocity(self, client, auth_headers):
        resp = client.get("/api/reports/items/velocity", headers=auth_headers)
        assert resp.status_code == 200

    def test_price_comparison(self, client, auth_headers):
        resp = client.get(
            "/api/reports/items/price-comparison",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_best_stores(self, client, auth_headers):
        resp = client.get("/api/reports/items/best-stores", headers=auth_headers)
        assert resp.status_code == 200


class TestInflation:
    def test_personal_inflation(self, client, auth_headers):
        resp = client.get(
            "/api/reports/inflation/personal",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_price_spikes(self, client, auth_headers):
        resp = client.get("/api/reports/inflation/spikes", headers=auth_headers)
        assert resp.status_code == 200


class TestForecast:
    def test_forecast(self, client, auth_headers):
        resp = client.get("/api/reports/forecast", headers=auth_headers)
        assert resp.status_code == 200

    def test_forecast_custom_period(self, client, auth_headers):
        resp = client.get(
            "/api/reports/forecast?period_days=60",
            headers=auth_headers,
        )
        assert resp.status_code == 200
