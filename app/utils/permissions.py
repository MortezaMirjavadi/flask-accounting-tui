"""Wallet role-based access control utilities."""

from database import get_connection, release_connection
from flask import jsonify

# Role hierarchy: owner > editor > viewer
ROLE_HIERARCHY = {'owner': 3, 'editor': 2, 'viewer': 1}


def get_wallet_role(cursor, wallet_id, user_id):
    """Return user's role in a wallet, or None if no access.

    For personal wallets, only the owner (wallets.user_id) has access.
    For shared wallets, check wallet_members table.
    """
    # Check if user is the wallet creator
    cursor.execute(
        "SELECT user_id, wallet_type FROM wallets WHERE id = %s AND deleted_at IS NULL",
        (wallet_id,)
    )
    wallet = cursor.fetchone()
    if wallet is None:
        return None

    if wallet['user_id'] == user_id:
        return 'owner'

    if wallet['wallet_type'] == 'personal':
        return None

    # Check wallet_members for shared wallets
    cursor.execute(
        "SELECT role FROM wallet_members WHERE wallet_id = %s AND user_id = %s",
        (wallet_id, user_id)
    )
    member = cursor.fetchone()
    if member is None:
        return None

    return member['role']


def has_wallet_access(cursor, wallet_id, user_id, min_role='viewer'):
    """Check if user has at least the specified role in a wallet."""
    role = get_wallet_role(cursor, wallet_id, user_id)
    if role is None:
        return False
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


def require_wallet_access(cursor, wallet_id, user_id, min_role='viewer'):
    """Return error response if user lacks sufficient role, or None if allowed."""
    role = get_wallet_role(cursor, wallet_id, user_id)
    if role is None:
        return jsonify({"error": "کیف پول یافت نشد"}), 404
    if ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY.get(min_role, 0):
        return jsonify({"error": "شما دسترسی کافی برای این عملیات را ندارید"}), 403
    return None


def get_account_wallet_id(cursor, account_id):
    """Resolve the wallet_id for a given account. Returns None if not found."""
    cursor.execute(
        "SELECT wallet_id FROM accounts WHERE id = %s AND deleted_at IS NULL",
        (account_id,)
    )
    row = cursor.fetchone()
    return row['wallet_id'] if row else None


def get_account_role(cursor, account_id, user_id):
    """Get user's role via the account's wallet. Returns None if no access."""
    wallet_id = get_account_wallet_id(cursor, account_id)
    if wallet_id is None:
        return None
    return get_wallet_role(cursor, wallet_id, user_id)


def require_account_access(cursor, account_id, user_id, min_role='viewer'):
    """Check access to an account via its wallet. Returns error response or None."""
    wallet_id = get_account_wallet_id(cursor, account_id)
    if wallet_id is None:
        return jsonify({"error": "حساب یافت نشد"}), 404
    return require_wallet_access(cursor, wallet_id, user_id, min_role)


def can_view(user_role):
    return user_role in ('owner', 'editor', 'viewer')


def can_edit(user_role):
    return user_role in ('owner', 'editor')


def can_manage(user_role):
    return user_role == 'owner'
