import sqlite3
from flask import Flask, jsonify, request
from database import get_connection, init_db
from models import (
    validate_category_payload,
    validate_source_payload,
    validate_transaction_payload,
    gregorian_to_jalali,
)

app = Flask(__name__)


@app.before_request
def ensure_db():
    init_db()


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.route("/categories", methods=["GET"])
def list_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_category_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (name, type) VALUES (?, ?)",
            (payload["name"], payload["type"]),
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Category not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_category_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    try:
        cursor.execute(
            "UPDATE categories SET name = ?, type = ? WHERE id = ?",
            (payload["name"], payload["type"], cat_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": cat_id, **payload})


@app.route("/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sources")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/sources", methods=["POST"])
def create_source():
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
            INSERT INTO sources (name, amount) VALUES (?, ?)
            """,
            (payload["name"], payload["amount"]),
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Source not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/sources/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_source_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404
    try:
        cursor.execute(
            "UPDATE sources SET name = ? WHERE id = ?",
            (payload["name"], source_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    conn.close()
    return jsonify({"id": source_id, **payload})


@app.route("/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
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
    category_id = request.args.get("category_id", type=int)
    source_id = request.args.get("source_id", type=int)
    conn = get_connection()
    cursor = conn.cursor()
    query = (
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE 1=1"
    )
    params = []
    if category_id is not None:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if source_id is not None:
        query += " AND t.source_id = ?"
        params.append(source_id)
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
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transactions (date, amount, category_id, source_id, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE t.id = ?",
        (tx_id,),
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
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404
    cursor.execute(
        """
        UPDATE transactions
        SET date = ?, amount = ?, category_id = ?, source_id = ?, description = ?
        WHERE id = ?
        """,
        (
            payload["date"],
            payload["amount"],
            payload["category_id"],
            payload.get("source_id"),
            payload["description"],
            tx_id,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify(
        {"id": tx_id, **payload, "date": gregorian_to_jalali(payload["date"])}
    )


@app.route("/transactions/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404
    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Transaction deleted"})


@app.route("/transactions/summary", methods=["GET"])
def transactions_summary():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        """
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
        GROUP BY c.id
        ORDER BY total DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/transactions/report/monthly", methods=["GET"])
def report_by_month():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            strftime('%Y-%m', date) AS month,
            COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        GROUP BY month
        ORDER BY month
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/transactions/report/category-chart", methods=["GET"])
def report_category_chart():
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
        GROUP BY c.id
        HAVING total > 0
        ORDER BY total DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/sources/<int:source_id>/balance", methods=["GET"])
def source_balance(source_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
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
        WHERE t.source_id = ?
        """,
        (source_id,),
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
