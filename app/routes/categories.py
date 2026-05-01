import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_category_payload
from database import get_connection, release_connection

bp = Blueprint('categories', __name__)


@bp.route("", methods=["GET"])
def list_categories():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    name_filter = request.args.get("name", "").strip()
    type_filter = request.args.get("type", "").strip()

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM categories WHERE user_id = %s AND deleted_at IS NULL"
        params = [user_id]
        
        if name_filter:
            query += " AND name LIKE %s"
            params.append(f"%{name_filter}%")
        if type_filter:
            query += " AND type = %s"
            params.append(type_filter)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return jsonify([row_to_dict(r) for r in rows])
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
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
            return jsonify({"error": "Category not found"}), 404
        
        return jsonify(row_to_dict(row))
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:cat_id>", methods=["PUT"])
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
    
    try:
        cursor.execute(
            "SELECT id FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id)
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "Category not found"}), 404
        
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
            return jsonify({"error": "Category not found"}), 404
        
        cursor.execute(
            "UPDATE categories SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (cat_id, user_id),
        )
        conn.commit()
        
        return jsonify({"message": "Category archived"})
    finally:
        cursor.close()
        release_connection(conn)
