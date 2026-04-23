import sqlite3
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.models import validate_category_payload
from database import get_connection

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
    
    query = "SELECT * FROM categories WHERE user_id = ?"
    params = [user_id]
    
    if name_filter:
        query += " AND name LIKE ?"
        params.append(f"%{name_filter}%")
    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([row_to_dict(r) for r in rows])


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
            "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)",
            (user_id, payload["name"], payload["type"]),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    
    conn.close()
    return jsonify({"id": new_id, **payload}), 201


@bp.route("/<int:cat_id>", methods=["GET"])
def get_category(cat_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?",
        (cat_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return jsonify({"error": "Category not found"}), 404
    
    return jsonify(row_to_dict(row))


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
    
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?",
        (cat_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    
    try:
        cursor.execute(
            "UPDATE categories SET name = ?, type = ? WHERE id = ? AND user_id = ?",
            (payload["name"], payload["type"], cat_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 400
    
    conn.close()
    return jsonify({"id": cat_id, **payload})


@bp.route("/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?",
        (cat_id, user_id)
    )
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    
    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Category deleted"})
