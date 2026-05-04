from flask import Blueprint, jsonify, request

from app.models import validate_check_payload
from app.utils.helpers import get_user_id_from_request
from services.check_service import CheckService

bp = Blueprint('checks', __name__)


@bp.route("", methods=["GET"])
def list_checks():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    status = request.args.get("status", "").strip().lower()
    bank_name = request.args.get("bank_name", "").strip()
    check_number = request.args.get("check_number", "").strip()
    check_type = request.args.get("type", "").strip().lower()

    params = {
        "status": status or None,
        "bank_name": bank_name or None,
        "check_number": check_number or None,
        "check_type": check_type or None,
    }
    
    try:
        return jsonify(CheckService.list_checks(user_id, params=params))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("", methods=["POST"])
def add_check():
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(CheckService.mark_check_bounced(user_id, check_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:check_id>/cancel", methods=["POST"])
def cancel_check(check_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(CheckService.cancel_check(user_id, check_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/upcoming", methods=["GET"])
def upcoming_checks():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    days = request.args.get("days", type=int) or 30
    try:
        return jsonify(CheckService.get_upcoming_checks(user_id, days=days))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
