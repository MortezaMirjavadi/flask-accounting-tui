"""Shared helpers for commitment-related services."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.utils.helpers import jalali_to_gregorian


def to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        raise ValueError("Invalid amount")


def to_float(value: Decimal | int | float | str) -> float:
    return float(value)


def quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def coerce_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    value = str(value).strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def to_int(value: Any, field_name: str, *, allow_zero: bool = False) -> int:
    try:
        val = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")
    if not allow_zero and val <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return val


def safe_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    parsed = to_int(value, field_name, allow_zero=True)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return parsed


def coerce_positive_decimal(value: Any, field_name: str) -> Decimal:
    val = to_decimal(value)
    if val <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return val


def coerce_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    val = to_decimal(value)
    if val < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero")
    return val


def coerce_date(value: Any, *, allow_null: bool = False) -> date | None:
    if value is None:
        if allow_null:
            return None
        raise ValueError("Date is required")
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        raise ValueError("Date must be a string in YYYY-MM-DD format")

    value = value.strip()
    if not value:
        if allow_null:
            return None
        raise ValueError("Date is required")

    # Try Gregorian first; then Jalali compatibility path.
    for parser in (
        lambda txt: datetime.strptime(txt, "%Y-%m-%d").date(),
        lambda txt: datetime.strptime(jalali_to_gregorian(txt), "%Y-%m-%d").date(),
    ):
        try:
            return parser(value)
        except ValueError:
            continue

    raise ValueError("Invalid date format. Use YYYY-MM-DD")


def to_iso_date(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%Y-%m-%d")


def get_category_type(cursor, category_id: int, user_id: int) -> str:
    cursor.execute(
        "SELECT type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Category not found")
    return row["type"]


def ensure_category_exists(cursor, category_id: int, user_id: int) -> None:
    get_category_type(cursor, category_id, user_id)


def ensure_source_exists(cursor, source_id: int | None, user_id: int) -> None:
    if source_id is None:
        return
    cursor.execute(
        "SELECT 1 FROM sources WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (source_id, user_id),
    )
    if cursor.fetchone() is None:
        raise ValueError("Source not found")


def get_source_balance(cursor, source_id: int, user_id: int) -> Decimal:
    cursor.execute(
        "SELECT amount FROM sources WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
        (source_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Source not found")
    return to_decimal(row["amount"])


def apply_source_adjustment(cursor, source_id: int | None, user_id: int, amount: Decimal, category_type: str) -> None:
    if source_id is None:
        return
    delta = amount if category_type == "income" else -amount
    cursor.execute(
        "UPDATE sources SET amount = amount + %s WHERE id = %s AND user_id = %s",
        (to_float(delta), source_id, user_id),
    )


def create_settlement_transaction(
    cursor,
    user_id: int,
    *,
    tx_date: date,
    amount: Decimal,
    category_id: int,
    source_id: int | None,
    description: str,
    reference_type: str,
    reference_id: int,
) -> int:
    category_type = get_category_type(cursor, category_id, user_id)

    if source_id is not None:
        balance = get_source_balance(cursor, source_id, user_id)
        if category_type == "cost" and balance < amount:
            raise ValueError("Insufficient source balance")

    cursor.execute(
        """
        INSERT INTO transactions (
            user_id, date, amount, category_id, source_id, description, reference_type, reference_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (
            user_id,
            to_iso_date(tx_date),
            to_float(amount),
            category_id,
            source_id,
            description,
            reference_type,
            reference_id,
        ),
    )
    tx_id = cursor.fetchone()["id"]

    apply_source_adjustment(cursor, source_id, user_id, amount, category_type)
    return int(tx_id)
