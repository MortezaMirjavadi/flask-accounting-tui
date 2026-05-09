"""Debt & Receivable management routes."""

from flask import Blueprint, request, jsonify

from app.models import validate_debt_payload, validate_debt_payment_payload
from app.utils.helpers import get_user_id_from_request, gregorian_to_jalali
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    debt_type = request.args.get("type", "").strip() or None
    status = request.args.get("status", "").strip() or None
    counterparty = request.args.get("counterparty", "").strip() or None
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    rows = DebtService.list_debts(
        user_id, debt_type=debt_type, status=status,
        counterparty=counterparty, limit=limit, offset=offset,
    )
    return jsonify([_serialize(r) for r in rows])


@bp.route("", methods=["POST"])
def create_debt():
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = DebtService.get_debt(debt_id, user_id)
    if row is None:
        return jsonify({"error": "Debt not found"}), 404
    return jsonify(_serialize(row))


@bp.route("/<int:debt_id>", methods=["PUT"])
def update_debt(debt_id):
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result, error = DebtService.get_payments(debt_id, user_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify([_serialize(r) for r in result])


@bp.route("/<int:debt_id>/payments", methods=["POST"])
def add_payment(debt_id):
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
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = DebtService.get_summary(user_id)
    # Convert payment dates to Jalali
    if result.get("recent_payments"):
        result["recent_payments"] = [_serialize(p) for p in result["recent_payments"]]
    return jsonify(result)


@bp.route("/overdue", methods=["GET"])
def overdue():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    rows = DebtService.get_overdue(user_id)
    return jsonify([_serialize(r) for r in rows])


@bp.route("/due-soon", methods=["GET"])
def due_soon():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    days = request.args.get("days", 7, type=int)
    rows = DebtService.get_due_soon(user_id, days=days)
    return jsonify([_serialize(r) for r in rows])


@bp.route("/counterparty/<name>", methods=["GET"])
def counterparty_balance(name):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = DebtService.get_counterparty_balance(user_id, name)
    result["debts"] = [_serialize(d) for d in result.get("debts", [])]
    return jsonify(result)


@bp.route("/aging", methods=["GET"])
def aging_report():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = DebtService.get_aging_report(user_id)
    return jsonify(result)


@bp.route("/repayments/monthly", methods=["GET"])
def monthly_repayments():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    months = request.args.get("months", 6, type=int)
    result = DebtService.get_monthly_repayments(user_id, months=months)
    return jsonify(result)


@bp.route("/counterparties/top", methods=["GET"])
def top_counterparties():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 10, type=int)
    result = DebtService.get_top_counterparties(user_id, limit=limit)
    return jsonify(result)
