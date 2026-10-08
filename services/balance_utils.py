"""Wallet balance helpers.

Kept free of any `app.*` imports so low-level services can use it
without triggering the app-package import chain.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        raise ValueError("مبلغ نامعتبر است")


def get_wallet_balance(cursor, wallet_id: int, user_id: int) -> Decimal:
    """Derived balance: sum of account amounts + net transaction flow.

    Balances live on accounts and transactions, not on wallets.amount
    (that column was dropped).
    """
    cursor.execute(
        """
        SELECT
            COALESCE((SELECT SUM(a.amount) FROM accounts a
                      WHERE a.wallet_id = w.id AND a.deleted_at IS NULL), 0)
            + COALESCE((SELECT SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE -t.amount END)
                        FROM transactions t
                        LEFT JOIN categories c ON c.id = t.category_id
                        WHERE t.wallet_id = w.id AND t.user_id = w.user_id
                          AND t.deleted_at IS NULL), 0)
            AS balance
        FROM wallets w
        WHERE w.id = %s AND w.user_id = %s AND w.deleted_at IS NULL
        """,
        (wallet_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("کیف پول یافت نشد")
    return to_decimal(row["balance"])
