import math
import psycopg2
from flask import Blueprint, request, jsonify
from app.utils.helpers import (
    get_user_id_from_request,
    row_to_dict,
    gregorian_to_jalali,
    jalali_to_gregorian,
)
from app.models import validate_transaction_payload, validate_transaction_items_payload
from app.services.transaction_item_service import TransactionItemService
from services.metadata_service import TagService, LabelService
from app.utils.currency import get_exchange_rate, convert_amount
from app.utils.pagination import parse_pagination, paginated_query
from database import get_connection, release_connection

bp = Blueprint('transactions', __name__)


def _get_category_type(cursor, category_id, user_id):
    cursor.execute(
        "SELECT type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    return row["type"] if row else None


def _get_wallet_amount(cursor, wallet_id, user_id):
    cursor.execute(
        """SELECT COALESCE(SUM(a.amount), 0) AS amount
           FROM wallets w
           LEFT JOIN accounts a ON a.wallet_id = w.id AND a.deleted_at IS NULL
           WHERE w.id = %s AND w.user_id = %s AND w.deleted_at IS NULL
           GROUP BY w.id""",
        (wallet_id, user_id),
    )
    row = cursor.fetchone()
    return row["amount"] if row else None


def _get_account_amount(cursor, account_id):
    """Get account balance. Returns None if not found."""
    cursor.execute(
        "SELECT amount FROM accounts WHERE id = %s AND deleted_at IS NULL",
        (account_id,),
    )
    row = cursor.fetchone()
    return float(row["amount"]) if row else None


def _get_account_currency(cursor, account_id):
    """Get account currency (inherited from wallet). Returns None if not found."""
    cursor.execute(
        """
        SELECT w.currency FROM accounts a
        JOIN wallets w ON w.id = a.wallet_id
        WHERE a.id = %s AND a.deleted_at IS NULL
        """,
        (account_id,),
    )
    row = cursor.fetchone()
    return row["currency"] if row else None


def _get_account_wallet_id(cursor, account_id):
    """Get wallet_id for an account."""
    cursor.execute(
        "SELECT wallet_id FROM accounts WHERE id = %s AND deleted_at IS NULL",
        (account_id,),
    )
    row = cursor.fetchone()
    return row["wallet_id"] if row else None


def _wallet_exists(cursor, wallet_id, user_id):
    cursor.execute(
        "SELECT 1 FROM wallets WHERE id = %s AND deleted_at IS NULL AND (user_id = %s OR EXISTS (SELECT 1 FROM wallet_members WHERE wallet_id = %s AND user_id = %s))",
        (wallet_id, user_id, wallet_id, user_id),
    )
    return cursor.fetchone() is not None


def _adjust_wallet_amount(cursor, wallet_id, user_id, amount, category_type):
    """Legacy: no-op. Wallet balances are derived from account sums."""
    pass


def _adjust_account_amount(cursor, account_id, amount, category_type):
    """Adjust account balance."""
    if account_id is None or category_type not in ("income", "cost"):
        return
    delta = amount if category_type == "income" else -amount
    cursor.execute(
        "UPDATE accounts SET amount = amount + %s WHERE id = %s",
        (delta, account_id),
    )


def _validate_transfer_payload(data):
    date = (data.get("date") or "").strip()
    notes = (data.get("description") or data.get("notes") or "").strip() or None

    if not date:
        raise ValueError("تاریخ الزامی است")

    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ معتبر مثبت الزامی است")

    from_account_id = data.get("from_account_id")
    to_account_id = data.get("to_account_id")

    if from_account_id is None:
        raise ValueError("شناسه حساب مبدا الزامی است")
    if to_account_id is None:
        raise ValueError("شناسه حساب مقصد الزامی است")

    try:
        from_account_id = int(from_account_id)
    except (TypeError, ValueError):
        raise ValueError("شناسه حساب مبدا معتبر الزامی است")
    try:
        to_account_id = int(to_account_id)
    except (TypeError, ValueError):
        raise ValueError("شناسه حساب مقصد معتبر الزامی است")

    if from_account_id == to_account_id:
        raise ValueError("حساب مبدا و مقصد باید متفاوت باشند")

    return {
        "date": jalali_to_gregorian(date),
        "amount": amount,
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "notes": notes,
    }


def _serialize_transaction(payload, tx_id):
    return {
        "id": tx_id,
        "record_type": "transaction",
        "is_transfer": False,
        **payload,
        "date": gregorian_to_jalali(payload["date"]),
    }


def _serialize_transfer(payload, tx_id):
    return {
        "id": tx_id,
        "record_type": "transfer",
        "is_transfer": True,
        **payload,
        "description": payload.get("notes"),
        "date": gregorian_to_jalali(payload["date"]),
    }


def _format_transfer_list_row(row):
    data = row_to_dict(row)
    from_name = data.get("from_account_name") or data.get("from_wallet_name") or "Unknown"
    to_name = data.get("to_account_name") or data.get("to_wallet_name") or "Unknown"
    data["record_type"] = "transfer"
    data["is_transfer"] = True
    data["category_name"] = "Transfer"
    data["source_name"] = f"{from_name} -> {to_name}"
    data["description"] = data.get("notes") or "Transfer between accounts"
    data["date"] = gregorian_to_jalali(data["date"])
    return data


def _get_transaction_row(cursor, tx_id, user_id):
    cursor.execute(
        "SELECT t.*, c.name as category_name, w.name as source_name, "
        "w.wallet_type, w.user_id as wallet_owner_id, "
        "u.username as creator_username, u.display_name as creator_display_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN wallets w ON t.wallet_id = w.id "
        "LEFT JOIN users u ON u.id = t.user_id "
        "WHERE t.id = %s AND t.deleted_at IS NULL"
        " AND ("
        "   (t.wallet_id IS NULL AND t.user_id = %s)"
        "   OR t.wallet_id IN ("
        "     SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
        "     UNION"
        "     SELECT wallet_id FROM wallet_members WHERE user_id = %s"
        "   )"
        " )",
        (tx_id, user_id, user_id, user_id),
    )
    return cursor.fetchone()


def _get_transfer_row(cursor, tx_id, user_id):
    cursor.execute(
        "SELECT t.*, "
        "fa.name as from_account_name, ta.name as to_account_name, "
        "fw.name as from_wallet_name, tw.name as to_wallet_name "
        "FROM transfers t "
        "LEFT JOIN accounts fa ON t.from_account_id = fa.id "
        "LEFT JOIN accounts ta ON t.to_account_id = ta.id "
        "LEFT JOIN wallets fw ON t.from_wallet_id = fw.id "
        "LEFT JOIN wallets tw ON t.to_wallet_id = tw.id "
        "WHERE t.id = %s AND t.deleted_at IS NULL"
        " AND (t.from_wallet_id IN ("
        "   SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
        "   UNION SELECT wallet_id FROM wallet_members WHERE user_id = %s"
        " ) OR t.to_wallet_id IN ("
        "   SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
        "   UNION SELECT wallet_id FROM wallet_members WHERE user_id = %s"
        " ))",
        (tx_id, user_id, user_id, user_id, user_id),
    )
    return cursor.fetchone()


def _can_modify_transaction(cursor, transaction_row, user_id):
    """Check if the user can edit/delete a transaction.

    Returns True if:
    - The wallet is personal and user is the creator
    - The wallet is shared and user is the wallet owner
    - The wallet is shared and user is an editor who created the transaction
    """
    wallet_id = transaction_row.get("wallet_id")
    if wallet_id is None:
        # No wallet — only the creator can modify
        return transaction_row["user_id"] == user_id

    # Check wallet info
    cursor.execute(
        "SELECT user_id, wallet_type FROM wallets WHERE id = %s AND deleted_at IS NULL",
        (wallet_id,)
    )
    wallet = cursor.fetchone()
    if wallet is None:
        return False

    # Personal wallet — only the creator can modify
    if wallet["wallet_type"] == "personal" or wallet["wallet_type"] is None:
        return transaction_row["user_id"] == user_id

    # Shared wallet
    if wallet["user_id"] == user_id:
        # User is the wallet owner — can modify anything
        return True

    # Check user's role in the wallet
    cursor.execute(
        "SELECT role FROM wallet_members WHERE wallet_id = %s AND user_id = %s",
        (wallet_id, user_id)
    )
    member = cursor.fetchone()
    if member is None:
        return False

    if member["role"] == "owner":
        return True
    if member["role"] == "editor":
        # Editor can only modify their own transactions
        return transaction_row["user_id"] == user_id

    # Viewer cannot modify
    return False


def _validate_transaction_business_rules(cursor, user_id, payload, old_transaction=None, old_transfer=None):
    new_type = _get_category_type(cursor, payload["category_id"], user_id)
    if new_type is None:
        return jsonify({"error": "دسته‌بندی یافت نشد"}), None

    new_wallet_id = payload.get("wallet_id")
    if new_wallet_id is not None and not _wallet_exists(cursor, new_wallet_id, user_id):
        return jsonify({"error": "کیف پول یافت نشد"}), None

    # Validate against account balance (balances live on accounts, not wallets)
    account_id = payload.get("account_id")
    if new_type == "cost" and account_id is not None:
        current = _get_account_amount(cursor, account_id)
        if current is None:
            return jsonify({"error": "حساب یافت نشد"}), None

        effective = current
        if old_transaction is not None:
            old_type = _get_category_type(cursor, old_transaction["category_id"], user_id)
            if old_transaction.get("account_id") == account_id and old_type:
                effective += old_transaction["amount"] if old_type == "cost" else -old_transaction["amount"]
        if old_transfer is not None:
            if old_transfer.get("from_account_id") == account_id:
                effective += old_transfer["amount"]
            if old_transfer.get("to_account_id") == account_id:
                effective -= old_transfer["amount"]

        if effective < payload["amount"]:
            return (
                jsonify(
                    {
                        "error": "موجودی حساب کافی نیست",
                        "account_balance": effective,
                        "requested": payload["amount"],
                    }
                ),
                None,
            )

    return None, new_type


def _validate_transfer_business_rules(cursor, user_id, payload, old_transaction=None, old_transfer=None):
    from_account_id = payload.get("from_account_id")
    to_account_id = payload.get("to_account_id")

    if from_account_id is not None:
        current = _get_account_amount(cursor, from_account_id)
        if current is None:
            return jsonify({"error": "حساب مبدا یافت نشد"})

        effective = current
        if old_transaction is not None:
            old_type = _get_category_type(cursor, old_transaction["category_id"], user_id)
            if old_transaction.get("account_id") == from_account_id and old_type:
                effective += old_transaction["amount"] if old_type == "cost" else -old_transaction["amount"]
        if old_transfer is not None:
            if old_transfer.get("from_account_id") == from_account_id:
                effective += old_transfer["amount"]
            if old_transfer.get("to_account_id") == from_account_id:
                effective -= old_transfer["amount"]

        if effective < payload["amount"]:
            return jsonify(
                {
                    "error": "موجودی حساب کافی نیست",
                    "account_balance": effective,
                    "requested": payload["amount"],
                }
            )

    # Validate both accounts exist and belong to the same wallet
    if from_account_id and to_account_id:
        from_wallet = _get_account_wallet_id(cursor, from_account_id)
        to_wallet = _get_account_wallet_id(cursor, to_account_id)
        if from_wallet is None:
            return jsonify({"error": "حساب مبدا یافت نشد"})
        if to_wallet is None:
            return jsonify({"error": "حساب مقصد یافت نشد"})
        if from_wallet != to_wallet:
            return jsonify({"error": "هر دو حساب باید متعلق به یک کیف پول باشند"})

    return None


def _reverse_transaction_effect(cursor, transaction_row, user_id):
    old_type = _get_category_type(cursor, transaction_row["category_id"], user_id)
    if old_type:
        account_id = transaction_row.get("account_id")
        if account_id:
            _adjust_account_amount(cursor, account_id, transaction_row["amount"],
                                   "cost" if old_type == "income" else "income")
        else:
            _adjust_wallet_amount(cursor, transaction_row["wallet_id"], user_id,
                                  transaction_row["amount"],
                                  "cost" if old_type == "income" else "income")


def _apply_transfer_effect(cursor, transfer_row, user_id):
    """Apply transfer: debit from, credit to (with optional currency conversion)."""
    from_account_id = transfer_row.get("from_account_id")
    to_account_id = transfer_row.get("to_account_id")
    amount = transfer_row["amount"]

    if from_account_id and to_account_id:
        # Account-level transfer with possible currency conversion
        from_currency = _get_account_currency(cursor, from_account_id)
        to_currency = _get_account_currency(cursor, to_account_id)

        to_amount = amount
        if from_currency and to_currency and from_currency != to_currency:
            rate = get_exchange_rate(cursor, user_id, from_currency, to_currency)
            if rate is not None:
                to_amount = float(convert_amount(amount, from_currency, to_currency, rate))

        _adjust_account_amount(cursor, from_account_id, amount, "cost")
        _adjust_account_amount(cursor, to_account_id, to_amount, "income")
    # else: legacy wallet-level transfers no longer supported (wallets have no amount column)


def _reverse_transfer_effect(cursor, transfer_row, user_id):
    from_account_id = transfer_row.get("from_account_id")
    to_account_id = transfer_row.get("to_account_id")
    amount = transfer_row["amount"]

    if from_account_id and to_account_id:
        from_currency = _get_account_currency(cursor, from_account_id)
        to_currency = _get_account_currency(cursor, to_account_id)

        to_amount = amount
        if from_currency and to_currency and from_currency != to_currency:
            rate = get_exchange_rate(cursor, user_id, from_currency, to_currency)
            if rate is not None:
                to_amount = float(convert_amount(amount, from_currency, to_currency, rate))

        _adjust_account_amount(cursor, from_account_id, amount, "income")
        _adjust_account_amount(cursor, to_account_id, to_amount, "cost")
    # else: legacy wallet-level transfers no longer supported


def _error_status(response):
    payload = response.get_json(silent=True) or {}
    error = (payload.get("error") or "").lower()
    return 404 if "not found" in error else 400


@bp.route("", methods=["GET"])
def list_transactions():
    """List transactions with filters and optional transfers.
    ---
    tags:
      - Transactions
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
      - name: category_id
        in: query
        type: integer
      - name: wallet_id
        in: query
        type: integer
      - name: source_id
        in: query
        type: integer
        description: Alias for wallet_id
      - name: date_from
        in: query
        type: string
        description: Jalali start date (YYYY/MM/DD)
      - name: date_to
        in: query
        type: string
        description: Jalali end date (YYYY/MM/DD)
      - name: min_amount
        in: query
        type: number
      - name: max_amount
        in: query
        type: number
      - name: description
        in: query
        type: string
      - name: category_type
        in: query
        type: string
        enum: [income, cost, transfer]
      - name: tag_id
        in: query
        type: integer
        description: Filter transactions by tag
      - name: label_id
        in: query
        type: integer
        description: Filter transactions by label
      - name: include_transfers
        in: query
        type: string
        description: Set to 1/true/yes to merge transfers into results
    responses:
      200:
        description: Paginated list of transactions
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    page, per_page = parse_pagination()

    category_id = request.args.get("category_id", type=int)
    wallet_id = request.args.get("wallet_id", type=int) or request.args.get("source_id", type=int)
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)
    description = request.args.get("description", "").strip()
    category_type = request.args.get("category_type", "").strip().lower()
    tag_id = request.args.get("tag_id", type=int)
    label_id = request.args.get("label_id", type=int)
    include_transfers = request.args.get("include_transfers", "").strip().lower() in ("1", "true", "yes")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        base_where = (
            " WHERE t.deleted_at IS NULL"
            " AND ("
            "   (t.wallet_id IS NULL AND t.user_id = %s)"
            "   OR t.wallet_id IN ("
            "     SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
            "     UNION"
            "     SELECT wallet_id FROM wallet_members WHERE user_id = %s"
            "   )"
            " )"
            " AND ("
            "   t.is_private = FALSE"
            "   OR t.user_id = %s"
            "   OR EXISTS (SELECT 1 FROM wallets w2 WHERE w2.id = t.wallet_id AND w2.user_id = %s)"
            " )"
        )
        base_params = [user_id, user_id, user_id, user_id, user_id]

        filter_clause = ""
        filter_params = []

        if category_type == "transfer":
            filter_clause += " AND 1 = 0"
        if category_id is not None:
            filter_clause += " AND t.category_id = %s"
            filter_params.append(category_id)
        if category_type in ("income", "cost"):
            filter_clause += " AND c.type = %s"
            filter_params.append(category_type)
        if wallet_id is not None:
            filter_clause += " AND t.wallet_id = %s"
            filter_params.append(wallet_id)
        if date_from:
            filter_clause += " AND t.date >= %s"
            date_from = jalali_to_gregorian(date_from)
            filter_params.append(date_from)
        if date_to:
            filter_clause += " AND t.date <= %s"
            date_to = jalali_to_gregorian(date_to)
            filter_params.append(date_to)
        if min_amount is not None:
            filter_clause += " AND t.amount >= %s"
            filter_params.append(min_amount)
        if max_amount is not None:
            filter_clause += " AND t.amount <= %s"
            filter_params.append(max_amount)
        if description:
            filter_clause += " AND t.description LIKE %s"
            filter_params.append(f"%{description}%")
        if tag_id is not None:
            filter_clause += " AND EXISTS (SELECT 1 FROM transaction_tags tt WHERE tt.transaction_id = t.id AND tt.tag_id = %s)"
            filter_params.append(tag_id)
        if label_id is not None:
            filter_clause += " AND EXISTS (SELECT 1 FROM transaction_labels tl WHERE tl.transaction_id = t.id AND tl.label_id = %s)"
            filter_params.append(label_id)

        join_clause = (
            " FROM transactions t "
            "LEFT JOIN categories c ON t.category_id = c.id "
            "LEFT JOIN wallets w ON t.wallet_id = w.id "
            "LEFT JOIN users u ON u.id = t.user_id"
        )
        all_params = base_params + filter_params

        def _attach_tags_labels(tx_ids):
            """Batch-attach tags and labels to a list of transaction ids."""
            if not tx_ids:
                return {}, {}
            tags_map, labels_map = {}, {}
            cursor.execute(
                "SELECT tt.transaction_id, t.id, t.name, t.color "
                "FROM transaction_tags tt JOIN tags t ON t.id = tt.tag_id "
                "WHERE t.deleted_at IS NULL AND tt.transaction_id = ANY(%s)",
                (tx_ids,),
            )
            for r in cursor.fetchall():
                tags_map.setdefault(r["transaction_id"], []).append(
                    {"id": r["id"], "name": r["name"], "color": r["color"]}
                )
            cursor.execute(
                "SELECT tl.transaction_id, l.id, l.name, l.color "
                "FROM transaction_labels tl JOIN labels l ON l.id = tl.label_id "
                "WHERE l.deleted_at IS NULL AND tl.transaction_id = ANY(%s)",
                (tx_ids,),
            )
            for r in cursor.fetchall():
                labels_map.setdefault(r["transaction_id"], []).append(
                    {"id": r["id"], "name": r["name"], "color": r["color"]}
                )
            return tags_map, labels_map

        def _serialize_tx(row, tags_map=None, labels_map=None):
            d = row_to_dict(row)
            tx_id = d.get("id")
            d["record_type"] = "transaction"
            d["is_transfer"] = False
            d["date"] = gregorian_to_jalali(d["date"])
            d["tags"] = tags_map.get(tx_id, []) if tags_map else []
            d["labels"] = labels_map.get(tx_id, []) if labels_map else []
            return d

        # When including transfers, merge both types and paginate in Python
        if include_transfers and category_id is None and category_type in ("", "transfer"):
            count_sql = "SELECT COUNT(*) as total" + join_clause + base_where + filter_clause
            data_sql = (
                "SELECT t.*, c.name as category_name, w.name as source_name, c.type as category_type, "
                "w.wallet_type, w.user_id as wallet_owner_id, "
                "u.username as creator_username, u.display_name as creator_display_name"
                + join_clause + base_where + filter_clause + " ORDER BY t.date DESC"
            )
            cursor.execute(count_sql, all_params)
            tx_total = cursor.fetchone()["total"]

            # Fetch all transactions (no LIMIT) for merging
            cursor.execute(data_sql, all_params)
            tx_rows = cursor.fetchall()
            tx_ids = [r["id"] for r in tx_rows]
            tags_map, labels_map = _attach_tags_labels(tx_ids)
            results = [_serialize_tx(r, tags_map, labels_map) for r in tx_rows]

            # Fetch matching transfers
            transfer_query = (
                "SELECT t.*, "
                "fa.name as from_account_name, ta.name as to_account_name, "
                "fw.name as from_wallet_name, tw.name as to_wallet_name "
                "FROM transfers t "
                "LEFT JOIN accounts fa ON t.from_account_id = fa.id "
                "LEFT JOIN accounts ta ON t.to_account_id = ta.id "
                "LEFT JOIN wallets fw ON t.from_wallet_id = fw.id "
                "LEFT JOIN wallets tw ON t.to_wallet_id = tw.id "
                "WHERE t.deleted_at IS NULL"
                " AND (t.from_wallet_id IN ("
                "   SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
                "   UNION SELECT wallet_id FROM wallet_members WHERE user_id = %s"
                " ) OR t.to_wallet_id IN ("
                "   SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
                "   UNION SELECT wallet_id FROM wallet_members WHERE user_id = %s"
                " ))"
            )
            transfer_params = [user_id, user_id, user_id, user_id]

            if wallet_id is not None:
                transfer_query += " AND (t.from_wallet_id = %s OR t.to_wallet_id = %s)"
                transfer_params.extend([wallet_id, wallet_id])
            if date_from:
                transfer_query += " AND t.date >= %s"
                transfer_params.append(date_from)
            if date_to:
                transfer_query += " AND t.date <= %s"
                transfer_params.append(date_to)
            if min_amount is not None:
                transfer_query += " AND t.amount >= %s"
                transfer_params.append(min_amount)
            if max_amount is not None:
                transfer_query += " AND t.amount <= %s"
                transfer_params.append(max_amount)
            if description:
                transfer_query += " AND t.notes LIKE %s"
                transfer_params.append(f"%{description}%")

            cursor.execute(transfer_query, transfer_params)
            transfer_rows = cursor.fetchall()
            results.extend(_format_transfer_list_row(row) for row in transfer_rows)

            results.sort(key=lambda item: item.get("date", ""), reverse=True)
            total = len(results)
            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            offset = (page - 1) * per_page
            page_items = results[offset:offset + per_page]

            return jsonify({
                "items": page_items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            })
        else:
            # Standard pagination (transactions only)
            count_sql = "SELECT COUNT(*) as total" + join_clause + base_where + filter_clause
            data_sql = (
                "SELECT t.*, c.name as category_name, w.name as source_name, c.type as category_type, "
                "w.wallet_type, w.user_id as wallet_owner_id, "
                "u.username as creator_username, u.display_name as creator_display_name"
                + join_clause + base_where + filter_clause + " ORDER BY t.date DESC"
            )
            cursor.execute(count_sql, all_params)
            total = cursor.fetchone()["total"]
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", all_params + [per_page, offset])
            rows = cursor.fetchall()
            tx_ids = [r["id"] for r in rows]
            tags_map, labels_map = _attach_tags_labels(tx_ids)
            items = [_serialize_tx(r, tags_map, labels_map) for r in rows]
            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return jsonify({
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            })
    finally:
        cursor.close()
        release_connection(conn)


@bp.route("", methods=["POST"])
def create_transaction():
    """Create a new transaction or transfer.
    ---
    tags:
      - Transactions
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
            is_transfer:
              type: boolean
              description: If true, creates a transfer instead of a transaction
            date:
              type: string
              description: Jalali date (YYYY/MM/DD)
            amount:
              type: number
            category_id:
              type: integer
            wallet_id:
              type: integer
            account_id:
              type: integer
            description:
              type: string
            is_private:
              type: boolean
            items:
              type: array
              description: Optional transaction line items
            from_account_id:
              type: integer
              description: Required if is_transfer is true
            to_account_id:
              type: integer
              description: Required if is_transfer is true
          required:
            - date
            - amount
    responses:
      201:
        description: Transaction or transfer created successfully
      400:
        description: Validation error
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    is_transfer = bool(data.get("is_transfer"))

    if is_transfer:
        try:
            payload = _validate_transfer_payload(data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        conn = get_connection()
        cursor = conn.cursor()
        err_response = _validate_transfer_business_rules(cursor, user_id, payload)
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code
        try:
            # Derive wallet IDs from accounts
            from_account_id = payload["from_account_id"]
            to_account_id = payload["to_account_id"]
            from_wallet_id = _get_account_wallet_id(cursor, from_account_id)
            to_wallet_id = _get_account_wallet_id(cursor, to_account_id)

            cursor.execute(
                """
                INSERT INTO transfers (user_id, from_wallet_id, to_wallet_id, from_account_id, to_account_id, amount, date, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    from_wallet_id,
                    to_wallet_id,
                    from_account_id,
                    to_account_id,
                    payload["amount"],
                    payload["date"],
                    payload["notes"],
                ),
            )
            new_row = cursor.fetchone()
            if new_row is None:
                conn.rollback()
                cursor.close()
                release_connection(conn)
                return jsonify({"error": "خطا در ثبت اطلاعات"}), 500
            new_id = new_row["id"]
            _apply_transfer_effect(cursor, payload, user_id)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400
        else:
            cursor.close()
            release_connection(conn)
            return jsonify(_serialize_transfer(payload, new_id)), 201

    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Validate items if provided
    raw_items = data.get("items")
    items = None
    if raw_items is not None:
        try:
            items = validate_transaction_items_payload(raw_items)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if items:
            items_sum = sum(i["total_price"] for i in items)
            if abs(items_sum - payload["amount"]) > 0.01:
                return jsonify({
                    "error": "مجموع قیمت اقلام با مبلغ تراکنش مطابقت ندارد",
                    "items_sum": items_sum,
                    "transaction_amount": payload["amount"],
                }), 400

    conn = get_connection()
    cursor = conn.cursor()

    err_response, cat_type = _validate_transaction_business_rules(cursor, user_id, payload)
    if err_response:
        status_code = _error_status(err_response)
        cursor.close()
        release_connection(conn)
        return err_response, status_code

    # Resolve account_id and wallet_id
    account_id = data.get("account_id")
    source_id = payload.get("wallet_id")
    is_private = bool(data.get("is_private", False))

    # If account_id provided, resolve wallet_id from it
    if account_id:
        resolved_wallet = _get_account_wallet_id(cursor, account_id)
        if resolved_wallet:
            source_id = resolved_wallet
            payload["wallet_id"] = source_id

    try:
        cursor.execute(
            """
            INSERT INTO transactions (user_id, date, amount, category_id, wallet_id, account_id, description, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                payload["date"],
                payload["amount"],
                payload["category_id"],
                source_id,
                account_id,
                payload["description"],
                is_private,
            ),
        )
        new_row = cursor.fetchone()
        if new_row is None:
            conn.rollback()
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "خطا در ثبت اطلاعات"}), 500
        new_id = new_row['id']

        # Insert items if provided
        inserted_items = []
        if items:
            inserted_items = TransactionItemService.create_items(cursor, new_id, items)

        # Adjust balance at account level or wallet level
        if account_id:
            _adjust_account_amount(cursor, account_id, payload["amount"], cat_type)
        else:
            _adjust_wallet_amount(cursor, source_id, user_id, payload["amount"], cat_type)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        cursor.close()
        release_connection(conn)
        return jsonify({"error": str(exc)}), 400

    cursor.close()
    release_connection(conn)

    result = _serialize_transaction(payload, new_id)
    if inserted_items:
        result["items"] = inserted_items
    return jsonify(result), 201


@bp.route("/<int:tx_id>", methods=["GET"])
def get_transaction(tx_id):
    """Get a single transaction or transfer by ID.
    ---
    tags:
      - Transactions
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: record_type
        in: query
        type: string
        enum: [transaction, transfer]
        description: Hint to look up as transaction or transfer first
    responses:
      200:
        description: Transaction or transfer details
      404:
        description: Transaction not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    record_type = request.args.get("record_type", "").strip().lower()
    row = None
    if record_type != "transfer":
        row = _get_transaction_row(cursor, tx_id, user_id)
        if row is not None:
            record_type = "transaction"
    if row is None:
        row = _get_transfer_row(cursor, tx_id, user_id)
        record_type = "transfer"
    if row is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "تراکنش یافت نشد"}), 404
    d = row_to_dict(row)
    d["date"] = gregorian_to_jalali(d["date"])
    if record_type == "transfer":
        d["is_transfer"] = True
        d["description"] = d.get("notes")
    else:
        d["is_transfer"] = False
        # Include items for regular transactions
        items = TransactionItemService.get_items_by_transaction(cursor, tx_id, user_id)
        if items:
            d["items"] = items
            d["item_count"] = len(items)
        # Include tags and labels
        d["tags"] = TagService.get_transaction_tags(tx_id)
        d["labels"] = LabelService.get_transaction_labels(tx_id)
    cursor.close()
    release_connection(conn)
    return jsonify(d)


@bp.route("/<int:tx_id>", methods=["PUT"])
def update_transaction(tx_id):
    """Update an existing transaction or transfer. Supports type conversion between transaction and transfer.
    ---
    tags:
      - Transactions
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: record_type
        in: query
        type: string
        enum: [transaction, transfer]
        description: Hint for the current record type
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            is_transfer:
              type: boolean
            original_is_transfer:
              type: boolean
              description: Indicates the current record is a transfer
            date:
              type: string
            amount:
              type: number
            category_id:
              type: integer
            wallet_id:
              type: integer
            account_id:
              type: integer
            description:
              type: string
            is_private:
              type: boolean
            items:
              type: array
            from_account_id:
              type: integer
            to_account_id:
              type: integer
          required:
            - date
            - amount
    responses:
      200:
        description: Updated transaction or transfer
      400:
        description: Validation error
      403:
        description: Unauthorized
      404:
        description: Transaction not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    data = request.get_json(force=True, silent=True) or {}
    is_transfer = bool(data.get("is_transfer"))
    original_is_transfer = bool(data.get("original_is_transfer"))
    record_type = request.args.get("record_type", "").strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    if original_is_transfer or record_type == "transfer":
        old_transfer = _get_transfer_row(cursor, tx_id, user_id)
        if old_transfer is None:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "انتقال یافت نشد"}), 404

        # Check transfer permission
        can_modify = False
        for wid in [old_transfer.get("from_wallet_id"), old_transfer.get("to_wallet_id")]:
            if wid is None:
                continue
            cursor.execute(
                "SELECT user_id, wallet_type FROM wallets WHERE id = %s AND deleted_at IS NULL", (wid,)
            )
            w = cursor.fetchone()
            if w and w["user_id"] == user_id:
                can_modify = True
                break
            if w and w["wallet_type"] == "shared":
                cursor.execute(
                    "SELECT role FROM wallet_members WHERE wallet_id = %s AND user_id = %s", (wid, user_id)
                )
                m = cursor.fetchone()
                if m and m["role"] in ("owner", "editor"):
                    can_modify = True
                    break
        if not can_modify:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "دسترسی غیرمجاز"}), 403

        if is_transfer:
            try:
                payload = _validate_transfer_payload(data)
            except ValueError as exc:
                cursor.close()
                release_connection(conn)
                return jsonify({"error": str(exc)}), 400

            err_response = _validate_transfer_business_rules(cursor, user_id, payload, old_transfer=old_transfer)
            if err_response:
                status_code = _error_status(err_response)
                cursor.close()
                release_connection(conn)
                return err_response, status_code

            _reverse_transfer_effect(cursor, old_transfer, user_id)
            cursor.execute(
                """
                UPDATE transfers
                SET from_wallet_id = %s, to_wallet_id = %s, from_account_id = %s, to_account_id = %s,
                    amount = %s, date = %s, notes = %s
                WHERE id = %s
                """,
                (
                    payload["from_wallet_id"],
                    payload["to_wallet_id"],
                    payload.get("from_account_id"),
                    payload.get("to_account_id"),
                    payload["amount"],
                    payload["date"],
                    payload["notes"],
                    tx_id,
                ),
            )
            _apply_transfer_effect(cursor, payload, user_id)
            conn.commit()
            cursor.close()
            release_connection(conn)
            return jsonify(_serialize_transfer(payload, tx_id))

        try:
            payload = validate_transaction_payload(data)
        except ValueError as exc:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400

        account_id = data.get("account_id")
        is_private = bool(data.get("is_private", False))

        err_response, new_type = _validate_transaction_business_rules(
            cursor, user_id, payload, old_transfer=old_transfer
        )
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code

        _reverse_transfer_effect(cursor, old_transfer, user_id)
        cursor.execute(
            "UPDATE transfers SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL",
            (tx_id,),
        )

        if account_id:
            wallet_id = _get_account_wallet_id(cursor, account_id)
        else:
            wallet_id = payload.get("wallet_id")

        cursor.execute(
            """
            INSERT INTO transactions (user_id, date, amount, category_id, wallet_id, account_id, description, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                payload["date"],
                payload["amount"],
                payload["category_id"],
                wallet_id,
                account_id,
                payload["description"],
                is_private,
            ),
        )
        new_id = cursor.fetchone()['id']

        if account_id:
            _adjust_account_amount(cursor, account_id, payload["amount"], new_type)
        else:
            _adjust_wallet_amount(cursor, wallet_id, user_id, payload["amount"], new_type)
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify(_serialize_transaction(payload, new_id))

    old_transaction = _get_transaction_row(cursor, tx_id, user_id)
    if old_transaction is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "تراکنش یافت نشد"}), 404

    if not _can_modify_transaction(cursor, old_transaction, user_id):
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دسترسی غیرمجاز"}), 403

    if is_transfer:
        try:
            payload = _validate_transfer_payload(data)
        except ValueError as exc:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400

        err_response = _validate_transfer_business_rules(cursor, user_id, payload, old_transaction=old_transaction)
        if err_response:
            status_code = _error_status(err_response)
            cursor.close()
            release_connection(conn)
            return err_response, status_code

        _reverse_transaction_effect(cursor, old_transaction, user_id)
        cursor.execute(
            "UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL",
            (tx_id,),
        )
        cursor.execute(
            """
            INSERT INTO transfers (user_id, from_wallet_id, to_wallet_id, from_account_id, to_account_id, amount, date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                payload["from_wallet_id"],
                payload["to_wallet_id"],
                payload.get("from_account_id"),
                payload.get("to_account_id"),
                payload["amount"],
                payload["date"],
                payload["notes"],
            ),
        )
        new_id = cursor.fetchone()['id']
        _apply_transfer_effect(cursor, payload, user_id)
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify(_serialize_transfer(payload, new_id))

    try:
        payload = validate_transaction_payload(data)
    except ValueError as exc:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": str(exc)}), 400

    # Validate items if provided
    raw_items = data.get("items")
    items = None
    if raw_items is not None:
        try:
            items = validate_transaction_items_payload(raw_items)
        except ValueError as exc:
            cursor.close()
            release_connection(conn)
            return jsonify({"error": str(exc)}), 400
        if items:
            items_sum = sum(i["total_price"] for i in items)
            if abs(items_sum - payload["amount"]) > 0.01:
                cursor.close()
                release_connection(conn)
                return jsonify({
                    "error": "مجموع قیمت اقلام با مبلغ تراکنش مطابقت ندارد",
                    "items_sum": items_sum,
                    "transaction_amount": payload["amount"],
                }), 400

    err_response, new_type = _validate_transaction_business_rules(
        cursor, user_id, payload, old_transaction=old_transaction
    )
    if err_response:
        status_code = _error_status(err_response)
        cursor.close()
        release_connection(conn)
        return err_response, status_code

    # Resolve account_id
    account_id = data.get("account_id") or old_transaction.get("account_id")
    is_private = data.get("is_private", old_transaction.get("is_private", False))

    if account_id:
        wallet_id = _get_account_wallet_id(cursor, account_id)
    else:
        wallet_id = payload.get("wallet_id")

    try:
        _reverse_transaction_effect(cursor, old_transaction, user_id)
        cursor.execute(
            """
            UPDATE transactions
            SET date = %s, amount = %s, category_id = %s, wallet_id = %s, account_id = %s,
                description = %s, is_private = %s
            WHERE id = %s
            """,
            (
                payload["date"],
                payload["amount"],
                payload["category_id"],
                wallet_id,
                account_id,
                payload["description"],
                is_private,
                tx_id,
            ),
        )
        # Replace items if provided
        inserted_items = []
        if items is not None:
            TransactionItemService.soft_delete_items_by_transaction(cursor, tx_id)
            if items:
                inserted_items = TransactionItemService.create_items(cursor, tx_id, items)

        if account_id:
            _adjust_account_amount(cursor, account_id, payload["amount"], new_type)
        else:
            _adjust_wallet_amount(cursor, wallet_id, user_id, payload["amount"], new_type)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        cursor.close()
        release_connection(conn)
        return jsonify({"error": str(exc)}), 400

    cursor.close()
    release_connection(conn)

    result = _serialize_transaction(payload, tx_id)
    if items is not None:
        result["items"] = inserted_items
    return jsonify(result)


@bp.route("/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    """Soft-delete a transaction or transfer. Reverses balance effects.
    ---
    tags:
      - Transactions
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: record_type
        in: query
        type: string
        enum: [transaction, transfer]
        description: Hint for the record type to delete
    responses:
      200:
        description: Transaction archived
      403:
        description: Unauthorized
      404:
        description: Transaction not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    record_type = request.args.get("record_type", "").strip().lower()
    old = None if record_type == "transfer" else _get_transaction_row(cursor, tx_id, user_id)
    if old is not None:
        if not _can_modify_transaction(cursor, old, user_id):
            cursor.close()
            release_connection(conn)
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        _reverse_transaction_effect(cursor, old, user_id)
        cursor.execute(
            "UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL",
            (tx_id,),
        )
        conn.commit()
        cursor.close()
        release_connection(conn)
        return jsonify({"message": "Transaction archived"})

    old_transfer = _get_transfer_row(cursor, tx_id, user_id)
    if old_transfer is None:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "تراکنش یافت نشد"}), 404

    # Check transfer permission — must be owner of at least one wallet
    from_wallet_id = old_transfer.get("from_wallet_id")
    to_wallet_id = old_transfer.get("to_wallet_id")
    can_modify = False
    for wid in [from_wallet_id, to_wallet_id]:
        if wid is None:
            continue
        cursor.execute(
            "SELECT user_id, wallet_type FROM wallets WHERE id = %s AND deleted_at IS NULL",
            (wid,)
        )
        w = cursor.fetchone()
        if w and w["user_id"] == user_id:
            can_modify = True
            break
        if w and w["wallet_type"] == "shared":
            cursor.execute(
                "SELECT role FROM wallet_members WHERE wallet_id = %s AND user_id = %s",
                (wid, user_id)
            )
            m = cursor.fetchone()
            if m and m["role"] in ("owner", "editor"):
                can_modify = True
                break
    if not can_modify:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "دسترسی غیرمجاز"}), 403

    _reverse_transfer_effect(cursor, old_transfer, user_id)
    cursor.execute(
        "UPDATE transfers SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL",
        (tx_id,),
    )
    conn.commit()
    cursor.close()
    release_connection(conn)
    return jsonify({"message": "Transaction archived"})


# ── Item CRUD endpoints ────────────────────────────────────────────────


def _get_transaction_for_items(cursor, tx_id, user_id):
    """Fetch transaction row and verify access (owner or wallet member). Returns (row, error_response)."""
    cursor.execute(
        "SELECT * FROM transactions WHERE id = %s AND deleted_at IS NULL"
        " AND ("
        "   (wallet_id IS NULL AND user_id = %s)"
        "   OR wallet_id IN ("
        "     SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL"
        "     UNION"
        "     SELECT wallet_id FROM wallet_members WHERE user_id = %s"
        "   )"
        " )",
        (tx_id, user_id, user_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        return None, (jsonify({"error": "تراکنش یافت نشد"}), 404)
    return row, None


@bp.route("/<int:tx_id>/items", methods=["GET"])
def list_transaction_items(tx_id):
    """List all items for a transaction.
    ---
    tags:
      - Transaction Items
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
        description: List of transaction items
      404:
        description: Transaction not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    conn = get_connection()
    cursor = conn.cursor()
    tx_row, err_resp = _get_transaction_for_items(cursor, tx_id, user_id)
    if err_resp:
        cursor.close()
        release_connection(conn)
        return err_resp
    items = TransactionItemService.get_items_by_transaction(cursor, tx_id, user_id)
    cursor.close()
    release_connection(conn)
    return jsonify(items)


@bp.route("/<int:tx_id>/items", methods=["POST"])
def add_transaction_item(tx_id):
    """Add a new item to a transaction.
    ---
    tags:
      - Transaction Items
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
            name:
              type: string
            quantity:
              type: number
            unit_price:
              type: number
            total_price:
              type: number
            description:
              type: string
          required:
            - name
            - quantity
            - unit_price
            - total_price
    responses:
      201:
        description: Item created successfully
      400:
        description: Validation error
      404:
        description: Transaction not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    try:
        item_data = validate_transaction_items_payload([data])[0]
    except (ValueError, IndexError) as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    tx_row, err_resp = _get_transaction_for_items(cursor, tx_id, user_id)
    if err_resp:
        cursor.close()
        release_connection(conn)
        return err_resp

    try:
        inserted = TransactionItemService.create_item(cursor, tx_id, item_data)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        cursor.close()
        release_connection(conn)
        return jsonify({"error": str(exc)}), 400

    cursor.close()
    release_connection(conn)
    return jsonify(inserted), 201


@bp.route("/<int:tx_id>/items/<int:item_id>", methods=["PUT"])
def update_transaction_item(tx_id, item_id):
    """Update an existing transaction item.
    ---
    tags:
      - Transaction Items
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: item_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            quantity:
              type: number
            unit_price:
              type: number
            total_price:
              type: number
            description:
              type: string
          required:
            - name
            - quantity
            - unit_price
            - total_price
    responses:
      200:
        description: Updated item
      400:
        description: Validation error
      404:
        description: Item not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    try:
        item_data = validate_transaction_items_payload([data])[0]
    except (ValueError, IndexError) as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    cursor = conn.cursor()
    tx_row, err_resp = _get_transaction_for_items(cursor, tx_id, user_id)
    if err_resp:
        cursor.close()
        release_connection(conn)
        return err_resp

    existing = TransactionItemService.get_item(cursor, item_id, user_id)
    if existing is None or existing["transaction_id"] != tx_id:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "قلم یافت نشد"}), 404

    cursor.close()
    release_connection(conn)

    try:
        updated = TransactionItemService.update_item(item_id, user_id, item_data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(updated)


@bp.route("/<int:tx_id>/items/<int:item_id>", methods=["DELETE"])
def delete_transaction_item(tx_id, item_id):
    """Soft-delete a transaction item.
    ---
    tags:
      - Transaction Items
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: tx_id
        in: path
        type: integer
        required: true
      - name: item_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Item archived
      404:
        description: Item not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err

    conn = get_connection()
    cursor = conn.cursor()
    tx_row, err_resp = _get_transaction_for_items(cursor, tx_id, user_id)
    if err_resp:
        cursor.close()
        release_connection(conn)
        return err_resp

    existing = TransactionItemService.get_item(cursor, item_id, user_id)
    if existing is None or existing["transaction_id"] != tx_id:
        cursor.close()
        release_connection(conn)
        return jsonify({"error": "قلم یافت نشد"}), 404

    cursor.close()
    release_connection(conn)

    try:
        TransactionItemService.delete_item(item_id, user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Item archived"})


# ── Item reporting endpoints ───────────────────────────────────────────


@bp.route("/items/most-purchased", methods=["GET"])
def most_purchased_items():
    """Get the most frequently purchased items.
    ---
    tags:
      - Transaction Items
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
        description: List of most purchased items
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    limit = request.args.get("limit", 10, type=int)
    results = TransactionItemService.get_most_purchased(user_id, limit=limit)
    return jsonify(results)


@bp.route("/items/search", methods=["GET"])
def search_items():
    """Search transaction items by name.
    ---
    tags:
      - Transaction Items
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: q
        in: query
        type: string
        required: true
        description: Search query string
    responses:
      200:
        description: Matching items
      400:
        description: Missing search query
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "جستجو با پارامتر 'q' الزامی است"}), 400
    results = TransactionItemService.search_items(user_id, q)
    return jsonify(results)


@bp.route("/items/stats", methods=["GET"])
def item_stats():
    """Get statistics for a specific item by name.
    ---
    tags:
      - Transaction Items
    parameters:
      - name: X-Username
        in: header
        type: string
        required: true
      - name: name
        in: query
        type: string
        required: true
        description: Item name to get stats for
    responses:
      200:
        description: Item statistics
      400:
        description: Missing item name
      404:
        description: Item not found
    """
    user_id, err = get_user_id_from_request()
    if err:
        return err
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "نام قلم با پارامتر 'name' الزامی است"}), 400
    stats = TransactionItemService.get_item_stats(user_id, name)
    if stats is None:
        return jsonify({"error": "قلمی با این نام یافت نشد"}), 404
    return jsonify(stats)
