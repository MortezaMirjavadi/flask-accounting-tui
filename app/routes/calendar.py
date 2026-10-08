"""Calendar API routes — wraps CalendarService for financial events."""

from flask import Blueprint, jsonify, request

from app.utils.helpers import get_user_id_from_request, row_to_dict
from app.utils.pagination import parse_pagination
from services.calendar_service import CalendarService

bp = Blueprint("calendar", __name__)


# ── Events ──────────────────────────────────────────────────────────────

@bp.route("/events", methods=["GET"])
def list_events():
    """List calendar events.
    ---
    tags:
      - Calendar
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
      - name: include_inactive
        in: query
        type: string
        description: Set to "1", "true", or "yes" to include inactive events
    responses:
      200:
        description: Paginated list of calendar events
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    page, per_page = parse_pagination()
    include_inactive = request.args.get("include_inactive", "").lower() in ("1", "true", "yes")
    try:
        events = CalendarService.get_user_events(user_id, include_inactive=include_inactive, page=page, per_page=per_page)
        return jsonify(events)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events", methods=["POST"])
def create_event():
    """Create a calendar event.
    ---
    tags:
      - Calendar
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
          required:
            - title
            - frequency
          properties:
            title:
              type: string
            frequency:
              type: string
              enum: [once, daily, weekly, monthly, yearly]
            start_date:
              type: string
            end_date:
              type: string
            amount:
              type: number
            category_id:
              type: integer
            wallet_id:
              type: integer
            description:
              type: string
    responses:
      201:
        description: Created event and its instances
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        event, instances = CalendarService.create_event(user_id, data)
        return jsonify({"event": event, "instances": instances}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>", methods=["GET"])
def get_event(event_id):
    """Get a single calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Calendar event details
      404:
        description: Event not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        event = CalendarService.get_event(event_id, user_id)
        if event is None:
            return jsonify({"error": "رویداد یافت نشد"}), 404
        return jsonify(event)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    """Update a calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
            frequency:
              type: string
            start_date:
              type: string
            end_date:
              type: string
            amount:
              type: number
            category_id:
              type: integer
            wallet_id:
              type: integer
            description:
              type: string
    responses:
      200:
        description: Updated calendar event
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    try:
        event = CalendarService.update_event(event_id, user_id, data)
        return jsonify(event)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    """Delete a calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event deleted successfully
      404:
        description: Event not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        deleted = CalendarService.delete_event(event_id, user_id)
        if not deleted:
            return jsonify({"error": "رویداد یافت نشد"}), 404
        return jsonify({"message": "Event deleted"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>/cancel", methods=["POST"])
def cancel_event(event_id):
    """Cancel a calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event cancelled successfully
      404:
        description: Event not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        cancelled = CalendarService.cancel_event(event_id, user_id)
        if not cancelled:
            return jsonify({"error": "رویداد یافت نشد"}), 404
        return jsonify({"message": "Event cancelled"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>/pause", methods=["POST"])
def pause_event(event_id):
    """Pause a calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event paused successfully
      404:
        description: Event not found or inactive
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        paused = CalendarService.pause_event(event_id, user_id)
        if not paused:
            return jsonify({"error": "رویداد یافت نشد یا غیرفعال است"}), 404
        return jsonify({"message": "Event paused"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/events/<int:event_id>/resume", methods=["POST"])
def resume_event(event_id):
    """Resume a paused calendar event.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event resumed successfully
      404:
        description: Event not found or not paused
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        resumed = CalendarService.resume_event(event_id, user_id)
        if not resumed:
            return jsonify({"error": "رویداد یافت نشد یا متوقف نشده است"}), 404
        return jsonify({"message": "Event resumed"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Instances ───────────────────────────────────────────────────────────

@bp.route("/instances", methods=["GET"])
def list_instances():
    """List calendar event instances within a date range.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: start_date
        in: query
        type: string
        description: Filter instances from this date
      - name: end_date
        in: query
        type: string
        description: Filter instances up to this date
      - name: include_cancelled
        in: query
        type: string
        description: Set to "1", "true", or "yes" to include cancelled instances
      - name: wallet_id
        in: query
        type: integer
        description: Filter by wallet ID
    responses:
      200:
        description: List of calendar event instances
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    start_date = request.args.get("start_date", "").strip() or None
    end_date = request.args.get("end_date", "").strip() or None
    include_cancelled = request.args.get("include_cancelled", "").lower() in ("1", "true", "yes")
    wallet_id = request.args.get("wallet_id", type=int)
    try:
        CalendarService.ensure_instances(user_id)
        instances = CalendarService.get_instances(
            user_id,
            start_date=start_date,
            end_date=end_date,
            include_cancelled=include_cancelled,
            wallet_id=wallet_id,
        )
        return jsonify(instances)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/instances/<int:instance_id>/confirm", methods=["POST"])
def confirm_instance(instance_id):
    """Confirm a calendar event instance.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: instance_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Instance confirmed
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        result = CalendarService.confirm_instance(instance_id, user_id)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/instances/<int:instance_id>/snooze", methods=["POST"])
def snooze_instance(instance_id):
    """Snooze a calendar event instance to a new date.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: instance_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - new_due_date
          properties:
            new_due_date:
              type: string
              description: New due date for the instance
    responses:
      200:
        description: Instance snoozed
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    new_due_date = data.get("new_due_date", "").strip()
    if not new_due_date:
        return jsonify({"error": "new_due_date الزامی است"}), 400
    try:
        result = CalendarService.snooze_instance(instance_id, user_id, new_due_date)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/instances/<int:instance_id>/cancel", methods=["POST"])
def cancel_instance(instance_id):
    """Cancel a calendar event instance.
    ---
    tags:
      - Calendar
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: instance_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Instance cancelled
      404:
        description: Instance not found or already resolved
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    try:
        cancelled = CalendarService.cancel_instance(instance_id, user_id)
        if not cancelled:
            return jsonify({"error": "نمونه یافت نشد یا قبلاً حل شده است"}), 404
        return jsonify({"message": "Instance cancelled"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
