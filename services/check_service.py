"""Check commitment service (issued/received)."""

from __future__ import annotations

from datetime import date, timedelta

from database import get_connection, release_connection
from services.commitment_utils import (
    coerce_date,
    coerce_positive_decimal,
    create_settlement_transaction,
    get_category_type,
    safe_int,
    to_int,
    to_iso_date,
    to_decimal,
)


def _coerce_check_type(value) -> str:
    if value is None:
        raise ValueError("type is required")
    if not isinstance(value, str):
        raise ValueError("type must be 'issued' or 'received'")
    value = value.strip().lower()
    if value not in ("issued", "received"):
        raise ValueError("type must be 'issued' or 'received'")
    return value


def _row_to_dict(row) -> dict:
    item = dict(row)
    if item.get("issue_date") is not None:
        item["issue_date"] = to_iso_date(item["issue_date"])
    if item.get("due_date") is not None:
        item["due_date"] = to_iso_date(item["due_date"])
    return item


class CheckService:
    """Service methods for check obligations."""

    @staticmethod
    def add_check(user_id: int, payload: dict) -> dict:
        bank_name = (payload.get("bank_name") or "").strip() or None
        check_number = (payload.get("check_number") or "").strip() or None

        amount = coerce_positive_decimal(payload.get("amount"), "amount")
        issue_date = coerce_date(payload.get("issue_date"))
        due_date = coerce_date(payload.get("due_date"))
        check_type = _coerce_check_type(payload.get("type"))

        category_id = to_int(payload.get("category_id"), "category_id")
        source_id = safe_int(payload.get("source_id"), "source_id")
        description = (payload.get("description") or "").strip() or None

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT type FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (category_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Category not found")

            if source_id is not None:
                cursor.execute(
                    "SELECT 1 FROM sources WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                    (source_id, user_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Source not found")

            cursor.execute(
                """
                INSERT INTO checks (
                    user_id, check_number, bank_name, amount, issue_date, due_date,
                    type, source_id, category_id, description, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (
                    user_id,
                    check_number,
                    bank_name,
                    amount,
                    to_iso_date(issue_date),
                    to_iso_date(due_date),
                    check_type,
                    source_id,
                    category_id,
                    description,
                ),
            )
            check_id = int(cursor.fetchone()["id"])
            conn.commit()

            cursor.execute("SELECT * FROM checks WHERE id = %s", (check_id,))
            return _row_to_dict(cursor.fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def list_checks(user_id: int, params: dict) -> list[dict]:
        status = params.get("status")
        bank_name = params.get("bank_name")
        check_number = params.get("check_number")
        check_type = params.get("check_type")

        conn = get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT * FROM checks
                WHERE user_id = %s AND deleted_at IS NULL
            """
            db_params = [user_id]

            if status:
                query += " AND status = %s"
                db_params.append(status)
            if bank_name:
                query += " AND bank_name ILIKE %s"
                db_params.append(f"%{bank_name}%")
            if check_number:
                query += " AND check_number ILIKE %s"
                db_params.append(f"%{check_number}%")
            if check_type:
                query += " AND type = %s"
                db_params.append(check_type)

            query += " ORDER BY due_date ASC"

            print("List Checks" + query)
            print("List Checks Params" + str(db_params))

            cursor.execute(query, db_params)
            return [_row_to_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_check(user_id: int, check_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM checks WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (check_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Check not found")
            return _row_to_dict(row)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def mark_check_cleared(user_id: int, check_id: int, *, cleared_date: str | date | None = None) -> dict:
        if cleared_date is None:
            cleared_date_value = date.today()
        else:
            cleared_date_value = coerce_date(cleared_date)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, type, category_id, source_id, amount, status, transaction_id
                FROM checks
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (check_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Check not found")

            if row["status"] == "cleared":
                raise ValueError("Check already cleared")
            if row["status"] in ("bounced", "canceled"):
                raise ValueError(f"Cannot clear a {row['status']} check")

            category_type = get_category_type(cursor, row["category_id"], user_id)
            expected = "cost" if row["type"] == "issued" else "income"
            if category_type != expected:
                raise ValueError(f"Category type must be '{expected}' for {row['type']} checks")

            tx_id = create_settlement_transaction(
                cursor,
                user_id,
                tx_date=cleared_date_value,
                amount=to_decimal(row["amount"]),
                category_id=row["category_id"],
                source_id=row["source_id"],
                description=f"Check #{row['id']} cleared",
                reference_type="check",
                reference_id=row["id"],
            )

            cursor.execute(
                """
                UPDATE checks
                SET status = 'cleared', transaction_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (tx_id, check_id),
            )
            conn.commit()

            cursor.execute(
                "SELECT * FROM checks WHERE id = %s AND user_id = %s",
                (check_id, user_id),
            )
            check_row = _row_to_dict(cursor.fetchone())
            check_row["transaction_id"] = tx_id
            return check_row
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def mark_check_bounced(user_id: int, check_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, status FROM checks
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (check_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Check not found")
            if row["status"] != "pending":
                raise ValueError(f"Cannot bounce check with status {row['status']}")

            cursor.execute(
                """
                UPDATE checks
                SET status = 'bounced', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (check_id,),
            )
            conn.commit()

            cursor.execute("SELECT * FROM checks WHERE id = %s", (check_id,))
            return _row_to_dict(cursor.fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def cancel_check(user_id: int, check_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, status FROM checks
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (check_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Check not found")
            if row["status"] not in ("pending",):
                raise ValueError(f"Cannot cancel check with status {row['status']}")

            cursor.execute(
                """
                UPDATE checks
                SET status = 'canceled', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (check_id,),
            )
            conn.commit()
            return {"id": int(check_id), "status": "canceled"}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update_check_dates(
        user_id: int,
        check_id: int,
        *,
        due_date,
    ) -> dict:
        due_date_value = coerce_date(due_date)
        if due_date_value is None:
            raise ValueError("due_date is required")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, status
                FROM checks
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (check_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Check not found")
            if row["status"] not in ("pending",):
                raise ValueError(f"Cannot update due date for status {row['status']}")

            cursor.execute(
                """
                UPDATE checks
                SET due_date = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (to_iso_date(due_date_value), check_id),
            )
            updated = cursor.fetchone()
            if updated is None:
                raise ValueError("Check update failed")
            conn.commit()
            return _row_to_dict(updated)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_upcoming_checks(user_id: int, days: int = 30) -> list[dict]:
        days = to_int(days, "days")
        window_end = date.today() + timedelta(days=days)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT * FROM checks
                WHERE user_id = %s
                  AND deleted_at IS NULL
                  AND status = 'pending'
                  AND due_date >= CURRENT_DATE
                  AND due_date <= %s
                ORDER BY due_date ASC
                """,
                (user_id, to_iso_date(window_end)),
            )
            return [_row_to_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)
