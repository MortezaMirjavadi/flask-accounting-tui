import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_budget_period_payload, validate_budget_item_payload
from app.services.budget_service import BudgetService
from app.utils.pagination import parse_pagination, paginated_query
from database import get_connection, release_connection

bp = Blueprint('budget', __name__)


# Period routes

@bp.route("/periods", methods=["GET"])
def list_periods():
    """List budget periods.
    ---
    tags:
      - Budget
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
      - name: year
        in: query
        type: integer
      - name: month
        in: query
        type: integer
    responses:
      200:
        description: Paginated list of budget periods
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    year_filter = request.args.get("year", type=int)
    month_filter = request.args.get("month", type=int)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        where_clause = " WHERE bp.user_id = %s AND bp.deleted_at IS NULL"
        params = [user_id]

        if year_filter is not None:
            where_clause += " AND bp.year = %s"
            params.append(year_filter)
        if month_filter is not None:
            where_clause += " AND bp.month = %s"
            params.append(month_filter)

        join_clause = (
            " FROM budget_periods bp"
            " LEFT JOIN ("
            "   SELECT budget_period_id, COUNT(*) as item_count"
            "   FROM budget_items WHERE deleted_at IS NULL GROUP BY budget_period_id"
            " ) bi ON bp.id = bi.budget_period_id"
        )

        count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
        data_sql = (
            "SELECT bp.*, COALESCE(bi.item_count, 0) as item_count"
            + join_clause + where_clause + " ORDER BY bp.year DESC, bp.month DESC"
        )
        return paginated_query(cursor, count_sql, data_sql, params, row_to_dict, page, per_page)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/periods/with-items", methods=["GET"])
def list_periods_with_items():
    """List budget periods with their items.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: year
        in: query
        type: integer
      - name: month
        in: query
        type: integer
    responses:
      200:
        description: List of budget periods with nested items
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    
    result = BudgetService.get_periods_with_items(user_id, year, month)
    return jsonify(result)


@bp.route("/periods", methods=["POST"])
def create_period():
    """Create a new budget period.
    ---
    tags:
      - Budget
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
            - year
            - month
          properties:
            year:
              type: integer
            month:
              type: integer
    responses:
      201:
        description: Budget period created
    """
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
    """Get a budget period by ID.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Budget period details
      404:
        description: Period not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    row = BudgetService.get_period(cursor, period_id, user_id)
    cursor.close()
    release_connection(conn)
    
    if row is None:
        return jsonify({"error": "دوره بودجه یافت نشد"}), 404

    return jsonify(row_to_dict(row))


@bp.route("/periods/<int:period_id>", methods=["PUT"])
def update_period(period_id):
    """Update a budget period.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - year
            - month
          properties:
            year:
              type: integer
            month:
              type: integer
    responses:
      200:
        description: Budget period updated
      404:
        description: Period not found
    """
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
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دوره بودجه یافت نشد"}), 404
    
    try:
        cursor.execute(
            "UPDATE budget_periods SET year = %s, month = %s WHERE id = %s AND user_id = %s",
            (payload["year"], payload["month"], period_id, user_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دوره بودجه برای این سال/ماه قبلاً ثبت شده است"}), 400
    
    cursor.close()
    release_connection(conn)
    return jsonify({"id": period_id, "year": payload["year"], "month": payload["month"]})


@bp.route("/periods/<int:period_id>", methods=["DELETE"])
def delete_period(period_id):
    """Soft-delete a budget period.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Budget period archived
      404:
        description: Period not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    success, error = BudgetService.delete_period(period_id, user_id)
    if not success:
        return jsonify({"error": error}), 404
    
    return jsonify({"message": "Budget period archived"})


# Item routes

@bp.route("/items", methods=["POST"])
def create_item():
    """Create a budget item in a period.
    ---
    tags:
      - Budget
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
            - budget_period_id
            - category_id
            - planned_amount
          properties:
            budget_period_id:
              type: integer
            category_id:
              type: integer
            planned_amount:
              type: number
            notes:
              type: string
    responses:
      201:
        description: Budget item created
    """
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
        return jsonify({"error": "budget_period_id الزامی است"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_period(cursor, period_id, user_id) is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دوره بودجه یافت نشد"}), 404

    # Verify category belongs to user
    cursor.execute(
        "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (payload["category_id"], user_id),
    )
    if cursor.fetchone() is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دسته‌بندی یافت نشد یا متعلق به شما نیست"}), 400

    try:
        cursor.execute(
            """
            INSERT INTO budget_items (budget_period_id, category_id, planned_amount, notes)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (period_id, payload["category_id"], payload["planned_amount"], payload["notes"]),
        )
        conn.commit()
        new_id = cursor.fetchone()['id']
    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.execute(
            """
            SELECT id FROM budget_items
            WHERE budget_period_id = %s AND category_id = %s AND deleted_at IS NOT NULL
            """,
            (period_id, payload["category_id"]),
        )
        archived = cursor.fetchone()
        if archived is None:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "قلم بودجه برای این دسته‌بندی در این دوره قبلاً ثبت شده است"}), 400
        cursor.execute(
            """
            UPDATE budget_items
            SET planned_amount = %s, notes = %s, deleted_at = NULL
            WHERE id = %s
            """,
            (payload["planned_amount"], payload["notes"], archived["id"]),
        )
        conn.commit()
        new_id = archived["id"]
    
    cursor.close()
    release_connection(conn)
    return jsonify({"id": new_id, "budget_period_id": period_id, **payload}), 201


@bp.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """Get a budget item by ID.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: item_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Budget item details
      404:
        description: Item not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    row = BudgetService.get_item(cursor, item_id, user_id)
    cursor.close()
    release_connection(conn)
    
    if row is None:
        return jsonify({"error": "قلم بودجه یافت نشد"}), 404
    
    return jsonify(row_to_dict(row))


@bp.route("/periods/<int:period_id>/items", methods=["GET"])
def list_items(period_id):
    """List items for a budget period.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: period_id
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
        description: Paginated list of budget items
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if BudgetService.get_period(cursor, period_id, user_id) is None:
            return jsonify({"error": "دوره بودجه یافت نشد"}), 404

        where_clause = " WHERE bi.budget_period_id = %s AND bi.deleted_at IS NULL"
        params = [period_id]

        count_sql = "SELECT COUNT(*) as total FROM budget_items bi" + where_clause
        data_sql = (
            "SELECT bi.*, c.name as category_name, c.type as category_type"
            " FROM budget_items bi JOIN categories c ON bi.category_id = c.id"
            + where_clause
        )
        return paginated_query(cursor, count_sql, data_sql, params, row_to_dict, page, per_page)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """Update a budget item.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: item_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - category_id
            - planned_amount
          properties:
            category_id:
              type: integer
            planned_amount:
              type: number
            notes:
              type: string
    responses:
      200:
        description: Budget item updated
      404:
        description: Item not found
    """
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
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "قلم بودجه یافت نشد"}), 404

    # Verify category belongs to user
    cursor.execute(
        "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (payload["category_id"], user_id),
    )
    if cursor.fetchone() is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دسته‌بندی یافت نشد یا متعلق به شما نیست"}), 400

    try:
        cursor.execute(
            "UPDATE budget_items SET category_id = %s, planned_amount = %s, notes = %s WHERE id = %s AND deleted_at IS NULL",
            (payload["category_id"], payload["planned_amount"], payload["notes"], item_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "قلم بودجه برای این دسته‌بندی در این دوره قبلاً ثبت شده است"}), 400
    
    cursor.close()
    release_connection(conn)
    return jsonify({"id": item_id, **payload})


@bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """Soft-delete a budget item.
    ---
    tags:
      - Budget
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: item_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Budget item archived
      404:
        description: Item not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if BudgetService.get_item(cursor, item_id, user_id) is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "قلم بودجه یافت نشد"}), 404
    
    cursor.execute(
        "UPDATE budget_items SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL",
        (item_id,),
    )
    conn.commit()
    cursor.close()
    release_connection(conn)
    
    return jsonify({"message": "Budget item archived"})
