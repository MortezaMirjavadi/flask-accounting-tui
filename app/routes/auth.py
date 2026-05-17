from flask import Blueprint, request, jsonify
from app.models import validate_user_payload
from app.services.auth_service import AuthService
from app.utils.pagination import parse_pagination

bp = Blueprint('auth', __name__)


def _get_admin_user():
    """Return (user_dict, error_response) for an admin-verified request."""
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return None, (jsonify({"error": "نام کاربری الزامی است"}), 400)

    result, error = AuthService.get_user_by_username(username)
    if error:
        return None, (jsonify({"error": error}), 404)
    if not result.get("is_admin"):
        return None, (jsonify({"error": "دسترسی مدیر لازم است"}), 403)
    return result, None


@bp.route("/register", methods=["POST"])
def register():
    """Register a new user.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
              minLength: 3
            password:
              type: string
              minLength: 6
            display_name:
              type: string
            email:
              type: string
    responses:
      201:
        description: User created successfully
      400:
        description: Validation error
    """
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
    """Authenticate user and return user info.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "نام کاربری و رمز عبور الزامی است"}), 400

    result, error = AuthService.authenticate_user(username, password)
    if error:
        return jsonify({"error": error}), 401

    return jsonify(result)


@bp.route("/me", methods=["GET"])
def me():
    """Get current user profile.
    ---
    tags:
      - Auth
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: User profile
      404:
        description: User not found
    """
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "نام کاربری الزامی است"}), 400

    result, error = AuthService.get_user_by_username(username)
    if error:
        return jsonify({"error": error}), 404

    return jsonify(result)


@bp.route("/pending-users", methods=["GET"])
def pending_users():
    """List pending users awaiting approval. Admin only.
    ---
    tags:
      - Auth (Admin)
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
        description: Paginated list of pending users
      403:
        description: Admin access required
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    page, per_page = parse_pagination()
    result, error = AuthService.get_pending_users(page=page, per_page=per_page)
    if error:
        return jsonify({"error": error}), 500

    return jsonify(result)


@bp.route("/approve-user/<int:user_id>", methods=["POST"])
def approve_user(user_id):
    """Approve a pending user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User approved
      400:
        description: Error approving user
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.approve_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/reject-user/<int:user_id>", methods=["POST"])
def reject_user(user_id):
    """Reject a pending user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User rejected
      400:
        description: Error rejecting user
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.reject_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/users", methods=["GET"])
def all_users():
    """List all users. Admin only.
    ---
    tags:
      - Auth (Admin)
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
        description: Paginated list of users
      403:
        description: Admin access required
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    page, per_page = parse_pagination()
    result, error = AuthService.get_all_users(page=page, per_page=per_page)
    if error:
        return jsonify({"error": error}), 500

    return jsonify(result)


@bp.route("/activate-user/<int:user_id>", methods=["POST"])
def activate_user(user_id):
    """Activate a deactivated user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User activated
      400:
        description: Error
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.activate_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/deactivate-user/<int:user_id>", methods=["POST"])
def deactivate_user(user_id):
    """Deactivate a user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User deactivated
      400:
        description: Error
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.deactivate_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user. Admin only.
    ---
    tags:
      - Auth (Admin)
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
          required: [username, password]
          properties:
            username:
              type: string
              minLength: 3
            password:
              type: string
              minLength: 6
            display_name:
              type: string
            email:
              type: string
            is_admin:
              type: boolean
            is_active:
              type: boolean
    responses:
      201:
        description: User created
      400:
        description: Validation error
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "نام کاربری و رمز عبور الزامی است"}), 400
    if len(username) < 3:
        return jsonify({"error": "نام کاربری باید حداقل ۳ کاراکتر باشد"}), 400
    if len(password) < 6:
        return jsonify({"error": "رمز عبور باید حداقل ۶ کاراکتر باشد"}), 400

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
    """Get user by ID. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User details
      404:
        description: User not found
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.get_user_by_id(user_id)
    if error:
        return jsonify({"error": error}), 404

    return jsonify(result)


@bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            display_name:
              type: string
            email:
              type: string
            is_admin:
              type: boolean
            is_approved:
              type: boolean
            is_active:
              type: boolean
            password:
              type: string
    responses:
      200:
        description: User updated
      400:
        description: Error
    """
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
    """Delete user. Admin only.
    ---
    tags:
      - Auth (Admin)
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User deleted
      400:
        description: Error
    """
    admin, err_resp = _get_admin_user()
    if err_resp:
        return err_resp

    result, error = AuthService.delete_user(user_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/setup-2fa", methods=["POST"])
def setup_2fa():
    """Set up two-factor authentication (generate TOTP secret).
    ---
    tags:
      - Auth (2FA)
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username]
          properties:
            username:
              type: string
    responses:
      200:
        description: TOTP secret and QR code
      400:
        description: Error
    """
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "نام کاربری الزامی است"}), 400
    result, error = AuthService.setup_totp(username)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/enable-2fa", methods=["POST"])
def enable_2fa():
    """Enable two-factor authentication (verify code and activate).
    ---
    tags:
      - Auth (2FA)
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, secret, code]
          properties:
            username:
              type: string
            secret:
              type: string
            code:
              type: string
    responses:
      200:
        description: 2FA enabled
      400:
        description: Error
    """
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    secret = data.get("secret", "").strip()
    code = data.get("code", "").strip()
    if not username or not secret or not code:
        return jsonify({"error": "نام کاربری، کد مخفی، و کد تأیید الزامی است"}), 400
    result, error = AuthService.enable_totp(username, secret, code)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/disable-2fa", methods=["POST"])
def disable_2fa():
    """Disable two-factor authentication.
    ---
    tags:
      - Auth (2FA)
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username]
          properties:
            username:
              type: string
    responses:
      200:
        description: 2FA disabled
      400:
        description: Error
    """
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "نام کاربری الزامی است"}), 400
    result, error = AuthService.disable_totp(username)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@bp.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    """Verify a TOTP code for two-factor authentication.
    ---
    tags:
      - Auth (2FA)
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, code]
          properties:
            username:
              type: string
            code:
              type: string
    responses:
      200:
        description: Code verified
      400:
        description: Invalid code
    """
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    code = data.get("code", "").strip()
    if not username or not code:
        return jsonify({"error": "نام کاربری و کد تأیید الزامی است"}), 400
    result, error = AuthService.verify_totp(username, code)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)
