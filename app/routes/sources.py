import sqlite3
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict, gregorian_to_jalali
from app.models import validate_source_payload
from database import get_connection

bp = Blueprint('sources', __name__)


@bp.route("", methods=["GET"])
def list_sources():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    name_filter = request.args.get("name", "").strip()
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)

    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM sources WHERE user_id = ? AND deleted_at IS NULL"
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


@bp.route("", methods=["POST"])
def create_source():
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
    
    try:
        cursor.execute(
            "INSERT INTO sources (user_id, name, amount) VALUES (?, ?, ?)",
            (user_id, payload["name"], payload["amount"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        cursor.execute(
            "SELECT id FROM sources WHERE user_id = ? AND name = ? AND deleted_at IS NOT NULL",
            (user_id, payload["name"]),
        )
        archived = cursor.fetchone()
        if archived is None:
            conn.close()
            return jsonify({"error": str(exc)}), 400
        cursor.execute(
            "UPDATE sources SET amount = ?, deleted_at = NULL WHERE id = ?",
            (payload["amount"], archived["id"]),
        )
        conn.commit()
        new_id = archived["id"]
    
    conn.close()
    return jsonify({"id": new_id, **payload}), 201


@bp.route("/<int:source_id>", methods=["GET"])
def get_source(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sources WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return jsonify({"error": "Source not found"}), 404
    
    return jsonify(row_to_dict(row))


@bp.route("/<int:source_id>", methods=["PUT"])
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
        "SELECT id FROM sources WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id)
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


@bp.route("/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM sources WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404
    
    cursor.execute(
        "UPDATE sources SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id),
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Source archived"})


@bp.route("/<int:source_id>/balance", methods=["GET"])
def source_balance(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM sources WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id)
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
        WHERE t.source_id = ? AND t.user_id = ? AND t.deleted_at IS NULL
        """,
        (source_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    
    total_income = row["total_income"] or 0
    total_cost = row["total_cost"] or 0
    
    return jsonify({
        "source_id": source_id,
        "total_income": total_income,
        "total_cost": total_cost,
        "balance": total_income - total_cost,
    })


@bp.route("/<int:source_id>/transfers", methods=["GET"])
def source_transfers(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name FROM sources WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (source_id, user_id),
    )
    source = cursor.fetchone()
    if source is None:
        conn.close()
        return jsonify({"error": "Source not found"}), 404

    cursor.execute(
        """
        SELECT
            t.id,
            t.date,
            t.amount,
            t.notes,
            t.from_source_id,
            t.to_source_id,
            fs.name AS from_source_name,
            ts.name AS to_source_name,
            CASE
                WHEN t.to_source_id = ? THEN 'in'
                ELSE 'out'
            END AS direction
        FROM transfers t
        LEFT JOIN sources fs ON t.from_source_id = fs.id
        LEFT JOIN sources ts ON t.to_source_id = ts.id
        WHERE t.user_id = ?
          AND t.deleted_at IS NULL
          AND (t.from_source_id = ? OR t.to_source_id = ?)
        ORDER BY t.date DESC, t.id DESC
        """,
        (source_id, user_id, source_id, source_id),
    )
    rows = cursor.fetchall()
    conn.close()

    records = []
    total_in = 0
    total_out = 0
    for row in rows:
        record = row_to_dict(row)
        record["date"] = gregorian_to_jalali(record["date"])
        if record.get("direction") == "in":
            total_in += record.get("amount", 0) or 0
        else:
            total_out += record.get("amount", 0) or 0
        records.append(record)

    return jsonify(
        {
            "source_id": source_id,
            "source_name": source["name"],
            "summary": {
                "total_transfer_in": total_in,
                "total_transfer_out": total_out,
                "net_transfer": total_in - total_out,
            },
            "records": records,
        }
    )
