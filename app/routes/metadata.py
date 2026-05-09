"""Contact, Tag, and Label management routes."""

from flask import Blueprint, request, jsonify

from app.utils.helpers import get_user_id_from_request
from services.metadata_service import ContactService, TagService, LabelService

bp = Blueprint('metadata', __name__)


# ── Contacts ────────────────────────────────────────────────────────

@bp.route("/contacts", methods=["GET"])
def list_contacts():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    search = request.args.get("q", "").strip() or None
    result = ContactService.list_contacts(user_id, search=search)
    return jsonify(result)


@bp.route("/contacts", methods=["POST"])
def create_contact():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    row, error = ContactService.create(user_id, {
        "name": name,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "address": (data.get("address") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
    })
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row), 201


@bp.route("/contacts/<int:contact_id>", methods=["GET"])
def get_contact(contact_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = ContactService.get_contact(contact_id, user_id)
    if not row:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(row)


@bp.route("/contacts/<int:contact_id>", methods=["PUT"])
def update_contact(contact_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = ContactService.update(contact_id, user_id, data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row)


@bp.route("/contacts/<int:contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = ContactService.delete(contact_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Contact deleted"})


# ── Tags ────────────────────────────────────────────────────────────

@bp.route("/tags", methods=["GET"])
def list_tags():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = TagService.list_tags(user_id)
    return jsonify(result)


@bp.route("/tags", methods=["POST"])
def create_tag():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    row, error = TagService.create(user_id, {
        "name": name,
        "color": (data.get("color") or "").strip() or None,
    })
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row), 201


@bp.route("/tags/<int:tag_id>", methods=["GET"])
def get_tag(tag_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = TagService.get_tag(tag_id, user_id)
    if not row:
        return jsonify({"error": "Tag not found"}), 404
    return jsonify(row)


@bp.route("/tags/<int:tag_id>", methods=["PUT"])
def update_tag(tag_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = TagService.update(tag_id, user_id, data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row)


@bp.route("/tags/<int:tag_id>", methods=["DELETE"])
def delete_tag(tag_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = TagService.delete(tag_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Tag deleted"})


@bp.route("/transactions/<int:tx_id>/tags", methods=["GET"])
def get_transaction_tags(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    tags = TagService.get_transaction_tags(tx_id)
    return jsonify(tags)


@bp.route("/transactions/<int:tx_id>/tags", methods=["PUT"])
def set_transaction_tags(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    tag_ids = data.get("tag_ids", [])
    if not isinstance(tag_ids, list):
        return jsonify({"error": "tag_ids must be a list"}), 400
    ok, error = TagService.set_transaction_tags(tx_id, tag_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Tags updated"})


# ── Labels ──────────────────────────────────────────────────────────

@bp.route("/labels", methods=["GET"])
def list_labels():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    result = LabelService.list_labels(user_id)
    return jsonify(result)


@bp.route("/labels", methods=["POST"])
def create_label():
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    row, error = LabelService.create(user_id, {
        "name": name,
        "color": (data.get("color") or "").strip() or None,
    })
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row), 201


@bp.route("/labels/<int:label_id>", methods=["GET"])
def get_label(label_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = LabelService.get_label(label_id, user_id)
    if not row:
        return jsonify({"error": "Label not found"}), 404
    return jsonify(row)


@bp.route("/labels/<int:label_id>", methods=["PUT"])
def update_label(label_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    row, error = LabelService.update(label_id, user_id, data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row)


@bp.route("/labels/<int:label_id>", methods=["DELETE"])
def delete_label(label_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = LabelService.delete(label_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Label deleted"})


@bp.route("/transactions/<int:tx_id>/labels", methods=["GET"])
def get_transaction_labels(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    labels = LabelService.get_transaction_labels(tx_id)
    return jsonify(labels)


@bp.route("/transactions/<int:tx_id>/labels", methods=["PUT"])
def set_transaction_labels(tx_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    label_ids = data.get("label_ids", [])
    if not isinstance(label_ids, list):
        return jsonify({"error": "label_ids must be a list"}), 400
    ok, error = LabelService.set_transaction_labels(tx_id, label_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Labels updated"})


@bp.route("/sources/<int:source_id>/labels", methods=["GET"])
def get_source_labels(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    labels = LabelService.get_source_labels(source_id)
    return jsonify(labels)


@bp.route("/sources/<int:source_id>/labels", methods=["PUT"])
def set_source_labels(source_id):
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    label_ids = data.get("label_ids", [])
    if not isinstance(label_ids, list):
        return jsonify({"error": "label_ids must be a list"}), 400
    ok, error = LabelService.set_source_labels(source_id, label_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Labels updated"})
