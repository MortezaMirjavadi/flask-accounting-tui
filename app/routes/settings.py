from flask import Blueprint, jsonify
from app.utils.helpers import get_user_id_from_request
from database import get_connection, release_connection

bp = Blueprint('settings', __name__)


@bp.route("/reset", methods=["POST"])
def reset_all_data():
    """Reset all user data by soft-deleting all records.
    ---
    tags:
      - Settings
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: All data archived successfully
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s AND deleted_at IS NULL", (user_id,))
    cursor.execute("UPDATE transfers SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s AND deleted_at IS NULL", (user_id,))
    cursor.execute(
        """
        UPDATE budget_items
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE budget_period_id IN (
            SELECT id FROM budget_periods WHERE user_id = %s AND deleted_at IS NULL
        ) AND deleted_at IS NULL
        """,
        (user_id,),
    )
    cursor.execute("UPDATE budget_periods SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s AND deleted_at IS NULL", (user_id,))
    cursor.execute("UPDATE wallets SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s AND deleted_at IS NULL", (user_id,))
    cursor.execute("UPDATE categories SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s AND deleted_at IS NULL", (user_id,))
    
    conn.commit()
    cursor.close()
    release_connection(conn)
    
    return jsonify({"message": "All data archived successfully"})
