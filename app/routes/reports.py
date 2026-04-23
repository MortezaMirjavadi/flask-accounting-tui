from collections import defaultdict
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict, gregorian_to_jalali
from database import get_connection

bp = Blueprint('reports', __name__)


@bp.route("/transactions/summary", methods=["GET"])
def transactions_summary():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.deleted_at IS NULL
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    
    total_income = row["total_income"] or 0
    total_cost = row["total_cost"] or 0
    
    return jsonify({
        "total_income": total_income,
        "total_cost": total_cost,
        "balance": total_income - total_cost,
    })


@bp.route("/transactions/category", methods=["GET"])
def report_by_category():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            c.name AS category_name,
            c.type AS category_type,
            COALESCE(SUM(t.amount), 0) AS total
        FROM categories c
        LEFT JOIN transactions t ON c.id = t.category_id AND t.deleted_at IS NULL
        WHERE c.user_id = ? AND c.deleted_at IS NULL
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/transactions/monthly", methods=["GET"])
def report_by_month():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            date AS raw_date,
            COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.deleted_at IS NULL
        GROUP BY raw_date
        ORDER BY raw_date
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    # Aggregate by Jalali month
    from collections import defaultdict
    import datetime

    monthly = defaultdict(lambda: {"total_income": 0, "total_cost": 0})
    for r in rows:
        jalali = gregorian_to_jalali(r["raw_date"])
        jalali_month = jalali[:7]  # YYYY-MM
        monthly[jalali_month]["total_income"] += r["total_income"] or 0
        monthly[jalali_month]["total_cost"] += r["total_cost"] or 0

    results = []
    for month in sorted(monthly.keys()):
        results.append({
            "month": month,
            "total_income": monthly[month]["total_income"],
            "total_cost": monthly[month]["total_cost"],
            "balance": monthly[month]["total_income"] - monthly[month]["total_cost"],
        })
    return jsonify(results)


@bp.route("/transactions/category-chart", methods=["GET"])
def report_category_chart():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            c.name AS category_name,
            c.type AS category_type,
            COALESCE(SUM(t.amount), 0) AS total
        FROM categories c
        LEFT JOIN transactions t ON c.id = t.category_id AND t.deleted_at IS NULL
        WHERE c.user_id = ? AND c.deleted_at IS NULL
        GROUP BY c.id
        HAVING total > 0
        ORDER BY total DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/budget", methods=["GET"])
def budget_report():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    
    if year is None or month is None:
        return jsonify({"error": "year and month query parameters are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Find the budget period
    cursor.execute(
        "SELECT * FROM budget_periods WHERE user_id = ? AND year = ? AND month = ? AND deleted_at IS NULL",
        (user_id, year, month),
    )
    period = cursor.fetchone()
    
    if period is None:
        conn.close()
        return jsonify({"error": "No budget period found for this year/month"}), 404

    period_id = period["id"]

    # Get all budget items for this period with category info
    cursor.execute(
        "SELECT bi.*, c.name as category_name "
        "FROM budget_items bi "
        "JOIN categories c ON bi.category_id = c.id "
        "WHERE bi.budget_period_id = ? AND bi.deleted_at IS NULL",
        (period_id,),
    )
    items = cursor.fetchall()

    # Calculate date range for Jalali month
    import jdatetime as _jd
    import datetime
    
    try:
        first_day = _jd.date(year, month, 1)
        if month < 12:
            last_day_greg = _jd.date(year, month + 1, 1).togregorian() - datetime.timedelta(days=1)
        else:
            last_day_greg = _jd.date(year + 1, 1, 1).togregorian() - datetime.timedelta(days=1)
        
        greg_start = first_day.togregorian().strftime("%Y-%m-%d")
        greg_end = last_day_greg.strftime("%Y-%m-%d")
    except Exception:
        conn.close()
        return jsonify({"error": "Invalid date"}), 400

    categories_report = []
    total_planned = 0
    total_spent = 0

    for item in items:
        cat_id = item["category_id"]
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions "
            "WHERE user_id = ? AND category_id = ? AND date >= ? AND date <= ? AND deleted_at IS NULL",
            (user_id, cat_id, greg_start, greg_end),
        )
        spent_row = cursor.fetchone()
        spent = spent_row["total"] if spent_row else 0
        remaining = item["planned_amount"] - spent
        
        categories_report.append({
            "category_id": cat_id,
            "category_name": item["category_name"],
            "planned_amount": item["planned_amount"],
            "total_spent": spent,
            "remaining_amount": remaining,
        })
        total_planned += item["planned_amount"]
        total_spent += spent

    conn.close()
    
    return jsonify({
        "period": row_to_dict(period),
        "categories": categories_report,
        "total_planned": total_planned,
        "total_spent": total_spent,
        "total_remaining": total_planned - total_spent,
    })
