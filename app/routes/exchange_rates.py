"""Exchange rate routes - manual currency rate management."""

import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.utils.pagination import parse_pagination, paginated_query
from app.utils.currency import SUPPORTED_CURRENCIES
from database import get_connection, release_connection
from decimal import Decimal

bp = Blueprint('exchange_rates', __name__)


@bp.route("", methods=["GET"])
def list_rates():
    """List user's exchange rates with pagination.
    ---
    tags:
      - Exchange Rates
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
    responses:
      200:
        description: Paginated list of exchange rates
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        where_clause = " WHERE user_id = %s"
        params = [user_id]

        count_sql = "SELECT COUNT(*) as total FROM exchange_rates" + where_clause
        data_sql = (
            "SELECT * FROM exchange_rates" + where_clause
            + " ORDER BY from_currency, to_currency, effective_date DESC"
        )
        return paginated_query(cursor, count_sql, data_sql, params, row_to_dict, page, per_page)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
def create_rate():
    """Set an exchange rate. Also auto-creates the reverse rate.
    ---
    tags:
      - Exchange Rates
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
            - from_currency
            - to_currency
            - rate
          properties:
            from_currency:
              type: string
            to_currency:
              type: string
            rate:
              type: number
    responses:
      201:
        description: Exchange rate created (including reverse rate)
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    from_currency = data.get("from_currency", "").strip().upper()
    to_currency = data.get("to_currency", "").strip().upper()
    rate = data.get("rate")

    if not from_currency or not to_currency:
        return jsonify({"error": "ارز مبدأ و مقصد الزامی است"}), 400
    if from_currency not in SUPPORTED_CURRENCIES:
        return jsonify({"error": f"ارز '{from_currency}' پشتیبانی نمی‌شود"}), 400
    if to_currency not in SUPPORTED_CURRENCIES:
        return jsonify({"error": f"ارز '{to_currency}' پشتیبانی نمی‌شود"}), 400
    if from_currency == to_currency:
        return jsonify({"error": "ارز مبدأ و مقصد نمی‌تواند یکسان باشد"}), 400
    if rate is None or float(rate) <= 0:
        return jsonify({"error": "نرخ تبدیل باید عددی مثبت باشد"}), 400

    rate = float(rate)
    reverse_rate = 1.0 / rate

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create forward rate
        cursor.execute(
            """
            INSERT INTO exchange_rates (user_id, from_currency, to_currency, rate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, from_currency, to_currency, effective_date)
            DO UPDATE SET rate = EXCLUDED.rate
            RETURNING id
            """,
            (user_id, from_currency, to_currency, rate)
        )
        forward_id = cursor.fetchone()['id']

        # Create reverse rate
        cursor.execute(
            """
            INSERT INTO exchange_rates (user_id, from_currency, to_currency, rate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, from_currency, to_currency, effective_date)
            DO UPDATE SET rate = EXCLUDED.rate
            RETURNING id
            """,
            (user_id, to_currency, from_currency, reverse_rate)
        )
        reverse_id = cursor.fetchone()['id']

        conn.commit()
        return jsonify({
            "id": forward_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "reverse_id": reverse_id,
            "reverse_rate": reverse_rate,
        }), 201
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:rate_id>", methods=["PUT"])
def update_rate(rate_id):
    """Update an exchange rate.
    ---
    tags:
      - Exchange Rates
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: rate_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - rate
          properties:
            rate:
              type: number
    responses:
      200:
        description: Exchange rate updated
      404:
        description: Rate not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    rate = data.get("rate")
    if rate is None or float(rate) <= 0:
        return jsonify({"error": "نرخ تبدیل باید عددی مثبت باشد"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM exchange_rates WHERE id = %s AND user_id = %s",
            (rate_id, user_id)
        )
        existing = cursor.fetchone()
        if existing is None:
            return jsonify({"error": "نرخ تبدیل یافت نشد"}), 404

        rate = float(rate)
        reverse_rate = 1.0 / rate

        cursor.execute(
            "UPDATE exchange_rates SET rate = %s WHERE id = %s",
            (rate, rate_id)
        )

        # Update reverse rate
        cursor.execute(
            """
            UPDATE exchange_rates SET rate = %s
            WHERE user_id = %s AND from_currency = %s AND to_currency = %s
            """,
            (reverse_rate, user_id, existing['to_currency'], existing['from_currency'])
        )

        conn.commit()
        return jsonify({"id": rate_id, "rate": rate})
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:rate_id>", methods=["DELETE"])
def delete_rate(rate_id):
    """Delete an exchange rate.
    ---
    tags:
      - Exchange Rates
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: rate_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Exchange rate deleted
      404:
        description: Rate not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM exchange_rates WHERE id = %s AND user_id = %s",
            (rate_id, user_id)
        )
        existing = cursor.fetchone()
        if existing is None:
            return jsonify({"error": "نرخ تبدیل یافت نشد"}), 404

        # Delete both forward and reverse
        cursor.execute("DELETE FROM exchange_rates WHERE id = %s", (rate_id,))
        cursor.execute(
            "DELETE FROM exchange_rates WHERE user_id = %s AND from_currency = %s AND to_currency = %s",
            (user_id, existing['to_currency'], existing['from_currency'])
        )

        conn.commit()
        return jsonify({"message": "نرخ تبدیل حذف شد"})
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/currencies", methods=["GET"])
def list_currencies():
    """List supported currencies.
    ---
    tags:
      - Exchange Rates
    responses:
      200:
        description: List of supported currency codes
    """
    return jsonify(SUPPORTED_CURRENCIES)
