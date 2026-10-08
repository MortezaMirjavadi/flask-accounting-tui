"""Wallet routes - multi-wallet management, sharing, and multi-currency support."""

import math
import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import get_user_id_from_request, row_to_dict, gregorian_to_jalali
from app.utils.permissions import get_wallet_role, has_wallet_access, require_wallet_access, ROLE_HIERARCHY
from app.utils.pagination import parse_pagination, paginated_query
from app.utils.currency import (
    SUPPORTED_CURRENCIES, get_exchange_rate, convert_amount,
    get_user_preferred_currency, validate_currency,
)
from app.utils.activity import (
    log_wallet_activity, ACTION_MEMBER_ADDED, ACTION_MEMBER_REMOVED,
    ACTION_MEMBER_ROLE_CHANGED, ACTION_SETTINGS_CHANGED,
    ACTION_INVITATION_SENT, ACTION_INVITATION_ACCEPTED, ACTION_INVITATION_REJECTED,
    ACTION_ACCOUNT_CREATED, ACTION_ACCOUNT_UPDATED, ACTION_ACCOUNT_DELETED,
)
from database import get_connection, release_connection

bp = Blueprint('wallets', __name__)

VALID_VARIANTS = ('family', 'team', 'travel', 'business', 'savings')
VALID_ACCOUNT_TYPES = ('cash', 'bank', 'card', 'savings', 'wallet', 'other')


# ── Wallet CRUD ──────────────────────────────────────────────────────

@bp.route("", methods=["GET"])
def list_wallets():
    """List all wallets the user has access to (owned + shared) with pagination.
    ---
    tags:
      - Wallets
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
        description: Paginated list of wallets
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        join_clause = (
            " FROM wallets w"
            " LEFT JOIN wallet_members wm ON wm.wallet_id = w.id AND wm.user_id = %s"
        )
        where_clause = (
            " WHERE w.deleted_at IS NULL"
            " AND (w.user_id = %s OR wm.user_id IS NOT NULL)"
        )
        params = [user_id]

        count_params = [user_id] + params

        count_sql = "SELECT COUNT(DISTINCT w.id) as total" + join_clause + where_clause
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()["total"]

        data_sql = (
            "SELECT w.*, wm.role,"
            " (SELECT COUNT(*) FROM wallet_members WHERE wallet_id = w.id) AS member_count,"
            " (SELECT COUNT(*) FROM accounts WHERE wallet_id = w.id AND deleted_at IS NULL) AS account_count,"
            " (SELECT COALESCE(SUM(a.amount), 0) FROM accounts a WHERE a.wallet_id = w.id AND a.deleted_at IS NULL) AS total_balance"
            + join_clause + where_clause + " ORDER BY w.user_id = %s DESC, w.name"
        )
        data_params = [user_id] + params + [user_id]
        offset = (page - 1) * per_page
        cursor.execute(data_sql + " LIMIT %s OFFSET %s", data_params + [per_page, offset])
        rows = cursor.fetchall()

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "items": [row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
def create_wallet():
    """Create a new wallet. Creator becomes owner.
    ---
    tags:
      - Wallets
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            currency:
              type: string
              default: IRR
            wallet_type:
              type: string
              enum: [personal, shared]
              default: personal
            icon:
              type: string
            description:
              type: string
            variant:
              type: string
              enum: [family, team, travel, business, savings]
            account_type:
              type: string
              enum: [cash, bank, card, savings, wallet, other]
              default: cash
            amount:
              type: number
              default: 0
            bank_type:
              type: string
              default: cash
    responses:
      201:
        description: Wallet created successfully
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "نام کیف پول الزامی است"}), 400

    currency = data.get("currency", "IRR")
    wallet_type = data.get("wallet_type", "personal")
    icon = data.get("icon")
    description = data.get("description")
    variant = data.get("variant")
    account_type = data.get("account_type", "cash")
    initial_amount = float(data.get("amount", 0))
    bank_type = data.get("bank_type", "cash")

    if not validate_currency(currency):
        return jsonify({"error": f"ارز '{currency}' پشتیبانی نمی‌شود. ارزهای مجاز: {', '.join(SUPPORTED_CURRENCIES)}"}), 400

    if wallet_type not in ('personal', 'shared'):
        return jsonify({"error": "نوع کیف پول باید personal یا shared باشد"}), 400

    if variant is not None and variant not in VALID_VARIANTS:
        return jsonify({"error": f"نوع کیف پول باید یکی از {', '.join(VALID_VARIANTS)} باشد"}), 400

    if account_type not in VALID_ACCOUNT_TYPES:
        account_type = "cash"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO wallets (user_id, name, currency, wallet_type, icon, description, variant)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (user_id, name, currency, wallet_type, icon, description, variant),
        )
        new_id = cursor.fetchone()['id']

        # Creator is automatically the owner
        cursor.execute(
            "INSERT INTO wallet_members (wallet_id, user_id, role) VALUES (%s, %s, 'owner')",
            (new_id, user_id)
        )

        # Auto-create default account "پول نقد" (balances live on accounts, not wallets)
        cursor.execute(
            """
            INSERT INTO accounts (wallet_id, name, account_type, bank_type, amount, is_default)
            VALUES (%s, %s, %s, %s, %s, TRUE) RETURNING id
            """,
            (new_id, "پول نقد", account_type, bank_type, initial_amount)
        )
        account_id = cursor.fetchone()['id']

        # Seed default categories for new users (only if user has zero categories)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM categories WHERE user_id = %s AND deleted_at IS NULL",
            (user_id,)
        )
        if cursor.fetchone()["cnt"] == 0:
            default_categories = [
                ("حقوق", "income"), ("درآمد", "income"), ("هدیه", "income"),
                ("خوراک", "cost"), ("حمل و نقل", "cost"), ("پوشاک", "cost"),
                ("بهداشت و درمان", "cost"), ("سرگرمی", "cost"), ("قبوض", "cost"),
                ("آموزش", "cost"), ("هدایا", "cost"),
            ]
            for cat_name, cat_type in default_categories:
                cursor.execute(
                    "INSERT INTO categories (user_id, name, type) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, cat_name, cat_type)
                )

        conn.commit()
        return jsonify({"id": new_id, "name": name,
                        "currency": currency, "wallet_type": wallet_type, "variant": variant,
                        "default_account_id": account_id}), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"error": "کیف پولی با این نام قبلاً ایجاد شده است"}), 400
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>", methods=["GET"])
def get_wallet(wallet_id):
    """Get wallet details with balance and member info.
    ---
    tags:
      - Wallets
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
        description: Wallet details with accounts and balance
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute("SELECT * FROM wallets WHERE id = %s AND deleted_at IS NULL", (wallet_id,))
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        result = row_to_dict(wallet)
        result['role'] = get_wallet_role(cursor, wallet_id, user_id)

        # Get accounts for this wallet
        cursor.execute(
            "SELECT * FROM accounts WHERE wallet_id = %s AND deleted_at IS NULL ORDER BY sort_order, id",
            (wallet_id,)
        )
        accounts = cursor.fetchall()
        result['accounts'] = [row_to_dict(a) for a in accounts]
        result['account_count'] = len(accounts)

        # Total balance across all accounts (balances live on accounts, not wallets)
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) as total_balance FROM accounts WHERE wallet_id = %s AND deleted_at IS NULL",
            (wallet_id,)
        )
        result['total_balance'] = float(cursor.fetchone()['total_balance'])

        # Get member count for shared wallets
        if wallet['wallet_type'] == 'shared':
            cursor.execute(
                "SELECT COUNT(*) as count FROM wallet_members WHERE wallet_id = %s",
                (wallet_id,)
            )
            result['member_count'] = cursor.fetchone()['count']

        return jsonify(result)
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>", methods=["PUT"])
def update_wallet(wallet_id):
    """Update wallet settings. Owner only.
    ---
    tags:
      - Wallets
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
            currency:
              type: string
            wallet_type:
              type: string
              enum: [personal, shared]
            icon:
              type: string
            description:
              type: string
            variant:
              type: string
              enum: [family, team, travel, business, savings]
    responses:
      200:
        description: Wallet updated successfully
      400:
        description: Validation error
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        cursor.execute("SELECT * FROM wallets WHERE id = %s AND deleted_at IS NULL", (wallet_id,))
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        name = data.get("name", wallet['name']).strip()
        currency = data.get("currency", wallet['currency'])
        wallet_type = data.get("wallet_type", wallet['wallet_type'])
        icon = data.get("icon", wallet['icon'])
        description = data.get("description", wallet['description'])
        variant = data.get("variant", wallet.get('variant'))

        if not name:
            return jsonify({"error": "نام کیف پول الزامی است"}), 400
        if not validate_currency(currency):
            return jsonify({"error": f"ارز '{currency}' پشتیبانی نمی‌شود"}), 400
        if wallet_type not in ('personal', 'shared'):
            return jsonify({"error": "نوع کیف پول باید personal یا shared باشد"}), 400
        if variant is not None and variant not in VALID_VARIANTS:
            return jsonify({"error": f"نوع کیف پول باید یکی از {', '.join(VALID_VARIANTS)} باشد"}), 400

        cursor.execute(
            """
            UPDATE wallets SET name = %s, currency = %s,
                   wallet_type = %s, icon = %s, description = %s, variant = %s
            WHERE id = %s AND user_id = %s
            """,
            (name, currency, wallet_type, icon, description, variant, wallet_id, user_id),
        )

        # Log activity for shared wallets
        if wallet['wallet_type'] == 'shared':
            log_wallet_activity(cursor, wallet_id, user_id, ACTION_SETTINGS_CHANGED,
                                details={"fields": list(data.keys())})

        conn.commit()
        return jsonify({"id": wallet_id, "name": name,
                        "currency": currency, "wallet_type": wallet_type})
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"error": "کیف پولی با این نام قبلاً ایجاد شده است"}), 400
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>", methods=["DELETE"])
def delete_wallet(wallet_id):
    """Soft-delete wallet. Owner only.
    ---
    tags:
      - Wallets
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
        description: Wallet deleted successfully
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        cursor.execute(
            "UPDATE wallets SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (wallet_id, user_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        conn.commit()
        return jsonify({"message": "کیف پول حذف شد"})
    finally:
        cursor.close()
        release_connection(conn)


# ── Wallet Balance & Transfers ───────────────────────────────────────

@bp.route("/<int:wallet_id>/balance", methods=["GET"])
def wallet_balance(wallet_id):
    """Get wallet balance breakdown.
    ---
    tags:
      - Wallets
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
        description: Wallet balance with per-account breakdown
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT id, name, currency FROM wallets WHERE id = %s AND deleted_at IS NULL",
            (wallet_id,)
        )
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        # Account-level balances (balances live on accounts, not wallets)
        cursor.execute(
            """
            SELECT id, name, account_type, amount
            FROM accounts WHERE wallet_id = %s AND deleted_at IS NULL ORDER BY sort_order, id
            """,
            (wallet_id,),
        )
        accounts = cursor.fetchall()
        total_balance = sum(float(a['amount']) for a in accounts)

        # Transaction summary for income/cost
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.wallet_id = %s AND t.deleted_at IS NULL
            """,
            (wallet_id,),
        )
        row = cursor.fetchone()

        total_income = float(row["total_income"]) if row["total_income"] else 0
        total_cost = float(row["total_cost"]) if row["total_cost"] else 0

        return jsonify({
            "wallet_id": wallet_id,
            "wallet_name": wallet['name'],
            "currency": wallet['currency'],
            "total_balance": total_balance,
            "total_income": total_income,
            "total_cost": total_cost,
            "balance": total_income - total_cost,
            "accounts": [{"id": a['id'], "name": a['name'], "account_type": a['account_type'],
                          "amount": float(a['amount'])} for a in accounts],
        })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/transfers", methods=["GET"])
def wallet_transfers(wallet_id):
    """Get transfers involving this wallet with pagination.
    ---
    tags:
      - Wallets
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
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
        description: Paginated list of wallet transfers
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT id, name, currency FROM wallets WHERE id = %s AND deleted_at IS NULL",
            (wallet_id,)
        )
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        where_clause = (
            " WHERE t.user_id = %s AND t.deleted_at IS NULL"
            " AND (t.from_wallet_id = %s OR t.to_wallet_id = %s)"
        )
        params = [user_id, wallet_id, wallet_id]

        join_clause = (
            " FROM transfers t"
            " LEFT JOIN wallets fw ON t.from_wallet_id = fw.id"
            " LEFT JOIN wallets tw ON t.to_wallet_id = tw.id"
        )

        count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        data_sql = (
            "SELECT t.id, t.date, t.amount, t.notes,"
            " t.from_wallet_id, t.to_wallet_id,"
            " fw.name AS from_wallet_name, fw.currency AS from_wallet_currency,"
            " tw.name AS to_wallet_name, tw.currency AS to_wallet_currency,"
            " CASE WHEN t.to_wallet_id = %s THEN 'in' ELSE 'out' END AS direction"
            + join_clause + where_clause + " ORDER BY t.date DESC, t.id DESC"
            + " LIMIT %s OFFSET %s"
        )
        cursor.execute(data_sql, [wallet_id] + params + [per_page, offset])
        rows = cursor.fetchall()

        records = []
        total_in = 0
        total_out = 0
        for row in rows:
            record = row_to_dict(row)
            record["date"] = gregorian_to_jalali(record["date"])
            record["amount"] = float(record["amount"]) if record["amount"] else 0
            if record.get("direction") == "in":
                total_in += record.get("amount", 0)
            else:
                total_out += record.get("amount", 0)
            records.append(record)

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "wallet_id": wallet_id,
            "wallet_name": wallet['name'],
            "currency": wallet['currency'],
            "summary": {
                "total_transfer_in": total_in,
                "total_transfer_out": total_out,
                "net_transfer": total_in - total_out,
            },
            "items": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)


# ── Members Management ───────────────────────────────────────────────

@bp.route("/<int:wallet_id>/members", methods=["GET"])
def list_members(wallet_id):
    """List all members of a shared wallet with pagination.
    ---
    tags:
      - Wallet Members
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
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
        description: Paginated list of wallet members
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        count_sql = "SELECT COUNT(*) as total FROM wallet_members WHERE wallet_id = %s"
        cursor.execute(count_sql, (wallet_id,))
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT wm.id, wm.wallet_id, wm.user_id, wm.role, wm.joined_at,
                   u.username, u.display_name
            FROM wallet_members wm
            JOIN users u ON u.id = wm.user_id
            WHERE wm.wallet_id = %s
            ORDER BY wm.role = 'owner' DESC, wm.joined_at
            LIMIT %s OFFSET %s
            """,
            (wallet_id, per_page, offset)
        )
        rows = cursor.fetchall()

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "items": [row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/invite", methods=["POST"])
def invite_member(wallet_id):
    """Invite a user to a shared wallet. Owner only.
    ---
    tags:
      - Wallet Invitations
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          required:
            - username
          properties:
            username:
              type: string
            role:
              type: string
              enum: [editor, viewer]
              default: viewer
    responses:
      201:
        description: Invitation sent successfully
      400:
        description: Validation error
      404:
        description: Wallet or user not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    role = data.get("role", "viewer")

    if not username:
        return jsonify({"error": "نام کاربری الزامی است"}), 400
    if role not in ('editor', 'viewer'):
        return jsonify({"error": "نقش باید editor یا viewer باشد"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        # Check wallet is shared
        cursor.execute("SELECT wallet_type FROM wallets WHERE id = %s AND deleted_at IS NULL", (wallet_id,))
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        # Find invitee
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        invitee = cursor.fetchone()
        if invitee is None:
            return jsonify({"error": f"کاربر '{username}' یافت نشد"}), 404

        invitee_id = invitee['id']
        if invitee_id == user_id:
            return jsonify({"error": "نمی‌توانید خودتان را دعوت کنید"}), 400

        # Check if already a member
        cursor.execute(
            "SELECT id FROM wallet_members WHERE wallet_id = %s AND user_id = %s",
            (wallet_id, invitee_id)
        )
        if cursor.fetchone():
            return jsonify({"error": f"'{username}' قبلاً عضو این کیف پول است"}), 400

        # Check for existing pending invitation
        cursor.execute(
            "SELECT id FROM wallet_invitations WHERE wallet_id = %s AND invitee_id = %s AND status = 'pending'",
            (wallet_id, invitee_id)
        )
        if cursor.fetchone():
            return jsonify({"error": f"دعوت‌نامه برای '{username}' قبلاً ارسال شده است"}), 400

        # Auto-upgrade to shared if personal
        if wallet['wallet_type'] == 'personal':
            cursor.execute("UPDATE wallets SET wallet_type = 'shared' WHERE id = %s", (wallet_id,))

        cursor.execute(
            """
            INSERT INTO wallet_invitations (wallet_id, inviter_id, invitee_id, role)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (wallet_id, user_id, invitee_id, role)
        )
        invite_id = cursor.fetchone()['id']

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_INVITATION_SENT,
                            details={"invitee": username, "role": role})

        conn.commit()
        return jsonify({"id": invite_id, "message": f"دعوت‌نامه برای '{username}' ارسال شد"}), 201
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/members/<int:member_user_id>/remove", methods=["POST"])
def remove_member(wallet_id, member_user_id):
    """Remove a member from a shared wallet. Owner only.
    ---
    tags:
      - Wallet Members
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: member_user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Member removed successfully
      400:
        description: Cannot remove yourself
      404:
        description: Member not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        if member_user_id == user_id:
            return jsonify({"error": "نمی‌توانید خودتان را حذف کنید"}), 400

        cursor.execute(
            "DELETE FROM wallet_members WHERE wallet_id = %s AND user_id = %s AND role != 'owner'",
            (wallet_id, member_user_id)
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "عضو یافت نشد یا نمی‌توان مالک را حذف کرد"}), 404

        # Get removed user's name for activity log
        cursor.execute("SELECT username FROM users WHERE id = %s", (member_user_id,))
        removed_user = cursor.fetchone()
        username = removed_user['username'] if removed_user else str(member_user_id)

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_MEMBER_REMOVED,
                            details={"removed_user": username})

        conn.commit()
        return jsonify({"message": "عضو حذف شد"})
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/members/<int:member_user_id>/role", methods=["PUT"])
def update_member_role(wallet_id, member_user_id):
    """Change a member's role. Owner only.
    ---
    tags:
      - Wallet Members
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: member_user_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          required:
            - role
          properties:
            role:
              type: string
              enum: [editor, viewer]
    responses:
      200:
        description: Member role updated successfully
      400:
        description: Validation error
      404:
        description: Member not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    new_role = data.get("role")
    if new_role not in ('editor', 'viewer'):
        return jsonify({"error": "نقش باید editor یا viewer باشد"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        if member_user_id == user_id:
            return jsonify({"error": "نمی‌توانید نقش خودتان را تغییر دهید"}), 400

        cursor.execute(
            "UPDATE wallet_members SET role = %s WHERE wallet_id = %s AND user_id = %s AND role != 'owner'",
            (new_role, wallet_id, member_user_id)
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "عضو یافت نشد یا نمی‌توان نقش مالک را تغییر داد"}), 404

        cursor.execute("SELECT username FROM users WHERE id = %s", (member_user_id,))
        member_user = cursor.fetchone()
        username = member_user['username'] if member_user else str(member_user_id)

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_MEMBER_ROLE_CHANGED,
                            details={"member": username, "new_role": new_role})

        conn.commit()
        return jsonify({"message": "نقش عضو تغییر کرد"})
    finally:
        cursor.close()
        release_connection(conn)


# ── Invitations ──────────────────────────────────────────────────────

@bp.route("/invitations", methods=["GET"])
def list_invitations():
    """List pending invitations for the current user with pagination.
    ---
    tags:
      - Wallet Invitations
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
        description: Paginated list of pending invitations
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        count_sql = (
            "SELECT COUNT(*) as total FROM wallet_invitations wi"
            " JOIN wallets w ON w.id = wi.wallet_id"
            " WHERE wi.invitee_id = %s AND wi.status = 'pending' AND w.deleted_at IS NULL"
        )
        cursor.execute(count_sql, (user_id,))
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT wi.id, wi.wallet_id, wi.role, wi.status, wi.created_at,
                   w.name AS wallet_name, w.currency,
                   u.username AS inviter_name, u.display_name AS inviter_display_name
            FROM wallet_invitations wi
            JOIN wallets w ON w.id = wi.wallet_id
            JOIN users u ON u.id = wi.inviter_id
            WHERE wi.invitee_id = %s AND wi.status = 'pending' AND w.deleted_at IS NULL
            ORDER BY wi.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, per_page, offset)
        )
        rows = cursor.fetchall()

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "items": [row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/invitations/<int:invitation_id>/accept", methods=["POST"])
def accept_invitation(invitation_id):
    """Accept a wallet invitation.
    ---
    tags:
      - Wallet Invitations
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: invitation_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Invitation accepted successfully
      404:
        description: Invitation not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT wi.*, w.name AS wallet_name
            FROM wallet_invitations wi
            JOIN wallets w ON w.id = wi.wallet_id
            WHERE wi.id = %s AND wi.invitee_id = %s AND wi.status = 'pending'
            """,
            (invitation_id, user_id)
        )
        invitation = cursor.fetchone()
        if invitation is None:
            return jsonify({"error": "دعوت‌نامه یافت نشد"}), 404

        # Add as member
        cursor.execute(
            """
            INSERT INTO wallet_members (wallet_id, user_id, role, invited_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (wallet_id, user_id) DO UPDATE SET role = EXCLUDED.role
            """,
            (invitation['wallet_id'], user_id, invitation['role'], invitation['inviter_id'])
        )

        # Update invitation status
        cursor.execute(
            "UPDATE wallet_invitations SET status = 'accepted' WHERE id = %s",
            (invitation_id,)
        )

        log_wallet_activity(cursor, invitation['wallet_id'], user_id, ACTION_INVITATION_ACCEPTED)

        conn.commit()
        return jsonify({"message": f"دعوت‌نامه کیف پول '{invitation['wallet_name']}' پذیرفته شد"})
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/invitations/<int:invitation_id>/reject", methods=["POST"])
def reject_invitation(invitation_id):
    """Reject a wallet invitation.
    ---
    tags:
      - Wallet Invitations
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: invitation_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Invitation rejected successfully
      404:
        description: Invitation not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE wallet_invitations SET status = 'rejected'
            WHERE id = %s AND invitee_id = %s AND status = 'pending'
            RETURNING wallet_id
            """,
            (invitation_id, user_id)
        )
        result = cursor.fetchone()
        if result is None:
            return jsonify({"error": "دعوت‌نامه یافت نشد"}), 404

        log_wallet_activity(cursor, result['wallet_id'], user_id, ACTION_INVITATION_REJECTED)

        conn.commit()
        return jsonify({"message": "دعوت‌نامه رد شد"})
    finally:
        cursor.close()
        release_connection(conn)


# ── Activity Log ─────────────────────────────────────────────────────

@bp.route("/<int:wallet_id>/activity", methods=["GET"])
def wallet_activity(wallet_id):
    """Get activity feed for a shared wallet with pagination.
    ---
    tags:
      - Wallet Activity
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
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
        description: Paginated wallet activity log
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT COUNT(*) as total FROM wallet_activity_log WHERE wallet_id = %s",
            (wallet_id,)
        )
        total = cursor.fetchone()['total']

        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT wal.id, wal.wallet_id, wal.user_id, wal.action,
                   wal.entity_type, wal.entity_id, wal.details, wal.created_at,
                   u.username, u.display_name
            FROM wallet_activity_log wal
            JOIN users u ON u.id = wal.user_id
            WHERE wal.wallet_id = %s
            ORDER BY wal.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (wallet_id, per_page, offset)
        )
        rows = cursor.fetchall()

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0
        return jsonify({
            "wallet_id": wallet_id,
            "items": [row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    finally:
        cursor.close()
        release_connection(conn)


# ── Per-Wallet Summary ──────────────────────────────────────────────

@bp.route("/<int:wallet_id>/summary", methods=["GET"])
def wallet_summary(wallet_id):
    """Get financial summary for a specific wallet.
    ---
    tags:
      - Wallets
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
        description: Wallet financial summary including balance, income, cost, and transfers
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT id, name, currency FROM wallets WHERE id = %s AND deleted_at IS NULL",
            (wallet_id,)
        )
        wallet = cursor.fetchone()
        if wallet is None:
            return jsonify({"error": "کیف پول یافت نشد"}), 404

        # Total balance from accounts (balances live on accounts, not wallets)
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total_balance FROM accounts WHERE wallet_id = %s AND deleted_at IS NULL",
            (wallet_id,)
        )
        total_balance = float(cursor.fetchone()['total_balance'])

        # Transaction summary
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN c.type = 'cost' THEN t.amount ELSE 0 END), 0) AS total_cost,
                COUNT(t.id) AS transaction_count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.wallet_id = %s AND t.user_id = %s AND t.deleted_at IS NULL
            """,
            (wallet_id, user_id)
        )
        tx_summary = cursor.fetchone()

        total_income = float(tx_summary['total_income'])
        total_cost = float(tx_summary['total_cost'])

        # Transfer summary
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN to_wallet_id = %s THEN amount ELSE 0 END), 0) AS transfer_in,
                COALESCE(SUM(CASE WHEN from_wallet_id = %s THEN amount ELSE 0 END), 0) AS transfer_out
            FROM transfers
            WHERE user_id = %s AND deleted_at IS NULL
              AND (from_wallet_id = %s OR to_wallet_id = %s)
            """,
            (wallet_id, wallet_id, user_id, wallet_id, wallet_id)
        )
        transfer_summary = cursor.fetchone()

        return jsonify({
            "wallet_id": wallet_id,
            "wallet_name": wallet['name'],
            "currency": wallet['currency'],
            "total_balance": total_balance,
            "total_income": total_income,
            "total_cost": total_cost,
            "net_income": total_income - total_cost,
            "balance": total_balance + total_income - total_cost,
            "transaction_count": int(tx_summary['transaction_count']),
            "transfer_in": float(transfer_summary['transfer_in']),
            "transfer_out": float(transfer_summary['transfer_out']),
        })
    finally:
        cursor.close()
        release_connection(conn)


# ── Consolidated Balance ────────────────────────────────────────────

@bp.route("/consolidated", methods=["GET"])
def consolidated_balance():
    """Get consolidated balance across all wallets in user's preferred currency.
    ---
    tags:
      - Wallets
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
    responses:
      200:
        description: Consolidated balance with per-wallet breakdown and currency conversion
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        preferred_currency = get_user_preferred_currency(cursor, user_id)

        # Get all accessible wallets with account-level balance
        cursor.execute(
            """
            SELECT w.id, w.name, w.currency, w.wallet_type, w.variant,
                   wm.role,
                   COALESCE(a_total.balance, 0) AS account_balance
            FROM wallets w
            LEFT JOIN wallet_members wm ON wm.wallet_id = w.id AND wm.user_id = %s
            LEFT JOIN (
                SELECT wallet_id, COALESCE(SUM(amount), 0) AS balance
                FROM accounts WHERE deleted_at IS NULL GROUP BY wallet_id
            ) a_total ON a_total.wallet_id = w.id
            WHERE w.deleted_at IS NULL
              AND (w.user_id = %s OR wm.user_id IS NOT NULL)
            """,
            (user_id, user_id)
        )
        wallets = cursor.fetchall()

        wallet_summaries = []
        total_converted = 0

        for wallet in wallets:
            balance = float(wallet['account_balance'])

            # Convert to preferred currency
            rate = get_exchange_rate(cursor, user_id, wallet['currency'], preferred_currency)
            if rate is not None:
                converted = float(convert_amount(balance, wallet['currency'], preferred_currency, rate))
            else:
                converted = None

            wallet_summaries.append({
                "wallet_id": wallet['id'],
                "wallet_name": wallet['name'],
                "currency": wallet['currency'],
                "wallet_type": wallet['wallet_type'],
                "variant": wallet.get('variant'),
                "role": wallet['role'] if wallet['role'] else 'owner',
                "balance": balance,
                "converted_balance": converted,
                "preferred_currency": preferred_currency,
            })

            if converted is not None:
                total_converted += converted

        return jsonify({
            "preferred_currency": preferred_currency,
            "total_converted_balance": total_converted,
            "wallet_count": len(wallet_summaries),
            "wallets": wallet_summaries,
        })
    finally:
        cursor.close()
        release_connection(conn)


# ── Account CRUD ────────────────────────────────────────────────────

@bp.route("/<int:wallet_id>/accounts", methods=["GET"])
def list_accounts(wallet_id):
    """List all accounts in a wallet.
    ---
    tags:
      - Wallet Accounts
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
        description: List of accounts in the wallet
      404:
        description: Wallet not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT * FROM accounts WHERE wallet_id = %s AND deleted_at IS NULL ORDER BY sort_order, id",
            (wallet_id,)
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(r) for r in rows])
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/accounts", methods=["POST"])
def create_account(wallet_id):
    """Add an account to a wallet. Editor+ required.
    ---
    tags:
      - Wallet Accounts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            account_type:
              type: string
              enum: [cash, bank, card, savings, wallet, other]
              default: cash
            bank_type:
              type: string
              default: cash
            amount:
              type: number
              default: 0
            icon:
              type: string
            description:
              type: string
            sort_order:
              type: integer
              default: 0
    responses:
      201:
        description: Account created successfully
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "نام حساب الزامی است"}), 400

    account_type = data.get("account_type", "cash")
    bank_type = data.get("bank_type", "cash")
    amount = float(data.get("amount", 0))
    icon = data.get("icon")
    description = data.get("description")
    sort_order = data.get("sort_order", 0)

    if account_type not in VALID_ACCOUNT_TYPES:
        return jsonify({"error": f"نوع حساب باید یکی از {', '.join(VALID_ACCOUNT_TYPES)} باشد"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'editor')
        if access_err:
            return access_err

        cursor.execute(
            """
            INSERT INTO accounts (wallet_id, name, account_type, bank_type, amount, icon, description, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (wallet_id, name, account_type, bank_type, amount, icon, description, sort_order),
        )
        new_id = cursor.fetchone()['id']

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_ACCOUNT_CREATED,
                            entity_type='account', entity_id=new_id,
                            details={"name": name, "account_type": account_type})

        conn.commit()
        return jsonify({"id": new_id, "wallet_id": wallet_id, "name": name,
                        "account_type": account_type, "amount": amount}), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"error": "حسابی با این نام در این کیف پول قبلاً وجود دارد"}), 400
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/accounts/<int:account_id>", methods=["GET"])
def get_account(wallet_id, account_id):
    """Get single account details.
    ---
    tags:
      - Wallet Accounts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: account_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Account details
      404:
        description: Account not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'viewer')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT * FROM accounts WHERE id = %s AND wallet_id = %s AND deleted_at IS NULL",
            (account_id, wallet_id)
        )
        account = cursor.fetchone()
        if account is None:
            return jsonify({"error": "حساب یافت نشد"}), 404

        return jsonify(row_to_dict(account))
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/accounts/<int:account_id>", methods=["PUT"])
def update_account(wallet_id, account_id):
    """Update an account. Editor+ required.
    ---
    tags:
      - Wallet Accounts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: account_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
            account_type:
              type: string
              enum: [cash, bank, card, savings, wallet, other]
            bank_type:
              type: string
            amount:
              type: number
            icon:
              type: string
            description:
              type: string
            sort_order:
              type: integer
    responses:
      200:
        description: Account updated successfully
      400:
        description: Validation error
      404:
        description: Account not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'editor')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT * FROM accounts WHERE id = %s AND wallet_id = %s AND deleted_at IS NULL",
            (account_id, wallet_id)
        )
        account = cursor.fetchone()
        if account is None:
            return jsonify({"error": "حساب یافت نشد"}), 404

        name = data.get("name", account['name']).strip()
        account_type = data.get("account_type", account['account_type'])
        bank_type = data.get("bank_type", account['bank_type'])
        amount = data.get("amount", account['amount'])
        icon = data.get("icon", account['icon'])
        description = data.get("description", account['description'])
        sort_order = data.get("sort_order", account['sort_order'])

        if not name:
            return jsonify({"error": "نام حساب الزامی است"}), 400
        if account_type not in VALID_ACCOUNT_TYPES:
            return jsonify({"error": f"نوع حساب نامعتبر"}), 400
        try:
            amount = float(amount)
            if amount < 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"error": "مبلغ نامعتبر است"}), 400

        cursor.execute(
            """
            UPDATE accounts SET name = %s, account_type = %s, bank_type = %s,
                   amount = %s, icon = %s, description = %s, sort_order = %s
            WHERE id = %s AND wallet_id = %s
            """,
            (name, account_type, bank_type, amount, icon, description, sort_order, account_id, wallet_id),
        )

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_ACCOUNT_UPDATED,
                            entity_type='account', entity_id=account_id,
                            details={"name": name})

        conn.commit()
        return jsonify({"id": account_id, "wallet_id": wallet_id, "name": name,
                        "account_type": account_type, "amount": amount})
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"error": "حسابی با این نام در این کیف پول قبلاً وجود دارد"}), 400
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("/<int:wallet_id>/accounts/<int:account_id>", methods=["DELETE"])
def delete_account(wallet_id, account_id):
    """Soft-delete an account. Owner only. Cannot delete default account.
    ---
    tags:
      - Wallet Accounts
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: wallet_id
        in: path
        type: integer
        required: true
      - name: account_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Account deleted successfully
      400:
        description: Cannot delete default account
      404:
        description: Account not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()

    try:
        access_err = require_wallet_access(cursor, wallet_id, user_id, 'owner')
        if access_err:
            return access_err

        cursor.execute(
            "SELECT * FROM accounts WHERE id = %s AND wallet_id = %s AND deleted_at IS NULL",
            (account_id, wallet_id)
        )
        account = cursor.fetchone()
        if account is None:
            return jsonify({"error": "حساب یافت نشد"}), 404

        if account['is_default']:
            return jsonify({"error": "نمی‌توان حساب پیش‌فرض را حذف کرد"}), 400

        cursor.execute(
            "UPDATE accounts SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
            (account_id,),
        )

        log_wallet_activity(cursor, wallet_id, user_id, ACTION_ACCOUNT_DELETED,
                            entity_type='account', entity_id=account_id,
                            details={"name": account['name']})

        conn.commit()
        return jsonify({"message": "حساب حذف شد"})
    finally:
        cursor.close()
        release_connection(conn)
