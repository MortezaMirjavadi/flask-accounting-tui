"""Alert API routes — wraps AlertService for financial alerts."""

from flask import Blueprint, jsonify

from app.utils.helpers import get_user_id_from_request
from services.alert_service import AlertService

bp = Blueprint("alerts", __name__)


@bp.route("/", methods=["GET"])
def get_alerts():
    """Generate alerts for upcoming bills and cashflow risks.
    ---
    tags:
      - Alerts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: List of generated alerts
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        alerts = AlertService.generate_alerts(user_id)
        return jsonify(AlertService.to_dict(alerts))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
