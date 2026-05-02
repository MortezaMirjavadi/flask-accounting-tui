import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import (
    get_user_id_from_request,
    row_to_dict,
    gregorian_to_jalali,
    jalali_to_gregorian,
)
from app.models import validate_transaction_payload
from database import get_connection, release_connection

bp = Blueprint('transactions', __name__)


def _get_category_type(cursor, category_id, user_id):
    cursor.execute(
        "SELECT type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    return row["type"] if row else None


def _get_source_amount(cursor, source_id, user_id):
    cursor.execute(
        "SELECT amount FROM sources WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (source_id, user_id),
    )
    row = cursor.fetchone()
    return row["amount"] if row else None


def _source_exists(cursor, source_id, user_id):
    cursor.execute(
        "SELECT 1 FROM sources WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (source_id, user_id),
    )
    return cursor.fetchone() is not None


def _adjust_source_amount(cursor, source_id, user_id, amount, category_type):
    if source_id is None or category_type not in ("income", "cost"):
        return
    delta = amount if category_type == "income" else -amount
    cursor.execute(
        "UPDATE sources SET amount = amount + %s WHERE id = %s AND user_id = %s",
        (delta, source_id, user_id),
    )


def _validate_transfer_payload(data):
    date = (data.get("date") or "").strip()
    notes = (data.get("description") or data.get("notes") or "").strip() or None

    if not date:
        raise ValueError("Date is required")

    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid positive amount is required")

    try:
        from_source_id = int(data.get("from_source_id"))
    except (TypeError, ValueError):
        raise ValueError("Valid from_source_id is required")

    try:
        to_source_id = int(data.get("to_source_id"))
    except (TypeError, ValueError):
        raise ValueError("Valid to_source_id is required")

    if from_source_id == to_source_id:
        raise ValueError("from_source_id and to_source_id must be different")

    return {
        "date": jalali_to_gregorian(date),
        "amount": amount,
        "from_source_id": from_source_id,
        "to_source_id": to_source_id,
        "notes": notes,
    }


def _serialize_transaction(payload, tx_id):
    return {
        "id": tx_id,
        "record_type": "transaction",
        "is_transfer": False,
        **payload,
        "date": gregorian_to_jalali(payload["date"]),
    }


def _serialize_transfer(payload, tx_id):
    return {
        "id": tx_id,
        "record_type": "transfer",
        "is_transfer": True,
        **payload,
        "description": payload.get("notes"),
        "date": gregorian_to_jalali(payload["date"]),
    }


def _format_transfer_list_row(row):
    data = row_to_dict(row)
    from_name = data.get("from_source_name") or "Unknown"
    to_name = data.get("to_source_name") or "Unknown"
    data["record_type"] = "transfer"
    data["is_transfer"] = True
    data["category_name"] = "Transfer"
    data["source_name"] = f"{from_name} -> {to_name}"
    data["description"] = data.get("notes") or "Transfer between sources"
    data["date"] = gregorian_to_jalali(data["date"])
    return data


def _get_transaction_row(cursor, tx_id, user_id):
    cursor.execute(
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE t.id = %s AND t.user_id = %s AND t.deleted_at IS NULL",
        (tx_id, user_id),
    )
    return cursor.fetchone()


def _get_transfer_row(cursor, tx_id, user_id):
    cursor.execute(
        "SELECT t.*, fs.name as from_source_name, ts.name as to_source_name "
        "FROM transfers t "
        "LEFT JOIN sources fs ON t.from_source_id = fs.id "
        "LEFT JOIN sources ts ON t.to_source_id = ts.id "
        "WHERE t.id = %s AND t.user_id = %s AND t.deleted_at IS NULL",
        (tx_id, user_id),
    )
    return cursor.fetchone()


def _validate_transaction_business_rules(cursor, user_id, payload, old_transaction=None, old_transfer=None):
    new_type = _get_category_type(cursor, payload["category_id"], user_id)
    if new_type is None:
        return jsonify({"error": "Category not found"}), None

    new_source_id = payload.get("source_id")
    if new_source_id is not None and not _source_exists(cursor, new_source_id, user_id):
        return jsonify({"error": "Source not found"}), None

    if new_type == "cost" and new_source_id is not None:
        current = _get_source_amount(cursor, new_source_id, user_id)
        if current is None:
            return jsonify({"error": "Source not found"}), None

        effective = current
        if old_transaction is not None:
            old_type = _get_category_type(cursor, old_transaction["category_id"], user_id)
            if old_transaction["source_id"] == new_source_id and old_type:
                effective += old_transaction["amount"] if old_type == "cost" else -old_transaction["amount"]
        if old_transfer is not None:
            if old_transfer["from_source_id"] == new_source_id:
                effective += old_transfer["amount"]
            if old_transfer["to_source_id"] == new_source_id:
                effective -= old_transfer["amount"]

        if effective < payload["amount"]:
            return (
                jsonify(
                    {
                        "error": "Insufficient source balance",
                        "source_amount": effective,
                        "requested": payload["amount"],
                    }
                ),
                None,
            )

    return None, new_type


def _validate_transfer_business_rules(cursor, user_id, payload, old_transaction=None, old_transfer=None):
    from_source_id = payload["from_source_id"]
    to_source_id = payload["to_source_id"]

    if not _source_exists(cursor, from_source_id, user_id):
        return jsonify({"error": "From source not found"})
    if not _source_exists(cursor, to_source_id, user_id):
        return jsonify({"error": "To source not found"})

    current = _get_source_amount(cursor, from_source_id, user_id)
    if current is None:
        return jsonify({"error": "From source not found"})

    effective = current
    if old_transaction is not None:
        old_type = _get_category_type(cursor, old_transaction["category_id"], user_id)
        if old_transaction["source_id"] == from_source_id and old_type:
            effective += old_transaction["amount"] if old_type == "cost" else -old_transaction["amount"]
    if old_transfer is not None:
        if old_transfer["from_source_id"] == from_source_id:
            effective += old_transfer["amount"]
        if old_transfer["to_source_id"] == from_source_id:
            effective -= old_transfer["amount"]

    if effective < payload["amount"]:
        return jsonify(
            {
                "error": "Insufficient source balance",
                "source_amount": effective,
                "requested": payload["amount"],
            }
        )

    return None


def _reverse_transaction_effect(cursor, transaction_row, user_id):
    old_type = _get_category_type(cursor, transaction_row["category_id"], user_id)
    if old_type:
        _adjust_source_amount(
            cursor,
            transaction_row["source_id"],
            user_id,
            transaction_row["amount"],
            "cost" if old_type == "income" else "income",
        )


def _apply_transfer_effect(cursor, transfer_row, user_id):
    cursor.execute(
        "UPDATE sources SET amount = amount - %s WHERE id = %s AND user_id = %s",
        (transfer_row["amount"], transfer_row["from_source_id"], user_id),
    )
    cursor.execute(
        "UPDATE sources SET amount = amount + %s WHERE id = %s AND user_id = %s",
        (transfer_row["amount"], transfer_row["to_source_id"], user_id),
    )


def _reverse_transfer_effect(cursor, transfer_row, user_id):
    cursor.execute(
        "UPDATE sources SET amount = amount + %s WHERE id = %s AND user_id = %s",
        (transfer_row["amount"], transfer_row["from_source_id"], user_id),
    )
    cursor.execute(
        "UPDATE sources SET amount = amount - %s WHERE id = %s AND user_id = %s",
        (transfer_row["amount"], transfer_row["to_source_id"], user_id),
    )


def _error_status(response):
    payload = response.get_json(silent=True) or {}
    error = (payload.get("error") or "").lower()
    return 404 if "not found" in error else 400


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
    category_type = request.args.get("category_type", "").strip().lower()
    include_transfers = request.args.get("include_transfers", "").strip().lower() in ("1", "true", "yes")

    conn = get_connection()
    cursor = conn.cursor()
    
    query = (
        "SELECT t.*, c.name as category_name, s.name as source_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN sources s ON t.source_id = s.id "
        "WHERE t.user_id = %s AND t.deleted_at IS NULL"
    )
    params = [user_id]
    
    if category_type == "transfer":
        query += " AND 1 = 0"
    if category_id is not None:
        query += " AND t.category_id = %s"
        params.append(category_id)
    if category_type in ("income", "cost"):
        query += " AND c.type = %s"
        params.append(category_type)
    if source_id is not None:
        query += " AND t.source_id = %s"
        params.append(source_id)
    if date_from:
        query += " AND t.date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND t.date <= %s"
        params.append(date_to)
    if min_amount is not None:
        query += " AND t.amount >= %s"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND t.amount <= %s"
        params.append(max_amount)
    if description:
        query += " AND t.description LIKE %s"
        params.append(f"%{description}%")
    
    query += " ORDER BY t.date DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for r in rows:
        d = row_to_dict(r)
        d["record_type"] = "transaction"
        d["is_transfer"] = False
        d["date"] = gregorian_to_jalali(d["date"])
        results.append(d)

    if include_transfers and category_id is None and category_type in ("", "transfer"):
        transfer_query = (
            "SELECT t.*, fs.name as from_source_name, ts.name as to_source_name "
            "FROM transfers t "
            "LEFT JOIN sources fs ON t.from_source_id = fs.id "
            "LEFT JOIN sources ts ON t.to_source_id = ts.id "
            "WHERE t.user_id = %s AND t.deleted_at IS NULL"
        )
        transfer_params = [user_id]

        if source_id is not None:
            transfer_query += " AND (t.from_source_id = %s OR t.to_source_id = %s)"
            transfer_params.extend([source_id, source_id])
        if date_from:
            transfer_query += " AND t.date >= %s"
            transfer_params.append(date_from)
        if date_to:
            transfer_query += " AND t.date <= %s"
            transfer_params.append(date_to)
        if min_amount is not None:
            transfer_query += " AND t.amount >= %s"
            transfer_params.append(min_amount)
        if max_amount is not None:
            transfer_query += " AND t.amount <= %s"
            transfer_params.append(max_amount)
        if description:
            transfer_query += " AND t.notes LIKE %s"
            transfer_params.append(f"%{description}%")

        cursor.execute(transfer_query, transfer_params)
        transfer_rows = cursor.fetchall()
        results.extend(_format_transfer_list_row(row) for row in transfer_rows)

    cursor.close()
    release_connection(conn)
    results.sort(key=lambda item: item.get("date", ""), reverse=True)
    
    return jsonify(results)


@bp.route("", methods=["POST"])
def create_transaction():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    data = request.get_json(force=True, silent=True) or {}
    is_transfer = bool(data.get("is_transfer"))

    if is_transfer:
        try:
            payload = _validate_transfer_payload(data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        conn = get_connection()
        cursor = conn.cursor()
        err_response = _validate_transfer_business_rules(cursor, user_id, payload)
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code
        try:
            cursor.execute(
                """
                INSERT INTO transfers (user_id, from_source_id, to_source_id, amount, date, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    payload["from_source_id"],
                    payload["to_source_id"],
                    payload["amount"],
                    payload["date"],
                    payload["notes"],
                ),
            )
            new_row = cursor.fetchone()
            if new_row is None:
                conn.rollback()
                cursor.close()
                release_connection(conn)
                return jsonify({"error": "Insert did not return id"}), 500
            new_id = new_row["id"]
            _apply_transfer_effect(cursor, payload, user_id)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400
        else:
            cursor.close()
            release_connection(conn)
            return jsonify(_serialize_transfer(payload, new_id)), 201

    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()

    err_response, cat_type = _validate_transaction_business_rules(cursor, user_id, payload)
    if err_response:
        status_code = _error_status(err_response)
        cursor.close()
        release_connection(conn)
        return err_response, status_code

    source_id = payload.get("source_id")
    cursor.execute(
        """
        INSERT INTO transactions (user_id, date, amount, category_id, source_id, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
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
    new_row = cursor.fetchone()
    if new_row is None:
        cursor.close()
        release_connection(conn)
        raise RuntimeError("Insert did not return id")
    new_id = new_row['id']
    _adjust_source_amount(cursor, source_id, user_id, payload["amount"], cat_type)
    conn.commit()
    cursor.close()
    release_connection(conn)

    return jsonify(_serialize_transaction(payload, new_id)), 201


@bp.route("/<int:tx_id>", methods=["GET"])
def get_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    record_type = request.args.get("record_type", "").strip().lower()
    row = None
    if record_type != "transfer":
        row = _get_transaction_row(cursor, tx_id, user_id)
        if row is not None:
            record_type = "transaction"
    if row is None:
        row = _get_transfer_row(cursor, tx_id, user_id)
        record_type = "transfer"
    cursor.close()
    release_connection(conn)
    if row is None:
        return jsonify({"error": "Transaction not found"}), 404
    d = row_to_dict(row)
    d["date"] = gregorian_to_jalali(d["date"])
    if record_type == "transfer":
        d["is_transfer"] = True
        d["description"] = d.get("notes")
    else:
        d["is_transfer"] = False
    return jsonify(d)


@bp.route("/<int:tx_id>", methods=["PUT"])
def update_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    is_transfer = bool(data.get("is_transfer"))
    original_is_transfer = bool(data.get("original_is_transfer"))
    record_type = request.args.get("record_type", "").strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    if original_is_transfer or record_type == "transfer":
        old_transfer = _get_transfer_row(cursor, tx_id, user_id)
        if old_transfer is None:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "Transfer not found"}), 404

        if is_transfer:
            try:
                payload = _validate_transfer_payload(data)
            except ValueError as exc:
                cursor.close()
                release_connection(conn)
                return jsonify({"error": str(exc)}), 400

            err_response = _validate_transfer_business_rules(cursor, user_id, payload, old_transfer=old_transfer)
            if err_response:
                status_code = _error_status(err_response)
                cursor.close()
                release_connection(conn)
                return err_response, status_code

            _reverse_transfer_effect(cursor, old_transfer, user_id)
            cursor.execute(
                """
                UPDATE transfers
                SET from_source_id = %s, to_source_id = %s, amount = %s, date = %s, notes = %s
                WHERE id = %s AND user_id = %s
                """,
                (
                    payload["from_source_id"],
                    payload["to_source_id"],
                    payload["amount"],
                    payload["date"],
                    payload["notes"],
                    tx_id,
                    user_id,
                ),
            )
            _apply_transfer_effect(cursor, payload, user_id)
            conn.commit()
            cursor.close()
            release_connection(conn)
            return jsonify(_serialize_transfer(payload, tx_id))

        try:
            payload = validate_transaction_payload(data)
        except ValueError as exc:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400

        err_response, new_type = _validate_transaction_business_rules(
            cursor, user_id, payload, old_transfer=old_transfer
        )
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code

        _reverse_transfer_effect(cursor, old_transfer, user_id)
        cursor.execute(
            "UPDATE transfers SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (tx_id, user_id),
        )
        cursor.execute(
            """
            INSERT INTO transactions (user_id, date, amount, category_id, source_id, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
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
        new_id = cursor.fetchone()['id']
        _adjust_source_amount(cursor, payload.get("source_id"), user_id, payload["amount"], new_type)
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify(_serialize_transaction(payload, new_id))

    old_transaction = _get_transaction_row(cursor, tx_id, user_id)
    if old_transaction is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "Transaction not found"}), 404

    if is_transfer:
        try:
            payload = _validate_transfer_payload(data)
        except ValueError as exc:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400

        err_response = _validate_transfer_business_rules(cursor, user_id, payload, old_transaction=old_transaction)
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code

        _reverse_transaction_effect(cursor, old_transaction, user_id)
        cursor.execute(
            "UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (tx_id, user_id),
        )
        cursor.execute(
            """
            INSERT INTO transfers (user_id, from_source_id, to_source_id, amount, date, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                payload["from_source_id"],
                payload["to_source_id"],
                payload["amount"],
                payload["date"],
                payload["notes"],
            ),
        )
        new_id = cursor.fetchone()['id']
        _apply_transfer_effect(cursor, payload, user_id)
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify(_serialize_transfer(payload, new_id))

    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": str(exc)}), 400

    err_response, new_type = _validate_transaction_business_rules(
        cursor, user_id, payload, old_transaction=old_transaction
    )
    if err_response:
        status_code = _error_status(err_response)
        cursor.close()
        release_connection(conn)
        return err_response, status_code

    _reverse_transaction_effect(cursor, old_transaction, user_id)
    cursor.execute(
        """
        UPDATE transactions
        SET date = %s, amount = %s, category_id = %s, source_id = %s, description = %s
        WHERE id = %s AND user_id = %s
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
    _adjust_source_amount(cursor, payload.get("source_id"), user_id, payload["amount"], new_type)
    conn.commit()
    cursor.close()
    release_connection(conn)
    return jsonify(_serialize_transaction(payload, tx_id))


@bp.route("/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    record_type = request.args.get("record_type", "").strip().lower()
    old = None if record_type == "transfer" else _get_transaction_row(cursor, tx_id, user_id)
    if old is not None:
        _reverse_transaction_effect(cursor, old, user_id)
        cursor.execute(
            "UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (tx_id, user_id),
        )
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify({"message": "Transaction archived"})

    old_transfer = _get_transfer_row(cursor, tx_id, user_id)
    if old_transfer is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "Transaction not found"}), 404

    _reverse_transfer_effect(cursor, old_transfer, user_id)
    cursor.execute(
        "UPDATE transfers SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (tx_id, user_id),
    )
    conn.commit()
    cursor.close()
    release_connection(conn)
    return jsonify({"message": "Transaction archived"})
