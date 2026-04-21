import sqlite3
from flask import Flask, jsonify, request
from database import get_connection, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from models import (
    validate_category_payload,
    validate_source_payload,
    validate_transaction_payload,
    validate_user_payload,
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
            "UPDATE sources SET name = ? WHERE id = ? AND user_id = ?",
            (payload["name"], source_id, user_id),
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
            payload.get("source_id"),
            payload["description"],
        ),
    )
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
        "SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404
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
            payload.get("source_id"),
            payload["description"],
            tx_id,
            user_id,
        ),
    )
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
        "SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
