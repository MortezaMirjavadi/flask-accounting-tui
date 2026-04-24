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
