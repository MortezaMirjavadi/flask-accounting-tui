from dataclasses import asdict
from datetime import datetime, timedelta

import jdatetime
from flask import Blueprint, jsonify, request

from app.services.reporting_service import (
    ReportingService,
    get_daily_report,
    get_monthly_report,
    get_weekly_report,
)
from app.services.item_report_service import ItemReportService
from app.utils.helpers import get_user_id_from_request
from services.forecast_service import ForecastService

bp = Blueprint('reports', __name__)


def _current_jalali_date() -> jdatetime.date:
    return jdatetime.date.fromgregorian(date=datetime.now().date())


@bp.route("/daily", methods=["GET"])
def daily_report():
    """Get daily financial report.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: date
        in: query
        type: string
        description: Jalali date (YYYY-MM-DD)
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Daily report summary
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    date = request.args.get("date", "").strip()
    if not date:
        date = _current_jalali_date().strftime("%Y-%m-%d")

    wallet_id = request.args.get("wallet_id", type=int)

    try:
        report = get_daily_report(user_id, date, wallet_id=wallet_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/weekly", methods=["GET"])
def weekly_report():
    """Get weekly financial report.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: start_date
        in: query
        type: string
        description: Jalali start date (YYYY-MM-DD)
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Weekly report summary
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    start_date = request.args.get("start_date", "").strip()
    if not start_date:
        current = _current_jalali_date()
        start_date = (current - timedelta(days=current.weekday() + 2)).strftime("%Y-%m-%d")

    wallet_id = request.args.get("wallet_id", type=int)

    try:
        report = get_weekly_report(user_id, start_date, wallet_id=wallet_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/monthly", methods=["GET"])
def monthly_report():
    """Get monthly financial report.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: year
        in: query
        type: integer
      - name: month
        in: query
        type: integer
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Monthly report summary
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    year = request.args.get("year", type=int) or current.year
    month = request.args.get("month", type=int) or current.month
    wallet_id = request.args.get("wallet_id", type=int)

    try:
        report = get_monthly_report(user_id, year, month, wallet_id=wallet_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/transactions/summary", methods=["GET"])
def transactions_summary():
    """Get current month transaction summary.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Income, cost, and balance for current month
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    wallet_id = request.args.get("wallet_id", type=int)
    report = ReportingService.get_monthly_report(user_id, current.year, current.month, wallet_id=wallet_id)
    return jsonify(
        {
            "total_income": report.summary.total_income,
            "total_cost": report.summary.total_expenses,
            "balance": report.summary.net,
        }
    )


@bp.route("/transactions/category", methods=["GET"])
def report_by_category():
    """Get current month expenses grouped by category.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Category breakdown for current month
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    wallet_id = request.args.get("wallet_id", type=int)
    report = ReportingService.get_monthly_report(user_id, current.year, current.month, wallet_id=wallet_id)
    return jsonify(
        [
            {
                "category_name": row.category_name,
                "category_type": "cost",
                "total": row.actual_amount,
            }
            for row in report.category_breakdown
            if row.actual_amount > 0
        ]
    )


@bp.route("/transactions/monthly", methods=["GET"])
def report_by_month():
    """Get last 6 months transaction trend.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Monthly income, cost, and balance for last 6 months
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    results = []
    year = current.year
    month = current.month
    wallet_id = request.args.get("wallet_id", type=int)
    for _ in range(6):
        report = ReportingService.get_monthly_report(user_id, year, month, wallet_id=wallet_id)
        results.append(
            {
                "month": report.month_label,
                "total_income": report.summary.total_income,
                "total_cost": report.summary.total_expenses,
                "balance": report.summary.net,
            }
        )
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
    results.reverse()
    return jsonify(results)


@bp.route("/transactions/category-chart", methods=["GET"])
def report_category_chart():
    """Get category chart data for current month.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Category spending data for charting
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    wallet_id = request.args.get("wallet_id", type=int)
    report = ReportingService.get_monthly_report(user_id, current.year, current.month, wallet_id=wallet_id)
    return jsonify(
        [
            {
                "category_name": row.category_name,
                "category_type": "cost",
                "total": row.actual_amount,
            }
            for row in report.category_breakdown
            if row.actual_amount > 0
        ]
    )


@bp.route("/budget", methods=["GET"])
def budget_report():
    """Get budget performance report for a month.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: year
        in: query
        type: integer
      - name: month
        in: query
        type: integer
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Budget vs actual spending per category
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    year = request.args.get("year", type=int) or current.year
    month = request.args.get("month", type=int) or current.month
    wallet_id = request.args.get("wallet_id", type=int)

    try:
        report = ReportingService.get_monthly_report(user_id, year, month, wallet_id=wallet_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "period": {"year": year, "month": month},
            "categories": [
                {
                    "category_id": row.category_id,
                    "category_name": row.category_name,
                    "planned_amount": row.planned_amount,
                    "total_spent": row.actual_amount,
                    "remaining_amount": row.remaining,
                }
                for row in report.category_breakdown
            ],
            "total_planned": sum(row.planned_amount for row in report.category_breakdown),
            "total_spent": report.summary.total_expenses,
            "total_remaining": sum(row.remaining for row in report.category_breakdown),
        }
    )


# ── Item-Level Analytics Endpoints ────────────────────────────────────


@bp.route("/items/top", methods=["GET"])
def item_top_purchased():
    """Top purchased items ranked by total spent.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of top purchased items
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 20, type=int)
    try:
        result = ItemReportService.get_top_items(user_id, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/price-history", methods=["GET"])
def item_price_history():
    """Chronological price history for a specific item.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: name
        in: query
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        default: 50
    responses:
      200:
        description: Price history entries
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "پارامتر 'name' الزامی است"}), 400
    limit = request.args.get("limit", 50, type=int)
    try:
        result = ItemReportService.get_price_history(user_id, name, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/monthly-basket", methods=["GET"])
def item_monthly_basket():
    """Monthly item basket: items bought each month with quantities and costs.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: months
        in: query
        type: integer
        default: 6
    responses:
      200:
        description: Monthly basket breakdown
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    months = request.args.get("months", 6, type=int)
    try:
        result = ItemReportService.get_monthly_basket(user_id, months=months)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/by-category", methods=["GET"])
def item_by_category():
    """Items aggregated by transaction category.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        default: 50
    responses:
      200:
        description: Items grouped by category
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 50, type=int)
    try:
        result = ItemReportService.get_items_by_category(user_id, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/velocity", methods=["GET"])
def item_velocity():
    """Spending velocity: consumption speed and next-purchase predictions.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: min_purchases
        in: query
        type: integer
        default: 3
    responses:
      200:
        description: Spending velocity data
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    min_purchases = request.args.get("min_purchases", 3, type=int)
    try:
        result = ItemReportService.get_spending_velocity(user_id, min_purchases=min_purchases)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/price-comparison", methods=["GET"])
def item_price_comparison():
    """Wallet-based price comparison for items.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: name
        in: query
        type: string
    responses:
      200:
        description: Price comparison across wallets
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name = request.args.get("name", "").strip() or None
    try:
        result = ItemReportService.get_source_prices(user_id, item_name=name)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Personal Inflation Tracker ────────────────────────────────────────


@bp.route("/inflation/personal", methods=["GET"])
def personal_inflation():
    """Personal CPI-like inflation index based on transaction items.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_months
        in: query
        type: integer
        default: 3
      - name: min_purchases
        in: query
        type: integer
        default: 2
    responses:
      200:
        description: Personal inflation index
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    period_months = request.args.get("period_months", 3, type=int)
    min_purchases = request.args.get("min_purchases", 2, type=int)
    try:
        result = ItemReportService.get_personal_inflation(
            user_id, period_months=period_months, min_purchases=min_purchases
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/inflation/spikes", methods=["GET"])
def price_spikes():
    """Detect items with price spikes above threshold.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: threshold
        in: query
        type: number
        default: 0.3
      - name: lookback_months
        in: query
        type: integer
        default: 3
    responses:
      200:
        description: Items with significant price spikes
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    threshold = request.args.get("threshold", 0.3, type=float)
    lookback = request.args.get("lookback_months", 3, type=int)
    try:
        result = ItemReportService.detect_price_spikes(
            user_id, threshold=threshold, lookback_months=lookback
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/best-stores", methods=["GET"])
def best_stores():
    """For each item, find the wallet with the lowest average price.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Best store per item
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 20, type=int)
    try:
        result = ItemReportService.get_best_stores(user_id, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Cashflow Forecast ─────────────────────────────────────────────────


@bp.route("/forecast", methods=["GET"])
def forecast():
    """Projected cashflow forecast for the next 30 days.
    ---
    tags:
      - Reports
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_days
        in: query
        type: integer
        default: 30
    responses:
      200:
        description: Cashflow forecast projection
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    period_days = request.args.get("period_days", 30, type=int)
    try:
        report = ForecastService.forecast_balance(user_id, period_days=period_days)
        return jsonify(ForecastService.to_dict(report))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
