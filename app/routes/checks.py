from flask import Blueprint, jsonify, request

from app.models import validate_check_payload
from app.utils.helpers import get_user_id_from_request
from app.utils.pagination import parse_pagination
from services.check_service import CheckService

bp = Blueprint('checks', __name__)


@bp.route("", methods=["GET"])
def list_checks():
    """List checks with optional filters.
    ---
    tags:
      - Checks
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
      - name: status
        in: query
        type: string
      - name: bank_name
        in: query
        type: string
      - name: check_number
        in: query
        type: string
      - name: type
        in: query
        type: string
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Paginated list of checks
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    status = request.args.get("status", "").strip().lower()
    bank_name = request.args.get("bank_name", "").strip()
    check_number = request.args.get("check_number", "").strip()
    check_type = request.args.get("type", "").strip().lower()
    wallet_id = request.args.get("wallet_id", type=int)

    params = {
        "status": status or None,
        "bank_name": bank_name or None,
        "check_number": check_number or None,
        "check_type": check_type or None,
        "wallet_id": wallet_id,
    }

    try:
        return jsonify(CheckService.list_checks(user_id, params=params, page=page, per_page=per_page))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("", methods=["POST"])
def add_check():
    """Add a new check.
    ---
    tags:
      - Checks
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
          properties:
            check_number:
              type: string
            bank_name:
              type: string
            amount:
              type: number
            due_date:
              type: string
            type:
              type: string
            wallet_id:
              type: integer
    responses:
      201:
        description: Check created
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_check_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        return jsonify(CheckService.add_check(user_id, payload)), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>", methods=["GET"])
def get_check(check_id):
    """Get a check by ID.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: check_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Check details
      404:
        description: Check not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(CheckService.get_check(user_id, check_id))
    except Exception as exc:
        if str(exc) == "Check not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>/clear", methods=["POST"])
def clear_check(check_id):
    """Mark a check as cleared.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: check_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            cleared_date:
              type: string
    responses:
      200:
        description: Check marked as cleared
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    payload = request.get_json(force=True, silent=True) or {}
    cleared_date = payload.get("cleared_date")

    try:
        return jsonify(CheckService.mark_check_cleared(user_id, check_id, cleared_date=cleared_date))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>/due-date", methods=["PUT"])
def change_check_due_date(check_id):
    """Update a check's due date.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: check_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - due_date
          properties:
            due_date:
              type: string
    responses:
      200:
        description: Due date updated
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    payload = request.get_json(force=True, silent=True) or {}
    due_date = payload.get("due_date")
    if due_date is None or (isinstance(due_date, str) and not due_date.strip()):
        return jsonify({"error": "due_date is required"}), 400

    try:
        return jsonify(CheckService.update_check_dates(user_id, check_id, due_date=due_date))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>/bounce", methods=["POST"])
def bounce_check(check_id):
    """Mark a check as bounced.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: check_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Check marked as bounced
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(CheckService.mark_check_bounced(user_id, check_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>/cancel", methods=["POST"])
def cancel_check(check_id):
    """Cancel a check.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: check_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Check cancelled
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(CheckService.cancel_check(user_id, check_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/upcoming", methods=["GET"])
def upcoming_checks():
    """Get upcoming checks due within a number of days.
    ---
    tags:
      - Checks
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: days
        in: query
        type: integer
        default: 30
    responses:
      200:
        description: List of upcoming checks
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    days = request.args.get("days", type=int) or 30
    try:
        return jsonify(CheckService.get_upcoming_checks(user_id, days=days))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
