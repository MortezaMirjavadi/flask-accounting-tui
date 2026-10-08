"""Contact, Tag, and Label management routes."""

from flask import Blueprint, request, jsonify

from app.utils.helpers import get_user_id_from_request
from app.utils.pagination import parse_pagination
from services.metadata_service import ContactService, TagService, LabelService

bp = Blueprint('metadata', __name__)


# ── Contacts ────────────────────────────────────────────────────────

@bp.route("/contacts", methods=["GET"])
def list_contacts():
    """List contacts.
    ---
    tags:
      - Contacts
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
      - name: q
        in: query
        type: string
        description: Search query for contact name
    responses:
      200:
        description: Paginated list of contacts
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    page, per_page = parse_pagination()
    search = request.args.get("q", "").strip() or None
    result = ContactService.list_contacts(user_id, search=search, page=page, per_page=per_page)
    return jsonify(result)


@bp.route("/contacts", methods=["POST"])
def create_contact():
    """Create a new contact.
    ---
    tags:
      - Contacts
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
            name:
              type: string
            phone:
              type: string
            email:
              type: string
            address:
              type: string
            notes:
              type: string
    responses:
      201:
        description: Contact created
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "نام الزامی است"}), 400

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
    """Get a contact by ID.
    ---
    tags:
      - Contacts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: contact_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Contact details
      404:
        description: Contact not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = ContactService.get_contact(contact_id, user_id)
    if not row:
        return jsonify({"error": "مخاطب یافت نشد"}), 404
    return jsonify(row)


@bp.route("/contacts/<int:contact_id>", methods=["PUT"])
def update_contact(contact_id):
    """Update a contact.
    ---
    tags:
      - Contacts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: contact_id
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
        description: Contact updated
      400:
        description: Validation error
    """
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
    """Delete a contact.
    ---
    tags:
      - Contacts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: contact_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Contact deleted
      400:
        description: Error deleting contact
    """
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
    """List tags.
    ---
    tags:
      - Tags
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
        description: Paginated list of tags
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    page, per_page = parse_pagination()
    result = TagService.list_tags(user_id, page=page, per_page=per_page)
    return jsonify(result)


@bp.route("/tags", methods=["POST"])
def create_tag():
    """Create a new tag.
    ---
    tags:
      - Tags
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
            name:
              type: string
            color:
              type: string
    responses:
      201:
        description: Tag created
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "نام الزامی است"}), 400
    row, error = TagService.create(user_id, {
        "name": name,
        "color": (data.get("color") or "").strip() or None,
    })
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row), 201


@bp.route("/tags/<int:tag_id>", methods=["GET"])
def get_tag(tag_id):
    """Get a tag by ID.
    ---
    tags:
      - Tags
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tag_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Tag details
      404:
        description: Tag not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = TagService.get_tag(tag_id, user_id)
    if not row:
        return jsonify({"error": "برچسب یافت نشد"}), 404
    return jsonify(row)


@bp.route("/tags/<int:tag_id>", methods=["PUT"])
def update_tag(tag_id):
    """Update a tag.
    ---
    tags:
      - Tags
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tag_id
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
        description: Tag updated
      400:
        description: Validation error
    """
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
    """Delete a tag.
    ---
    tags:
      - Tags
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tag_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Tag deleted
      400:
        description: Error deleting tag
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = TagService.delete(tag_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Tag deleted"})


@bp.route("/transactions/<int:tx_id>/tags", methods=["GET"])
def get_transaction_tags(tx_id):
    """Get tags for a transaction.
    ---
    tags:
      - Tags
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of tags for the transaction
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    tags = TagService.get_transaction_tags(tx_id)
    return jsonify(tags)


@bp.route("/transactions/<int:tx_id>/tags", methods=["PUT"])
def set_transaction_tags(tx_id):
    """Set tags for a transaction.
    ---
    tags:
      - Tags
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            tag_ids:
              type: array
              items:
                type: integer
    responses:
      200:
        description: Tags updated
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    tag_ids = data.get("tag_ids", [])
    if not isinstance(tag_ids, list):
        return jsonify({"error": "برچسب باید لیست باشد"}), 400
    ok, error = TagService.set_transaction_tags(tx_id, tag_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Tags updated"})


# ── Labels ──────────────────────────────────────────────────────────

@bp.route("/labels", methods=["GET"])
def list_labels():
    """List labels.
    ---
    tags:
      - Labels
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
        description: Paginated list of labels
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    page, per_page = parse_pagination()
    result = LabelService.list_labels(user_id, page=page, per_page=per_page)
    return jsonify(result)


@bp.route("/labels", methods=["POST"])
def create_label():
    """Create a new label.
    ---
    tags:
      - Labels
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
            name:
              type: string
            color:
              type: string
    responses:
      201:
        description: Label created
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "نام الزامی است"}), 400
    row, error = LabelService.create(user_id, {
        "name": name,
        "color": (data.get("color") or "").strip() or None,
    })
    if error:
        return jsonify({"error": error}), 400
    return jsonify(row), 201


@bp.route("/labels/<int:label_id>", methods=["GET"])
def get_label(label_id):
    """Get a label by ID.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: label_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Label details
      404:
        description: Label not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    row = LabelService.get_label(label_id, user_id)
    if not row:
        return jsonify({"error": "برچسب رنگی یافت نشد"}), 404
    return jsonify(row)


@bp.route("/labels/<int:label_id>", methods=["PUT"])
def update_label(label_id):
    """Update a label.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: label_id
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
        description: Label updated
      400:
        description: Validation error
    """
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
    """Delete a label.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: label_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Label deleted
      400:
        description: Error deleting label
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    ok, error = LabelService.delete(label_id, user_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Label deleted"})


@bp.route("/transactions/<int:tx_id>/labels", methods=["GET"])
def get_transaction_labels(tx_id):
    """Get labels for a transaction.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of labels for the transaction
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    labels = LabelService.get_transaction_labels(tx_id)
    return jsonify(labels)


@bp.route("/transactions/<int:tx_id>/labels", methods=["PUT"])
def set_transaction_labels(tx_id):
    """Set labels for a transaction.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            label_ids:
              type: array
              items:
                type: integer
    responses:
      200:
        description: Labels updated
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    label_ids = data.get("label_ids", [])
    if not isinstance(label_ids, list):
        return jsonify({"error": "برچسب‌ها باید لیست باشد"}), 400
    ok, error = LabelService.set_transaction_labels(tx_id, label_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Labels updated"})


@bp.route("/sources/<int:source_id>/labels", methods=["GET"])
def get_source_labels(source_id):
    """Get labels for a source/wallet.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of labels for the source
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    labels = LabelService.get_wallet_labels(source_id)
    return jsonify(labels)


@bp.route("/sources/<int:source_id>/labels", methods=["PUT"])
def set_source_labels(source_id):
    """Set labels for a source/wallet.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: source_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            label_ids:
              type: array
              items:
                type: integer
    responses:
      200:
        description: Labels updated
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    label_ids = data.get("label_ids", [])
    if not isinstance(label_ids, list):
        return jsonify({"error": "برچسب‌ها باید لیست باشد"}), 400
    ok, error = LabelService.set_wallet_labels(source_id, label_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Labels updated"})


@bp.route("/wallets/<int:wallet_id>/labels", methods=["GET"])
def get_wallet_labels(wallet_id):
    """Get labels for a wallet.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of labels for the wallet
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    labels = LabelService.get_wallet_labels(wallet_id)
    return jsonify(labels)


@bp.route("/wallets/<int:wallet_id>/labels", methods=["PUT"])
def set_wallet_labels(wallet_id):
    """Set labels for a wallet.
    ---
    tags:
      - Labels
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            label_ids:
              type: array
              items:
                type: integer
    responses:
      200:
        description: Labels updated
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    label_ids = data.get("label_ids", [])
    if not isinstance(label_ids, list):
        return jsonify({"error": "برچسب‌ها باید لیست باشد"}), 400
    ok, error = LabelService.set_wallet_labels(wallet_id, label_ids)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Labels updated"})
