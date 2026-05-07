from flask import Blueprint, request, jsonify
from app.models import validate_user_payload
from app.services.auth_service import AuthService

bp = Blueprint('auth', __name__)


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_user_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result, error = AuthService.register_user(
        payload["username"], payload["password"]
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
