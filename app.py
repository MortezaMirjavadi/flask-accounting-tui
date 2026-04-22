import sqlite3
from flask import Flask, jsonify, request
from database import get_connection, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from models import (
    validate_category_payload,
    validate_source_payload,
    validate_transaction_payload,
    validate_user_payload,
    validate_budget_period_payload,
    validate_budget_item_payload,
    gregorian_to_jalali,
)

app = Flask(__name__)


@app.before_request
def ensure_db():
    init_db()


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def get_user_id_from_request():
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return None, (jsonify({"error": "Username is required"}), 400)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None, (jsonify({"error": "User not found"}), 404)
    return row["id"], None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_user_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (payload["username"],))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already exists"}), 400

    password_hash = generate_password_hash(payload["password"])
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (payload["username"], password_hash),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "username": payload["username"]}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401
    return jsonify({"id": row["id"], "username": row["username"]})


@app.route("/auth/me", methods=["GET"])
def me():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(row_to_dict(row))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.route("/categories", methods=["GET"])
def list_categories():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name_filter = request.args.get("name", "").strip()
    type_filter = request.args.get("type", "").strip()

    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM categories WHERE user_id = ?"
    params = [user_id]
    if name_filter:
        query += " AND name LIKE ?"
        params.append(f"%{name_filter}%")
    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/categories", methods=["POST"])
def create_category():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_category_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)",
            (user_id, payload["name"], payload["type"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": new_id, **payload}), 201


@app.route("/categories/<int:cat_id>", methods=["GET"])
def get_category(cat_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Category not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_category_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    try:
        cursor.execute(
            "UPDATE categories SET name = ?, type = ? WHERE id = ? AND user_id = ?",
            (payload["name"], payload["type"], cat_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": cat_id, **payload})


@app.route("/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Category deleted"})


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@app.route("/sources", methods=["GET"])
def list_sources():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name_filter = request.args.get("name", "").strip()
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)

    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM sources WHERE user_id = ?"
    params = [user_id]
    if name_filter:
        query += " AND name LIKE ?"
        params.append(f"%{name_filter}%")
    if min_amount is not None:
        query += " AND amount >= ?"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND amount <= ?"
        params.append(max_amount)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/sources", methods=["POST"])
def create_source():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_source_payload(data)
        print(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO sources (user_id, name, amount) VALUES (?, ?, ?)
            """,
            (user_id, payload["name"], payload["amount"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": new_id, **payload}), 201


@app.route("/sources/<int:source_id>", methods=["GET"])
def get_source(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sources WHERE id = ? AND user_id = ?", (source_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Source not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/sources/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_source_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM sources WHERE id = ? AND user_id = ?", (source_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404
    try:
        cursor.execute(
            "UPDATE sources SET name = ?, amount = ? WHERE id = ? AND user_id = ?",
            (payload["name"], payload["amount"], source_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": source_id, **payload})


@app.route("/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM sources WHERE id = ? AND user_id = ?", (source_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404
    cursor.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Source deleted"})


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.route("/transactions", methods=["GET"])
def list_transactions():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    category_id = request.args.get("category_id", type=int)
    source_id = request.args.get("source_id", type=int)
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)
    description = request.args.get("description", "").strip()

    conn = get_connection()
    cursor = conn.cursor()
    query = (
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE t.user_id = ?"
    )
    params = [user_id]
    if category_id is not None:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if source_id is not None:
        query += " AND t.source_id = ?"
        params.append(source_id)
    if date_from:
        query += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND t.date <= ?"
        params.append(date_to)
    if min_amount is not None:
        query += " AND t.amount >= ?"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND t.amount <= ?"
        params.append(max_amount)
    if description:
        query += " AND t.description LIKE ?"
        params.append(f"%{description}%")
    query += " ORDER BY t.date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = row_to_dict(r)
        d["date"] = gregorian_to_jalali(d["date"])
        results.append(d)
    return jsonify(results)


def _get_category_type(cursor, category_id, user_id):
    """Return 'income', 'cost', or None if category not found."""
    cursor.execute(
        "SELECT type FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    return row["type"] if row else None


def _get_source_amount(cursor, source_id, user_id):
    """Return current source amount or None if source not found."""
    cursor.execute(
        "SELECT amount FROM sources WHERE id = ? AND user_id = ?",
        (source_id, user_id),
    )
    row = cursor.fetchone()
    return row["amount"] if row else None


def _adjust_source_amount(cursor, source_id, user_id, amount, category_type):
    """Increment source for income, decrement for cost."""
    if source_id is None or category_type not in ("income", "cost"):
        return
    delta = amount if category_type == "income" else -amount
    cursor.execute(
        "UPDATE sources SET amount = amount + ? WHERE id = ? AND user_id = ?",
        (delta, source_id, user_id),
    )


@app.route("/transactions", methods=["POST"])
def create_transaction():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cat_type = _get_category_type(cursor, payload["category_id"], user_id)
    if cat_type is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    # Check sufficient balance for cost transactions
    source_id = payload.get("source_id")
    if cat_type == "cost" and source_id is not None:
        current = _get_source_amount(cursor, source_id, user_id)
        if current is None:
            conn.close()
            return jsonify({"error": "Source not found"}), 404
        if current < payload["amount"]:
            conn.close()
            return (
                jsonify(
                    {
                        "error": "Insufficient source balance",
                        "source_amount": current,
                        "requested": payload["amount"],
                    }
                ),
                400,
            )

    cursor.execute(
        """
        INSERT INTO transactions (user_id, date, amount, category_id, source_id, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            payload["date"],
            payload["amount"],
            payload["category_id"],
            source_id,
            payload["description"],
        ),
    )
    _adjust_source_amount(cursor, source_id, user_id, payload["amount"], cat_type)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return (
        jsonify(
            {
                "id": new_id,
                **payload,
                "date": gregorian_to_jalali(payload["date"]),
            }
        ),
        201,
    )


@app.route("/transactions/<int:tx_id>", methods=["GET"])
def get_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE t.id = ? AND t.user_id = ?",
        (tx_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Transaction not found"}), 404
    d = row_to_dict(row)
    d["date"] = gregorian_to_jalali(d["date"])
    return jsonify(d)


@app.route("/transactions/<int:tx_id>", methods=["PUT"])
def update_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, category_id, source_id FROM transactions WHERE id = ? AND user_id = ?",
        (tx_id, user_id),
    )
    old = cursor.fetchone()
    if old is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404

    # Reverse old effect
    old_type = _get_category_type(cursor, old["category_id"], user_id)
    if old_type:
        _adjust_source_amount(
            cursor, old["source_id"], user_id, old["amount"], "cost" if old_type == "income" else "income"
        )

    # Apply new effect
    new_type = _get_category_type(cursor, payload["category_id"], user_id)
    if new_type is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    # Check sufficient balance for cost transactions
    new_source_id = payload.get("source_id")
    if new_type == "cost" and new_source_id is not None:
        current = _get_source_amount(cursor, new_source_id, user_id)
        if current is None:
            conn.close()
            return jsonify({"error": "Source not found"}), 404
        # Account for the reversed old effect if same source
        effective = current
        if old["source_id"] == new_source_id and old_type:
            effective += old["amount"] if old_type == "cost" else -old["amount"]
        if effective < payload["amount"]:
            conn.close()
            return (
                jsonify(
                    {
                        "error": "Insufficient source balance",
                        "source_amount": effective,
                        "requested": payload["amount"],
                    }
                ),
                400,
            )

    cursor.execute(
        """
        UPDATE transactions
        SET date = ?, amount = ?, category_id = ?, source_id = ?, description = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            payload["date"],
            payload["amount"],
            payload["category_id"],
            new_source_id,
            payload["description"],
            tx_id,
            user_id,
        ),
    )
    _adjust_source_amount(cursor, new_source_id, user_id, payload["amount"], new_type)
    conn.commit()
    conn.close()
    return jsonify(
        {"id": tx_id, **payload, "date": gregorian_to_jalali(payload["date"])}
    )


@app.route("/transactions/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, category_id, source_id FROM transactions WHERE id = ? AND user_id = ?",
        (tx_id, user_id),
    )
    old = cursor.fetchone()
    if old is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404

    # Reverse the effect on source
    old_type = _get_category_type(cursor, old["category_id"], user_id)
    if old_type:
        _adjust_source_amount(
            cursor, old["source_id"], user_id, old["amount"], "cost" if old_type == "income" else "income"
        )

    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Transaction deleted"})


@app.route("/transactions/summary", methods=["GET"])
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
        WHERE t.user_id = ?
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    total_income = row["total_income"] or 0
    total_cost = row["total_cost"] or 0
    return jsonify(
        {
            "total_income": total_income,
            "total_cost": total_cost,
            "balance": total_income - total_cost,
        }
    )


@app.route("/transactions/report/category", methods=["GET"])
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
        LEFT JOIN transactions t ON c.id = t.category_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/transactions/report/monthly", methods=["GET"])
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
        WHERE t.user_id = ?
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


@app.route("/transactions/report/category-chart", methods=["GET"])
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
        LEFT JOIN transactions t ON c.id = t.category_id
        WHERE c.user_id = ?
        GROUP BY c.id
        HAVING total > 0
        ORDER BY total DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/sources/<int:source_id>/balance", methods=["GET"])
def source_balance(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM sources WHERE id = ? AND user_id = ?", (source_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.source_id = ? AND t.user_id = ?
        """,
        (source_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    total_income = row["total_income"] or 0
    total_cost = row["total_cost"] or 0
    return jsonify(
        {
            "source_id": source_id,
            "total_income": total_income,
            "total_cost": total_cost,
            "balance": total_income - total_cost,
        }
    )


@app.route("/settings/reset", methods=["POST"])


# ---------------------------------------------------------------------------
# Budget Periods
# ---------------------------------------------------------------------------

def _get_budget_period(cursor, period_id, user_id):
    cursor.execute(
        "SELECT * FROM budget_periods WHERE id = ? AND user_id = ?",
        (period_id, user_id),
    )
    return cursor.fetchone()


def _get_budget_item(cursor, item_id, user_id):
    cursor.execute(
        "SELECT bi.*, bp.user_id FROM budget_items bi "
        "JOIN budget_periods bp ON bi.budget_period_id = bp.id "
        "WHERE bi.id = ? AND bp.user_id = ?",
        (item_id, user_id),
    )
    return cursor.fetchone()


@app.route("/budget/periods", methods=["POST"])
def create_budget_period():
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
    try:
        cursor.execute(
            "INSERT INTO budget_periods (user_id, year, month) VALUES (?, ?, ?)",
            (user_id, payload["year"], payload["month"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Budget period already exists for this year/month"}), 400
    conn.close()
    return jsonify({"id": new_id, "year": payload["year"], "month": payload["month"]}), 

@app.route("/budget/periods/with-items", methods=["GET"])
def list_budget_periods_with_items():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    year_filter = request.args.get("year", type=int)
    month_filter = request.args.get("month", type=int)

    conn = get_connection()
    cursor = conn.cursor()
    
    # Single query to get all periods with item counts and aggregated data
    query = """
        SELECT 
            bp.id,
            bp.year,
            bp.month,
            bp.created_at,
            COALESCE(bi.item_count, 0) as item_count,
            COALESCE(bi.total_planned, 0) as total_planned
        FROM budget_periods bp
        LEFT JOIN (
            SELECT 
                budget_period_id, 
                COUNT(*) as item_count,
                SUM(planned_amount) as total_planned
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
    periods = cursor.fetchall()
    
    # Get all items for all periods in one query
    period_ids = [p["id"] for p in periods]
    items_by_period = {}
    
    if period_ids:
        # SQLite supports this, but for many IDs you might chunk this
        placeholders = ",".join("?" * len(period_ids))
        cursor.execute(f"""
            SELECT 
                bi.id,
                bi.budget_period_id,
                bi.planned_amount,
                bi.notes,
                c.name as category_name
            FROM budget_items bi
            JOIN categories c ON bi.category_id = c.id
            WHERE bi.budget_period_id IN ({placeholders})
            ORDER BY bi.budget_period_id, c.name
        """, period_ids)
        
        for item in cursor.fetchall():
            pid = item["budget_period_id"]
            if pid not in items_by_period:
                items_by_period[pid] = []
            items_by_period[pid].append(dict(item))
    
    conn.close()
    
    # Build response
    result = []
    for period in periods:
        period_dict = {
            "id": period["id"],
            "year": period["year"],
            "month": period["month"],
            "created_at": period["created_at"],
            "item_count": period["item_count"],
            "total_planned": period["total_planned"],
            "items": items_by_period.get(period["id"], [])
        }
        result.append(period_dict)
    
    return jsonify(result)


@app.route("/budget/periods/<int:period_id>", methods=["GET"])
def get_budget_period(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    row = _get_budget_period(cursor, period_id, user_id)
    conn.close()
    if row is None:
        return jsonify({"error": "Budget period not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/budget/periods", methods=["GET"])
def list_budget_periods():
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


@app.route("/budget/periods/<int:period_id>", methods=["PUT"])
def update_budget_period(period_id):
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
    if _get_budget_period(cursor, period_id, user_id) is None:
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


@app.route("/budget/periods/<int:period_id>", methods=["DELETE"])
def delete_budget_period(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    if _get_budget_period(cursor, period_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget period not found"}), 404
    cursor.execute("DELETE FROM budget_periods WHERE id = ?", (period_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Budget period deleted"})


# ---------------------------------------------------------------------------
# Budget Items
# ---------------------------------------------------------------------------

@app.route("/budget/items", methods=["POST"])
def create_budget_item():
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
    if _get_budget_period(cursor, period_id, user_id) is None:
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


@app.route("/budget/items/<int:item_id>", methods=["GET"])
def get_budget_item(item_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    row = _get_budget_item(cursor, item_id, user_id)
    conn.close()
    if row is None:
        return jsonify({"error": "Budget item not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/budget/periods/<int:period_id>/items", methods=["GET"])
def list_budget_items(period_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    if _get_budget_period(cursor, period_id, user_id) is None:
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


@app.route("/budget/items/<int:item_id>", methods=["PUT"])
def update_budget_item(item_id):
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
    row = _get_budget_item(cursor, item_id, user_id)
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


@app.route("/budget/items/<int:item_id>", methods=["DELETE"])
def delete_budget_item(item_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    if _get_budget_item(cursor, item_id, user_id) is None:
        conn.close()
        return jsonify({"error": "Budget item not found"}), 404
    cursor.execute("DELETE FROM budget_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Budget item deleted"})


# ---------------------------------------------------------------------------
# Budget Report
# ---------------------------------------------------------------------------

@app.route("/budget/report", methods=["GET"])
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
        "SELECT * FROM budget_periods WHERE user_id = ? AND year = ? AND month = ?",
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
        "WHERE bi.budget_period_id = ?",
        (period_id,),
    )
    items = cursor.fetchall()

    # For each category, get total spent in that month
    # We need to match Jalali month/year to Gregorian date ranges
    import jdatetime as _jd
    try:
        first_day = _jd.date(year, month, 1)
        last_day_num = _jd.date(year, month % 12 + 1, 1).togregorian() - __import__("datetime").timedelta(days=1) if month < 12 else _jd.date(year + 1, 1, 1).togregorian() - __import__("datetime").timedelta(days=1)
        greg_start = first_day.togregorian().strftime("%Y-%m-%d")
        greg_end = last_day_num.strftime("%Y-%m-%d")
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
            "WHERE user_id = ? AND category_id = ? AND date >= ? AND date <= ?",
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


@app.route("/settings/reset", methods=["POST"])
def reset_all_data():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM sources WHERE user_id = ?", (user_id,))
    # cursor.execute("UPDATE sources SET amount = 0 WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "All data reset successfully"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
