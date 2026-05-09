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

bp = Blueprint('reports', __name__)


def _current_jalali_date() -> jdatetime.date:
    return jdatetime.date.fromgregorian(date=datetime.now().date())


@bp.route("/daily", methods=["GET"])
def daily_report():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    date = request.args.get("date", "").strip()
    if not date:
        date = _current_jalali_date().strftime("%Y-%m-%d")

    try:
        report = get_daily_report(user_id, date)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/weekly", methods=["GET"])
def weekly_report():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    start_date = request.args.get("start_date", "").strip()
    if not start_date:
        current = _current_jalali_date()
        start_date = (current - timedelta(days=current.weekday() + 2)).strftime("%Y-%m-%d")

    try:
        report = get_weekly_report(user_id, start_date)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/monthly", methods=["GET"])
def monthly_report():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    year = request.args.get("year", type=int) or current.year
    month = request.args.get("month", type=int) or current.month

    try:
        report = get_monthly_report(user_id, year, month)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(asdict(report))


@bp.route("/transactions/summary", methods=["GET"])
def transactions_summary():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    report = ReportingService.get_monthly_report(user_id, current.year, current.month)
    return jsonify(
        {
            "total_income": report.summary.total_income,
            "total_cost": report.summary.total_expenses,
            "balance": report.summary.net,
        }
    )


@bp.route("/transactions/category", methods=["GET"])
def report_by_category():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    report = ReportingService.get_monthly_report(user_id, current.year, current.month)
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
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    results = []
    year = current.year
    month = current.month
    for _ in range(6):
        report = ReportingService.get_monthly_report(user_id, year, month)
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    current = _current_jalali_date()
    report = ReportingService.get_monthly_report(user_id, current.year, current.month)
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
    user_id, err = get_user_id_from_request()
    if err:
        return err

    current = _current_jalali_date()
    year = request.args.get("year", type=int) or current.year
    month = request.args.get("month", type=int) or current.month

    try:
        report = ReportingService.get_monthly_report(user_id, year, month)
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
    """Top purchased items ranked by total spent."""
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
    """Chronological price history for a specific item."""
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400
    limit = request.args.get("limit", 50, type=int)
    try:
        result = ItemReportService.get_price_history(user_id, name, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/items/monthly-basket", methods=["GET"])
def item_monthly_basket():
    """Monthly item basket: items bought each month with quantities and costs."""
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
    """Items aggregated by transaction category."""
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
    """Spending velocity: consumption speed and next-purchase predictions."""
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
    """Source-based price comparison for items."""
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
    """Personal CPI-like inflation index based on transaction items."""
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
    """Detect items with price spikes above threshold."""
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
    """For each item, find the source with the lowest average price."""
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 20, type=int)
    try:
        result = ItemReportService.get_best_stores(user_id, limit=limit)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
