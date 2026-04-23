from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict, gregorian_to_jalali
from app.models import validate_transaction_payload
from database import get_connection

bp = Blueprint('transactions', __name__)


def _get_category_type(cursor, category_id, user_id):
    cursor.execute(
        "SELECT type FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    return row["type"] if row else None


def _get_source_amount(cursor, source_id, user_id):
    cursor.execute(
        "SELECT amount FROM sources WHERE id = ? AND user_id = ?",
        (source_id, user_id),
    )
    row = cursor.fetchone()
    return row["amount"] if row else None


def _adjust_source_amount(cursor, source_id, user_id, amount, category_type):
    if source_id is None or category_type not in ("income", "cost"):
        return
    delta = amount if category_type == "income" else -amount
    cursor.execute(
        "UPDATE sources SET amount = amount + ? WHERE id = ? AND user_id = ?",
        (delta, source_id, user_id),
    )


@bp.route("", methods=["GET"])
def list_transactions():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    # ... filters ...
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


@bp.route("", methods=["POST"])
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
            return jsonify({
                "error": "Insufficient source balance",
                "source_amount": current,
                "requested": payload["amount"],
            }), 400

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

    return jsonify({
        "id": new_id,
        **payload,
        "date": gregorian_to_jalali(payload["date"]),
    }), 201


@bp.route("/<int:tx_id>", methods=["GET"])
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


@bp.route("/<int:tx_id>", methods=["PUT"])
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


@bp.route("/<int:tx_id>", methods=["DELETE"])
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
