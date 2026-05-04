from flask import Blueprint, jsonify, request

from app.models import (
    validate_installment_payment_payload,
    validate_installment_plan_payload,
)
from app.utils.helpers import get_user_id_from_request
from services.installment_service import InstallmentService

bp = Blueprint('installments', __name__)


@bp.route("/plans", methods=["GET"])
def list_installment_plans():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    status = request.args.get("status", "").strip().lower()
    try:
        plans = InstallmentService.list_installment_plans(user_id, status=status or None)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(plans)


@bp.route("/plans", methods=["POST"])
def create_plan():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    payload = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_installment_plan_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        return jsonify(InstallmentService.create_installment_plan(user_id, payload)), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/plans/<int:plan_id>", methods=["GET"])
def get_plan(plan_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.get_plan_details(user_id, plan_id))
    except Exception as exc:
        if str(exc) == "Plan not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400


@bp.route("/plans/<int:plan_id>/generate", methods=["POST"])
def regenerate_plan_installments(plan_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        installments = InstallmentService.generate_installments(plan_id, user_id=user_id)
        return jsonify(installments), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/plans/<int:plan_id>/cancel", methods=["POST"])
def cancel_plan(plan_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.cancel_installment_plan(user_id, plan_id))
    except Exception as exc:
        if str(exc) == "Plan not found or cannot be canceled":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400


@bp.route("/pay", methods=["POST"])
def pay_installments():
    user_id, err = get_user_id_from_request()
    if err:
        return err

    payload = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_installment_payment_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = InstallmentService.mark_installment_paid(
            user_id,
            payload["installment_ids"],
            paid_date=payload["paid_date"],
        )
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/<int:installment_id>/due-date", methods=["PUT"])
def change_installment_due_date(installment_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err

    payload = request.get_json(force=True, silent=True) or {}
    due_date = payload.get("due_date")
    if due_date is None or (isinstance(due_date, str) and not due_date.strip()):
        return jsonify({"error": "due_date is required"}), 400

    try:
        return jsonify(InstallmentService.update_installment_due_date(user_id, installment_id, due_date=due_date))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/upcoming", methods=["GET"])
def upcoming_installments():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    days = request.args.get("days", type=int) or 30
    try:
        return jsonify(InstallmentService.get_upcoming_installments(user_id, days=days))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/overdue", methods=["GET"])
def overdue_installments():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.get_overdue_installments(user_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/debt", methods=["GET"])
def remaining_debt():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.get_remaining_installment_debt(user_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
