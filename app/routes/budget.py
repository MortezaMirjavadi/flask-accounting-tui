import sqlite3
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_budget_period_payload, validate_budget_item_payload
from app.services.budget_service import BudgetService
from database import get_connection

bp = Blueprint('budget', __name__)


# Period routes

@bp.route("/periods", methods=["GET"])
def list_periods():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    year_filter = request.args.get("year", type=int)
    month_filter = request.args.get("month", type=int)

    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            bp.*,
            COALESCE(bi.item_count, 0) as item_count
        FROM budget_periods bp
        LEFT JOIN (
            SELECT budget_period_id, COUNT(*) as item_count
            FROM budget_items
            GROUP BY budget_period_id
        ) bi ON bp.id = bi.budget_period_id
        WHERE bp.user_id = ?
    """
    params = [user_id]
    
    if year_filter is not None:
        query += " AND bp.year = ?"
        params.append(year_filter)
    if month_filter is not None:
        query += " AND bp.month = ?"
        params.append(month_filter)
    
    query += " ORDER BY bp.year DESC, bp.month DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/periods/with-items", methods=["GET"])
def list_periods_with_items():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    
    result = BudgetService.get_periods_with_items(user_id, year, month)
    return jsonify(result)


@bp.route("/periods", methods=["POST"])
def create_period():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_budget_period_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result, error = BudgetService.create_period(
        user_id, payload["year"], payload["month"]
    )
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify(result), 201


@bp.route("/periods/<int:period_id>", methods=["GET"])
def get_period(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    row = BudgetService.get_period(cursor, period_id, user_id)
    conn.close()
    
    if row is None:
        return jsonify({"error": "Budget period not found"}), 404
    
    return jsonify(row_to_dict(row))


@bp.route("/periods/<int:period_id>", methods=["PUT"])
def update_period(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_budget_period_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_period(cursor, period_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget period not found"}), 404
    
    try:
        cursor.execute(
            "UPDATE budget_periods SET year = ?, month = ? WHERE id = ? AND user_id = ?",
            (payload["year"], payload["month"], period_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Budget period already exists for this year/month"}), 400
    
    conn.close()
    return jsonify({"id": period_id, "year": payload["year"], "month": payload["month"]})


@bp.route("/periods/<int:period_id>", methods=["DELETE"])
def delete_period(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    success, error = BudgetService.delete_period(period_id, user_id)
    if not success:
        return jsonify({"error": error}), 404
    
    return jsonify({"message": "Budget period deleted"})


# Item routes

@bp.route("/items", methods=["POST"])
def create_item():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_budget_item_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    period_id = data.get("budget_period_id")
    try:
        period_id = int(period_id)
    except (TypeError, ValueError):
        return jsonify({"error": "budget_period_id is required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_period(cursor, period_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget period not found"}), 404

    # Verify category belongs to user
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?",
        (payload["category_id"], user_id),
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found or does not belong to you"}), 400

    try:
        cursor.execute(
            "INSERT INTO budget_items (budget_period_id, category_id, planned_amount, notes) VALUES (?, ?, ?, ?)",
            (period_id, payload["category_id"], payload["planned_amount"], payload["notes"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Budget item already exists for this category in this period"}), 400
    
    conn.close()
    return jsonify({"id": new_id, "budget_period_id": period_id, **payload}), 201


@bp.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    row = BudgetService.get_item(cursor, item_id, user_id)
    conn.close()
    
    if row is None:
        return jsonify({"error": "Budget item not found"}), 404
    
    return jsonify(row_to_dict(row))


@bp.route("/periods/<int:period_id>/items", methods=["GET"])
def list_items(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_period(cursor, period_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget period not found"}), 404
    
    cursor.execute(
        "SELECT bi.*, c.name as category_name, c.type as category_type "
        "FROM budget_items bi "
        "JOIN categories c ON bi.category_id = c.id "
        "WHERE bi.budget_period_id = ?",
        (period_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_budget_item_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    
    row = BudgetService.get_item(cursor, item_id, user_id)
    if row is None:
        conn.close()
        return jsonify({"error": "Budget item not found"}), 404

    # Verify category belongs to user
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?",
        (payload["category_id"], user_id),
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found or does not belong to you"}), 400

    try:
        cursor.execute(
            "UPDATE budget_items SET category_id = ?, planned_amount = ?, notes = ? WHERE id = ?",
            (payload["category_id"], payload["planned_amount"], payload["notes"], item_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Budget item already exists for this category in this period"}), 400
    
    conn.close()
    return jsonify({"id": item_id, **payload})


@bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_item(cursor, item_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget item not found"}), 404
    
    cursor.execute("DELETE FROM budget_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Budget item deleted"})
