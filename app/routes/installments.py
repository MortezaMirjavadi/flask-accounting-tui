from flask import Blueprint, jsonify, request

from app.models import (
    validate_installment_payment_payload,
    validate_installment_plan_payload,
)
from app.utils.helpers import get_user_id_from_request
from app.utils.pagination import parse_pagination
from services.installment_service import InstallmentService

bp = Blueprint('installments', __name__)


@bp.route("/plans", methods=["GET"])
def list_installment_plans():
    """List installment plans.
    ---
    tags:
      - Installments
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
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Paginated list of installment plans
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    status = request.args.get("status", "").strip().lower()
    wallet_id = request.args.get("wallet_id", type=int)
    try:
        result = InstallmentService.list_installment_plans(user_id, status=status or None, wallet_id=wallet_id, page=page, per_page=per_page)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/plans", methods=["POST"])
def create_plan():
    """Create an installment plan.
    ---
    tags:
      - Installments
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
    responses:
      201:
        description: Installment plan created
      400:
        description: Validation error
    """
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
    """Get installment plan details.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: plan_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Installment plan details
      404:
        description: Plan not found
    """
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
    """Regenerate installments for a plan.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: plan_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Regenerated installments list
    """
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
    """Cancel an installment plan.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: plan_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Plan canceled
      404:
        description: Plan not found or cannot be canceled
    """
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
    """Mark installments as paid.
    ---
    tags:
      - Installments
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
            installment_ids:
              type: array
              items:
                type: integer
            paid_date:
              type: string
    responses:
      200:
        description: Installments marked as paid
      400:
        description: Validation error
    """
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
    """Change an installment's due date.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: installment_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            due_date:
              type: string
    responses:
      200:
        description: Due date updated
      400:
        description: Validation error
    """
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
    """List upcoming installments.
    ---
    tags:
      - Installments
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
        description: List of upcoming installments
    """
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
    """List overdue installments.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: List of overdue installments
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.get_overdue_installments(user_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/debt", methods=["GET"])
def remaining_debt():
    """Get remaining installment debt summary.
    ---
    tags:
      - Installments
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: Remaining installment debt summary
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        return jsonify(InstallmentService.get_remaining_installment_debt(user_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
