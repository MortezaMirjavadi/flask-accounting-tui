from flask import Blueprint, request, jsonify
from app.models import validate_user_payload
from app.services.auth_service import AuthService

bp = Blueprint('auth', __name__)


def _get_admin_user():
    """Return (user_dict, error_response) for an admin-verified request."""
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return None, (jsonify({"error": "Username is required"}), 400)

    result, error = AuthService.get_user_by_username(username)
    if error:
        return None, (jsonify({"error": error}), 404)
    if not result.get("is_admin"):
        return None, (jsonify({"error": "Admin access required"}), 403)
    return result, None


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_user_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result, error = AuthService.register_user(
        payload["username"], payload["password"],
        display_name=payload.get("display_name"),
        email=payload.get("email"),
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result), 201


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    result, error = AuthService.authenticate_user(username, password)
    if error:
        return jsonify({"error": error}), 401

    return jsonify(result)


@bp.route("/me", methods=["GET"])
def me():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400

    result, error = AuthService.get_user_by_username(username)
    if error:
        return jsonify({"error": error}), 404

    return jsonify(result)


@bp.route("/pending-users", methods=["GET"])
def pending_users():
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.get_pending_users()
    if error:
        return jsonify({"error": error}), 500

    return jsonify(result)


@bp.route("/approve-user/<int:user_id>", methods=["POST"])
def approve_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.approve_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/reject-user/<int:user_id>", methods=["POST"])
def reject_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.reject_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/users", methods=["GET"])
def all_users():
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.get_all_users()
    if error:
        return jsonify({"error": error}), 500

    return jsonify(result)


@bp.route("/activate-user/<int:user_id>", methods=["POST"])
def activate_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.activate_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/deactivate-user/<int:user_id>", methods=["POST"])
def deactivate_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.deactivate_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/users", methods=["POST"])
def create_user():
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    result, error = AuthService.create_user_by_admin(
        username, password,
        display_name=data.get("display_name", "").strip() or None,
        email=data.get("email", "").strip() or None,
        is_admin=bool(data.get("is_admin", False)),
        is_active=bool(data.get("is_active", True)),
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result), 201


@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.get_user_by_id(user_id)
    if error:
        return jsonify({"error": error}), 404

    return jsonify(result)


@bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    data = request.get_json(force=True, silent=True) or {}

    result, error = AuthService.update_user(
        user_id,
        display_name=data.get("display_name"),
        email=data.get("email"),
        is_admin=data.get("is_admin"),
        is_approved=data.get("is_approved"),
        is_active=data.get("is_active"),
        password=data.get("password") or None,
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.delete_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/setup-2fa", methods=["POST"])
def setup_2fa():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400
    result, error = AuthService.setup_totp(username)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/enable-2fa", methods=["POST"])
def enable_2fa():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    secret = data.get("secret", "").strip()
    code = data.get("code", "").strip()
    if not username or not secret or not code:
        return jsonify({"error": "Username, secret, and code are required"}), 400
    result, error = AuthService.enable_totp(username, secret, code)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/disable-2fa", methods=["POST"])
def disable_2fa():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400
    result, error = AuthService.disable_totp(username)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    code = data.get("code", "").strip()
    if not username or not code:
        return jsonify({"error": "Username and code are required"}), 400
    result, error = AuthService.verify_totp(username, code)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)
