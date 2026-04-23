from flask import Blueprint, jsonify
from app.utils.helpers import get_user_id_from_request
from database import get_connection

bp = Blueprint('settings', __name__)


@bp.route("/reset", methods=["POST"])
def reset_all_data():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM sources WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))
    # Note: budget_periods and budget_items will be deleted via CASCADE if set up,
    # otherwise add explicit deletes
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "All data reset successfully"})
