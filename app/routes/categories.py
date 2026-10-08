import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_category_payload
from app.utils.pagination import parse_pagination, paginated_query
from database import get_connection, release_connection

bp = Blueprint('categories', __name__)


def _build_tree(rows):
    """Build a nested tree structure from flat category rows."""
    by_parent = {}
    for row in rows:
        pid = row.get("parent_id")
        by_parent.setdefault(pid, []).append(row)

    def attach_children(nodes):
        for node in nodes:
            children = by_parent.get(node["id"], [])
            children.sort(key=lambda c: c["name"])
            node["children"] = children
            attach_children(children)

    roots = by_parent.get(None, [])
    roots.sort(key=lambda c: c["name"])
    attach_children(roots)
    return roots


def _get_ancestors(cursor, cat_id):
    """Walk from a category up to root. Returns list of ancestor ids (excluding cat_id itself)."""
    ancestors = []
    current = cat_id
    seen = set()
    while current is not None:
        if current in seen:
            break
        seen.add(current)
        cursor.execute(
            "SELECT parent_id FROM categories WHERE id = %s AND deleted_at IS NULL",
            (current,),
        )
        row = cursor.fetchone()
        if row is None:
            break
        pid = row["parent_id"]
        if pid is not None:
            ancestors.append(pid)
        current = pid
    return ancestors


def _flatten_tree(nodes, depth=0):
    """Flatten a tree into a list with depth info for display."""
    result = []
    for node in nodes:
        node["_depth"] = depth
        result.append(node)
        result.extend(_flatten_tree(node.get("children", []), depth + 1))
    return result


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
      - name: tree
        in: query
        type: string
        description: Set to 'true' to get nested tree structure
      - name: name
        in: query
        type: string
        description: Filter by name (partial match)
      - name: type
        in: query
        type: string
        enum: [income, cost]
        description: Filter by category type
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
        description: Paginated list or tree of categories
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    name_filter = request.args.get("name", "").strip()
    type_filter = request.args.get("type", "").strip()
    tree_mode = request.args.get("tree", "").strip().lower() in ("true", "1", "yes")

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

        if tree_mode:
            data_sql = "SELECT id, user_id, name, type, parent_id, created_at, updated_at FROM categories" + where_clause + " ORDER BY id"
            cursor.execute(data_sql, params)
            rows = [dict(r) for r in cursor.fetchall()]
            tree = _build_tree(rows)
            return jsonify(tree)
        else:
            page, per_page = parse_pagination()
            count_sql = "SELECT COUNT(*) as total FROM categories" + where_clause
            data_sql = (
                "SELECT c.id, c.user_id, c.name, c.type, c.parent_id, c.created_at, c.updated_at,"
                " p.name as parent_name"
                " FROM categories c"
                " LEFT JOIN categories p ON c.parent_id = p.id AND p.deleted_at IS NULL"
                + where_clause.replace("WHERE user_id", "WHERE c.user_id").replace("deleted_at IS NULL", "c.deleted_at IS NULL")
                + " ORDER BY c.parent_id NULLS FIRST, c.name"
            )
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
            parent_id:
              type: integer
              description: Parent category ID (null for root)
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

    parent_id = payload.get("parent_id")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Validate parent exists and belongs to user, and type matches
        if parent_id is not None:
            cursor.execute(
                "SELECT id, type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (parent_id, user_id),
            )
            parent_row = cursor.fetchone()
            if parent_row is None:
                return jsonify({"error": "دسته‌بندی والد یافت نشد"}), 400
            if parent_row["type"] != payload["type"]:
                return jsonify({"error": "نوع دسته‌بندی فرزند باید با والد یکسان باشد"}), 400

        cursor.execute(
            "INSERT INTO categories (user_id, name, type, parent_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, payload["name"], payload["type"], parent_id),
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
            "UPDATE categories SET type = %s, parent_id = %s, deleted_at = NULL WHERE id = %s",
            (payload["type"], parent_id, archived["id"]),
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
            "SELECT c.*, p.name as parent_name FROM categories c"
            " LEFT JOIN categories p ON c.parent_id = p.id AND p.deleted_at IS NULL"
            " WHERE c.id = %s AND c.user_id = %s AND c.deleted_at IS NULL",
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
            parent_id:
              type: integer
              description: Parent category ID (null for root)
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

    parent_id = payload.get("parent_id")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 404

        # Prevent setting self as parent
        if parent_id == cat_id:
            return jsonify({"error": "یک دسته‌بندی نمی‌تواند والد خودش باشد"}), 400

        # Validate parent exists and type matches
        if parent_id is not None:
            cursor.execute(
                "SELECT id, type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (parent_id, user_id),
            )
            parent_row = cursor.fetchone()
            if parent_row is None:
                return jsonify({"error": "دسته‌بندی والد یافت نشد"}), 400
            if parent_row["type"] != payload["type"]:
                return jsonify({"error": "نوع دسته‌بندی فرزند باید با والد یکسان باشد"}), 400

            # Prevent circular reference
            ancestors = _get_ancestors(cursor, parent_id)
            if cat_id in ancestors:
                return jsonify({"error": "مرجع دایره‌ای: نمی‌توانید یک دسته‌بندی را به فرزند خودش تبدیل کنید"}), 400

        cursor.execute(
            "UPDATE categories SET name = %s, type = %s, parent_id = %s WHERE id = %s AND user_id = %s",
            (payload["name"], payload["type"], parent_id, cat_id, user_id),
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
            "SELECT id, parent_id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 404

        old_parent_id = row["parent_id"]

        # Reparent children to the deleted node's parent
        cursor.execute(
            "UPDATE categories SET parent_id = %s WHERE parent_id = %s AND deleted_at IS NULL",
            (old_parent_id, cat_id),
        )

        cursor.execute(
            "UPDATE categories SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id),
        )
        conn.commit()

        return jsonify({"message": "Category archived"})
    finally:
        cursor.close()
        release_connection(conn)
