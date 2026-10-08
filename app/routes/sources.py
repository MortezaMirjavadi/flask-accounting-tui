"""Legacy sources route — redirects to wallet-based account model.

Wallets no longer have amount/bank_type. All balance data lives on accounts.
This module provides backward-compatible read-only access where possible.
"""

import math
import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict, gregorian_to_jalali
from app.models import validate_source_payload
from app.utils.pagination import parse_pagination, paginated_query
from database import get_connection, release_connection

bp = Blueprint('sources', __name__)


@bp.route("", methods=["GET"])
def list_sources():
    """List wallets (legacy endpoint) with pagination.
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
      - name: name
        in: query
        type: string
        description: Filter wallets by name (partial match)
    responses:
      200:
        description: Paginated list of wallets
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    name_filter = request.args.get("name", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        where_clause = " WHERE w.user_id = %s AND w.deleted_at IS NULL"
        params = [user_id]

        if name_filter:
            where_clause += " AND w.name LIKE %s"
            params.append(f"%{name_filter}%")

        join_clause = (
            " FROM wallets w"
            " LEFT JOIN ("
            "   SELECT wallet_id, COALESCE(SUM(amount), 0) AS balance"
            "   FROM accounts WHERE deleted_at IS NULL GROUP BY wallet_id"
            " ) a_total ON a_total.wallet_id = w.id"
            " LEFT JOIN accounts a_default ON a_default.wallet_id = w.id AND a_default.is_default = TRUE"
        )

        count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
        data_sql = (
            "SELECT w.*, COALESCE(a_total.balance, 0) AS amount,"
            " COALESCE(a_default.bank_type, 'cash') AS bank_type"
            + join_clause + where_clause + " ORDER BY w.id"
        )
        return paginated_query(cursor, count_sql, data_sql, params, row_to_dict, page, per_page)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
def create_source():
    """Create a wallet with a default account (legacy endpoint).
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            amount:
              type: number
              description: Initial balance amount
            currency:
              type: string
              default: IRR
            wallet_type:
              type: string
              default: personal
            bank_type:
              type: string
              default: cash
    responses:
      201:
        description: Wallet created
    """
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
            "INSERT INTO wallets (user_id, name, currency, wallet_type) VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, payload["name"], data.get("currency", "IRR"), data.get("wallet_type", "personal")),
        )
        new_id = cursor.fetchone()['id']

        cursor.execute(
            "INSERT INTO wallet_members (wallet_id, user_id, role) VALUES (%s, %s, 'owner')",
            (new_id, user_id)
        )

        # Create default account with the initial amount
        cursor.execute(
            """
            INSERT INTO accounts (wallet_id, name, account_type, bank_type, amount, is_default)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            """,
            (new_id, payload["name"], "cash", data.get("bank_type", "cash"), payload["amount"]),
        )

        conn.commit()
    except psycopg2.IntegrityError as exc:
        conn.rollback()
        cursor.execute(
            "SELECT id FROM wallets WHERE user_id = %s AND name = %s AND deleted_at IS NOT NULL",
            (user_id, payload["name"]),
        )
        archived = cursor.fetchone()
        if archived is None:
            return jsonify({"error": str(exc)}), 400
        # Restore wallet
        cursor.execute(
            "UPDATE wallets SET deleted_at = NULL WHERE id = %s",
            (archived["id"],),
        )
        # Update default account amount
        cursor.execute(
            """
            UPDATE accounts SET amount = %s, deleted_at = NULL
            WHERE wallet_id = %s AND is_default = TRUE
            """,
            (payload["amount"], archived["id"]),
        )
        conn.commit()
        new_id = archived["id"]
    finally:
        cursor.close()
        release_connection(conn)

    return jsonify({"id": new_id, **payload}), 201


@bp.route("/<int:source_id>", methods=["GET"])
def get_source(source_id):
    """Get wallet with account-derived amount/bank_type (legacy endpoint).
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Wallet details
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT w.*,
                   COALESCE(a_total.balance, 0) AS amount,
                   COALESCE(a_default.bank_type, 'cash') AS bank_type
            FROM wallets w
            LEFT JOIN (
                SELECT wallet_id, COALESCE(SUM(amount), 0) AS balance
                FROM accounts WHERE deleted_at IS NULL GROUP BY wallet_id
            ) a_total ON a_total.wallet_id = w.id
            LEFT JOIN accounts a_default ON a_default.wallet_id = w.id AND a_default.is_default = TRUE
            WHERE w.id = %s AND w.user_id = %s AND w.deleted_at IS NULL
            """,
            (source_id, user_id)
        )
        row = cursor.fetchone()

        if row is None:
            return jsonify({"error": "منبع یافت نشد"}), 404

        return jsonify(row_to_dict(row))
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    """Update wallet name and default account amount (legacy endpoint).
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            amount:
              type: number
            bank_type:
              type: string
    responses:
      200:
        description: Wallet updated
      404:
        description: Wallet not found
    """
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
            "SELECT id FROM wallets WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (source_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "منبع یافت نشد"}), 404

        cursor.execute(
            "UPDATE wallets SET name = %s WHERE id = %s AND user_id = %s",
            (payload["name"], source_id, user_id),
        )

        # Update default account
        cursor.execute(
            """
            UPDATE accounts SET amount = %s, bank_type = %s
            WHERE wallet_id = %s AND is_default = TRUE
            """,
            (payload["amount"], data.get("bank_type", "cash"), source_id),
        )

        conn.commit()
    except psycopg2.IntegrityError as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cursor.close()
        release_connection(conn)

    return jsonify({"id": source_id, **payload})


@bp.route("/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    """Soft-delete wallet.
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Wallet archived
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM wallets WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (source_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "منبع یافت نشد"}), 404

        cursor.execute(
            "UPDATE wallets SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (source_id, user_id),
        )
        conn.commit()

        return jsonify({"message": "Source archived"})
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:source_id>/balance", methods=["GET"])
def source_balance(source_id):
    """Get wallet balance from accounts (legacy endpoint).
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Wallet balance breakdown
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM wallets WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (source_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "منبع یافت نشد"}), 404

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.wallet_id = %s AND t.deleted_at IS NULL
            """,
            (source_id,),
        )
        row = cursor.fetchone()

        total_income = float(row["total_income"]) if row["total_income"] else 0
        total_cost = float(row["total_cost"]) if row["total_cost"] else 0

        return jsonify({
            "source_id": source_id,
            "total_income": total_income,
            "total_cost": total_cost,
            "balance": total_income - total_cost,
        })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:source_id>/transfers", methods=["GET"])
def source_transfers(source_id):
    """Get transfers involving this wallet (legacy endpoint) with pagination.
    ---
    tags:
      - Sources
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated list of wallet transfers with summary
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, name FROM wallets WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (source_id, user_id),
        )
        source = cursor.fetchone()
        if source is None:
            return jsonify({"error": "منبع یافت نشد"}), 404

        where_clause = (
            " WHERE t.user_id = %s AND t.deleted_at IS NULL"
            " AND (t.from_wallet_id = %s OR t.to_wallet_id = %s)"
        )
        params = [user_id, source_id, source_id]

        join_clause = (
            " FROM transfers t"
            " LEFT JOIN wallets fw ON t.from_wallet_id = fw.id"
            " LEFT JOIN wallets tw ON t.to_wallet_id = tw.id"
        )

        count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        data_sql = (
            "SELECT t.id, t.date, t.amount, t.notes,"
            " t.from_wallet_id, t.to_wallet_id,"
            " fw.name AS from_source_name, tw.name AS to_source_name,"
            " CASE WHEN t.to_wallet_id = %s THEN 'in' ELSE 'out' END AS direction"
            + join_clause + where_clause + " ORDER BY t.date DESC, t.id DESC"
            + " LIMIT %s OFFSET %s"
        )
        cursor.execute(data_sql, [source_id] + params + [per_page, offset])
        rows = cursor.fetchall()

        records = []
        total_in = 0
        total_out = 0
        for row in rows:
            record = row_to_dict(row)
            record["date"] = gregorian_to_jalali(record["date"])
            record["amount"] = float(record["amount"]) if record["amount"] else 0
            if record.get("direction") == "in":
                total_in += record.get("amount", 0) or 0
            else:
                total_out += record.get("amount", 0) or 0
            records.append(record)

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "source_id": source_id,
            "source_name": source["name"],
            "summary": {
                "total_transfer_in": total_in,
                "total_transfer_out": total_out,
                "net_transfer": total_in - total_out,
            },
            "items": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)
