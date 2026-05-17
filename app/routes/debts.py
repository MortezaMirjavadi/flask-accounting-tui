"""Debt & Receivable management routes."""

from flask import Blueprint, request, jsonify

from app.models import validate_debt_payload, validate_debt_payment_payload
from app.utils.helpers import get_user_id_from_request, gregorian_to_jalali
from app.utils.pagination import parse_pagination
from services.debt_service import DebtService

bp = Blueprint('debts', __name__)


def _serialize(row):
    """Convert date fields to Jalali for JSON response."""
    d = dict(row)
    for field in ("issue_date", "due_date"):
        if d.get(field):
            d[field] = gregorian_to_jalali(d[field])
    if d.get("payment_date"):
        d["payment_date"] = gregorian_to_jalali(d["payment_date"])
    if d.get("changed_at"):
        d["changed_at"] = str(d["changed_at"])
    if d.get("created_at"):
        d["created_at"] = str(d["created_at"])
    return d


# ── CRUD ───────────────────────────────────────────────────────────

@bp.route("", methods=["GET"])
def list_debts():
    """List debts with optional filters.
    ---
    tags:
      - Debts
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
      - name: type
        in: query
        type: string
        description: Debt type filter (e.g. payable, receivable)
      - name: status
        in: query
        type: string
      - name: counterparty
        in: query
        type: string
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Paginated list of debts
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    page, per_page = parse_pagination()
    debt_type = request.args.get("type", "").strip() or None
    status = request.args.get("status", "").strip() or None
    counterparty = request.args.get("counterparty", "").strip() or None
    wallet_id = request.args.get("wallet_id", type=int)
    result = DebtService.list_debts(
        user_id, debt_type=debt_type, status=status,
        counterparty=counterparty, page=page, per_page=per_page,
        wallet_id=wallet_id,
    )
    result["items"] = [_serialize(r) for r in result["items"]]
    return jsonify(result)


@bp.route("", methods=["POST"])
def create_debt():
    """Create a new debt.
    ---
    tags:
      - Debts
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
        description: Debt created
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_debt_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row, error = DebtService.create_debt(user_id, payload)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row)), 201


@bp.route("/<int:debt_id>", methods=["GET"])
def get_debt(debt_id):
    """Get a debt by ID.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Debt details
      404:
        description: Debt not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = DebtService.get_debt(debt_id, user_id)
    if row is None:
        return jsonify({"error": "بدهی یافت نشد"}), 404
    return jsonify(_serialize(row))


@bp.route("/<int:debt_id>", methods=["PUT"])
def update_debt(debt_id):
    """Update a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
    responses:
      200:
        description: Debt updated
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = DebtService.update_debt(debt_id, user_id, data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row))


# ── Payments ───────────────────────────────────────────────────────

@bp.route("/<int:debt_id>/payments", methods=["GET"])
def list_payments(debt_id):
    """List payments for a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of payments
      404:
        description: Debt not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result, error = DebtService.get_payments(debt_id, user_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify([_serialize(r) for r in result])


@bp.route("/<int:debt_id>/payments", methods=["POST"])
def add_payment(debt_id):
    """Add a payment to a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
    responses:
      201:
        description: Payment recorded
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        payload = validate_debt_payment_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row, error = DebtService.register_payment(debt_id, user_id, payload)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row)), 201


@bp.route("/payments/<int:payment_id>/reverse", methods=["POST"])
def reverse_payment(payment_id):
    """Reverse a debt payment.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: payment_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Payment reversed
      400:
        description: Error reversing payment
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = DebtService.reverse_payment(payment_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Payment reversed"})


# ── Status Transitions ─────────────────────────────────────────────

@bp.route("/<int:debt_id>/write-off", methods=["POST"])
def write_off(debt_id):
    """Write off a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            note:
              type: string
    responses:
      200:
        description: Debt written off
      400:
        description: Error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = DebtService.write_off(debt_id, user_id, note=data.get("note"))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row))


@bp.route("/<int:debt_id>/cancel", methods=["POST"])
def cancel_debt(debt_id):
    """Cancel a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            note:
              type: string
    responses:
      200:
        description: Debt canceled
      400:
        description: Error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = DebtService.cancel_debt(debt_id, user_id, note=data.get("note"))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row))


@bp.route("/<int:debt_id>/settle", methods=["POST"])
def settle_debt(debt_id):
    """Manually settle a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            note:
              type: string
    responses:
      200:
        description: Debt settled
      400:
        description: Error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = DebtService.settle_manually(debt_id, user_id, note=data.get("note"))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_serialize(row))


@bp.route("/<int:debt_id>/history", methods=["GET"])
def status_history(debt_id):
    """Get status change history for a debt.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: debt_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Status history list
      404:
        description: Debt not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result, error = DebtService.get_status_history(debt_id, user_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify([_serialize(r) for r in result])


# ── Analytics ──────────────────────────────────────────────────────

@bp.route("/summary", methods=["GET"])
def summary():
    """Get debt summary analytics.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: Debt summary with totals and recent payments
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    wallet_id = request.args.get("wallet_id", type=int)
    result = DebtService.get_summary(user_id, wallet_id=wallet_id)
    # Convert payment dates to Jalali
    if result.get("recent_payments"):
        result["recent_payments"] = [_serialize(p) for p in result["recent_payments"]]
    return jsonify(result)


@bp.route("/overdue", methods=["GET"])
def overdue():
    """List overdue debts.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: List of overdue debts
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    wallet_id = request.args.get("wallet_id", type=int)
    rows = DebtService.get_overdue(user_id, wallet_id=wallet_id)
    return jsonify([_serialize(r) for r in rows])


@bp.route("/due-soon", methods=["GET"])
def due_soon():
    """List debts due soon.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: days
        in: query
        type: integer
        default: 7
      - name: wallet_id
        in: query
        type: integer
    responses:
      200:
        description: List of debts due within the specified days
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    days = request.args.get("days", 7, type=int)
    wallet_id = request.args.get("wallet_id", type=int)
    rows = DebtService.get_due_soon(user_id, days=days, wallet_id=wallet_id)
    return jsonify([_serialize(r) for r in rows])


@bp.route("/counterparty/<name>", methods=["GET"])
def counterparty_balance(name):
    """Get balance summary for a counterparty.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: name
        in: path
        type: string
        required: true
        description: Counterparty name
    responses:
      200:
        description: Counterparty balance and associated debts
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = DebtService.get_counterparty_balance(user_id, name)
    result["debts"] = [_serialize(d) for d in result.get("debts", [])]
    return jsonify(result)


@bp.route("/aging", methods=["GET"])
def aging_report():
    """Get debt aging report.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: Debt aging report by time buckets
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = DebtService.get_aging_report(user_id)
    return jsonify(result)


@bp.route("/repayments/monthly", methods=["GET"])
def monthly_repayments():
    """Get monthly repayment statistics.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: months
        in: query
        type: integer
        default: 6
    responses:
      200:
        description: Monthly repayment statistics
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    months = request.args.get("months", 6, type=int)
    result = DebtService.get_monthly_repayments(user_id, months=months)
    return jsonify(result)


@bp.route("/counterparties/top", methods=["GET"])
def top_counterparties():
    """Get top counterparties by debt volume.
    ---
    tags:
      - Debts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        default: 10
    responses:
      200:
        description: Top counterparties ranked by debt volume
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 10, type=int)
    result = DebtService.get_top_counterparties(user_id, limit=limit)
    return jsonify(result)
