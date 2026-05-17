import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_category_payload
from app.utils.pagination import parse_pagination, paginated_query
from database import get_connection, release_connection

bp = Blueprint('categories', __name__)


@bp.route("", methods=["GET"])
def list_categories():
    """List all categories for the current user.
    ---
    tags:
      - Categories
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
        description: Filter by name (partial match)
      - name: type
        in: query
        type: string
        enum: [income, cost]
        description: Filter by category type
    responses:
      200:
        description: Paginated list of categories
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    name_filter = request.args.get("name", "").strip()
    type_filter = request.args.get("type", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        where_clause = " WHERE user_id = %s AND deleted_at IS NULL"
        params = [user_id]

        if name_filter:
            where_clause += " AND name LIKE %s"
            params.append(f"%{name_filter}%")
        if type_filter:
            where_clause += " AND type = %s"
            params.append(type_filter)

        count_sql = "SELECT COUNT(*) as total FROM categories" + where_clause
        data_sql = "SELECT * FROM categories" + where_clause + " ORDER BY id"
        return paginated_query(cursor, count_sql, data_sql, params, row_to_dict, page, per_page)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
def create_category():
    """Create a new category.
    ---
    tags:
      - Categories
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, type]
          properties:
            name:
              type: string
            type:
              type: string
              enum: [income, cost]
    responses:
      201:
        description: Category created
      400:
        description: Validation error
    """
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
            "INSERT INTO categories (user_id, name, type) VALUES (%s, %s, %s) RETURNING id",
            (user_id, payload["name"], payload["type"]),
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
    except psycopg2.IntegrityError as exc:
        conn.rollback()
        cursor.execute(
            "SELECT id FROM categories WHERE user_id = %s AND name = %s AND deleted_at IS NOT NULL",
            (user_id, payload["name"]),
        )
        archived = cursor.fetchone()
        if archived is None:
            return jsonify({"error": str(exc)}), 400
        cursor.execute(
            "UPDATE categories SET type = %s, deleted_at = NULL WHERE id = %s",
            (payload["type"], archived["id"]),
        )
        conn.commit()
        new_id = archived["id"]
    finally:
        cursor.close()
        release_connection(conn)
    
    return jsonify({"id": new_id, **payload}), 201


@bp.route("/<int:cat_id>", methods=["GET"])
def get_category(cat_id):
    """Get a single category by ID.
    ---
    tags:
      - Categories
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: cat_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Category details
      404:
        description: Category not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        row = cursor.fetchone()
        
        if row is None:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 404
        
        return jsonify(row_to_dict(row))
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    """Update a category.
    ---
    tags:
      - Categories
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: cat_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, type]
          properties:
            name:
              type: string
            type:
              type: string
              enum: [income, cost]
    responses:
      200:
        description: Category updated
      400:
        description: Validation error
      404:
        description: Category not found
    """
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
            "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 404
        
        cursor.execute(
            "UPDATE categories SET name = %s, type = %s WHERE id = %s AND user_id = %s",
            (payload["name"], payload["type"], cat_id, user_id),
        )
        conn.commit()
    except psycopg2.IntegrityError as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cursor.close()
        release_connection(conn)
    
    return jsonify({"id": cat_id, **payload})


@bp.route("/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    """Soft-delete a category.
    ---
    tags:
      - Categories
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: cat_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Category archived
      404:
        description: Category not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 404
        
        cursor.execute(
            "UPDATE categories SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id),
        )
        conn.commit()
        
        return jsonify({"message": "Category archived"})
    finally:
        cursor.close()
        release_connection(conn)
