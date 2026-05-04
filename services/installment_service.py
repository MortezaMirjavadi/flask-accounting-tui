"""Installment plan and installment business logic."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from database import get_connection, release_connection
from services.commitment_utils import (
    coerce_date,
    coerce_optional_decimal,
    coerce_positive_decimal,
    coerce_string,
    create_settlement_transaction,
    ensure_category_exists,
    ensure_source_exists,
    quantize_amount,
    safe_int,
    to_int,
    to_iso_date,
    to_decimal,
)


def _build_installment_amounts(total_amount: Decimal, installment_count: int, installment_amount: Decimal | None) -> list[Decimal]:
    if installment_amount is None:
        if installment_count <= 0:
            raise ValueError("installment_count must be greater than zero")
        if installment_count == 1:
            return [quantize_amount(total_amount)]
        base = quantize_amount(total_amount / Decimal(installment_count))
        amounts = [quantize_amount(base) for _ in range(installment_count)]
    else:
        base = quantize_amount(installment_amount)
        amounts = [quantize_amount(base) for _ in range(installment_count)]

    total_sum = sum(amounts, Decimal("0.00"))
    diff = quantize_amount(total_amount - total_sum)
    if amounts:
        amounts[-1] += diff

    # Keep all values in two decimal places after adjustment.
    return [quantize_amount(a) for a in amounts]


def _build_installment_due_dates(start_date: date, due_day_of_month: int, count: int) -> list[date]:
    due_dates: list[date] = []
    for index in range(count):
        if index == 0:
            due_dates.append(start_date)
            continue

        month_offset = index
        month_index = (start_date.year * 12 + (start_date.month - 1) + month_offset)
        year = month_index // 12
        month = month_index % 12 + 1
        max_day = monthrange(year, month)[1]
        due_day = min(due_day_of_month, max_day)
        due_dates.append(date(year, month, due_day))

    return due_dates


def _row_to_dict(row) -> dict:
    item = dict(row)
    for key in ("start_date", "due_date", "paid_date", "issue_date"):
        if key in item and item[key] is not None:
            item[key] = to_iso_date(item[key])
    return item


class InstallmentService:
    """Service methods for installment plans and installments."""

    @staticmethod
    def create_installment_plan(user_id: int, payload: dict) -> dict:
        title = coerce_string(payload.get("title"), field_name="title")
        total_amount = coerce_positive_decimal(payload.get("total_amount"), "total_amount")
        installment_count = to_int(payload.get("installment_count"), "installment_count")

        amount_field = coerce_optional_decimal(payload.get("installment_amount"), "installment_amount")
        if amount_field is not None and amount_field == Decimal("0"):
            raise ValueError("installment_amount must be greater than zero")

        start_date = coerce_date(payload.get("start_date"))
        due_day_of_month = payload.get("due_day_of_month")
        if due_day_of_month is None or due_day_of_month == "":
            due_day_of_month = start_date.day
        else:
            due_day_of_month = to_int(due_day_of_month, "due_day_of_month")
        if not 1 <= due_day_of_month <= 31:
            raise ValueError("due_day_of_month must be between 1 and 31")

        category_id = to_int(payload.get("category_id"), "category_id")
        source_id = safe_int(payload.get("source_id"), "source_id")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            ensure_category_exists(cursor, category_id, user_id)
            ensure_source_exists(cursor, source_id, user_id)

            installment_amounts = _build_installment_amounts(total_amount, installment_count, amount_field)

            status = (payload.get("status") or "active").strip().lower()
            if status not in ("active", "completed", "canceled"):
                raise ValueError("status must be active, completed, or canceled")

            cursor.execute(
                """
                INSERT INTO installment_plans (
                    user_id, title, total_amount, installment_count, installment_amount, start_date,
                    due_day_of_month, category_id, source_id, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    title,
                    float(quantize_amount(total_amount)),
                    installment_count,
                    float(quantize_amount(installment_amounts[0] if installment_amounts else Decimal("0")),),
                    to_iso_date(start_date),
                    due_day_of_month,
                    category_id,
                    source_id,
                    status,
                ),
            )
            plan_id = int(cursor.fetchone()["id"])

            InstallmentService.generate_installments(plan_id, user_id=user_id, connection=conn, amounts=installment_amounts)
            conn.commit()

            plan = InstallmentService.get_plan_details(user_id, plan_id)
            return plan
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def generate_installments(plan_id: int, *, user_id: int | None = None, connection=None, amounts: list[Decimal] | None = None) -> list[dict]:
        cursor = None
        own_connection = False

        if connection is None:
            connection = get_connection()
            own_connection = True

        created = []
        try:
            cursor = connection.cursor()
            plan_query = "SELECT * FROM installment_plans WHERE id = %s"
            params = [plan_id]
            if user_id is not None:
                plan_query += " AND user_id = %s AND deleted_at IS NULL"
                params.append(user_id)

            cursor.execute(plan_query, tuple(params))
            plan = cursor.fetchone()
            if plan is None:
                raise ValueError("Plan not found")

            if plan["status"] not in ("active", "completed", "canceled"):
                raise ValueError("Invalid plan status")

            installment_count = int(plan["installment_count"])
            start_date = plan["start_date"]
            due_day = int(plan["due_day_of_month"])
            if amounts is None:
                amounts = _build_installment_amounts(to_decimal(plan["total_amount"]), installment_count, to_decimal(plan["installment_amount"]))
            elif len(amounts) != installment_count:
                raise ValueError("installment amounts length must match installment_count")

            due_dates = _build_installment_due_dates(start_date, due_day, installment_count)
            for index, (due_at, installment_amount) in enumerate(zip(due_dates, amounts), start=1):
                cursor.execute(
                    """
                    INSERT INTO installments (
                        plan_id, installment_number, amount, due_date
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (plan_id, installment_number)
                    DO UPDATE SET
                        amount = EXCLUDED.amount,
                        due_date = EXCLUDED.due_date,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE installments.status = 'pending'
                    """,
                    (
                        plan_id,
                        index,
                        float(installment_amount),
                        to_iso_date(due_at),
                    ),
                )

            cursor.execute(
                """
                SELECT id, plan_id, installment_number, amount, due_date, paid_date, status, transaction_id
                FROM installments
                WHERE plan_id = %s
                ORDER BY installment_number ASC
                """,
                (plan_id,),
            )
            created = [_row_to_dict(row) for row in cursor.fetchall()]

            if own_connection:
                connection.commit()
            return created
        except Exception:
            if own_connection:
                connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if own_connection:
                release_connection(connection)

    @staticmethod
    def list_installment_plans(user_id: int, status: str | None = None) -> list[dict]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT p.id,
                    p.title,
                    p.total_amount,
                    p.installment_count,
                    p.installment_amount,
                    p.start_date,
                    p.due_day_of_month,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    c.name Category,
                    s.name Source
                FROM installment_plans p
                        INNER JOIN categories c on c.id = p.category_id
                        INNER JOIN sources s on s.id = p.source_id
                WHERE p.user_id = %s AND p.deleted_at IS NULL
            """
            params = [user_id]
            if status:
                query += " AND p.status = %s"
                params.append(status)
            query += " ORDER BY p.created_at DESC"
            cursor.execute(query, params)
            return [_row_to_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_plan_details(user_id: int, plan_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT p.id,
                    p.title,
                    p.total_amount,
                    p.installment_count,
                    p.installment_amount,
                    p.start_date,
                    p.due_day_of_month,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    c.name Category,
                    s.name Source
                FROM installment_plans p
                        INNER JOIN categories c on c.id = p.category_id
                        INNER JOIN sources s on s.id = p.source_id
                WHERE p.id = %s AND p.user_id = %s AND p.deleted_at IS NULL
                """,
                (plan_id, user_id),
            )
            plan_row = cursor.fetchone()
            if plan_row is None:
                raise ValueError("Plan not found")

            cursor.execute(
                """
                SELECT id, plan_id, installment_number, amount, due_date, paid_date, status, transaction_id
                FROM installments
                WHERE plan_id = %s
                ORDER BY installment_number ASC
                """,
                (plan_id,),
            )
            installments = [_row_to_dict(row) for row in cursor.fetchall()]

            plan = _row_to_dict(plan_row)
            plan["installments"] = installments
            return plan
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update_installment_due_date(
        user_id: int,
        installment_id: int,
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
                SELECT i.id, i.status
                FROM installments i
                JOIN installment_plans p ON p.id = i.plan_id
                WHERE i.id = %s AND p.user_id = %s AND p.deleted_at IS NULL
                """,
                (installment_id, user_id),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Installment not found")
            if existing["status"] == "paid":
                raise ValueError("Cannot reschedule paid installment")

            cursor.execute(
                """
                UPDATE installments
                SET due_date = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, plan_id, installment_number, amount, due_date, paid_date, status, transaction_id
                """,
                (to_iso_date(due_date_value), installment_id),
            )
            row = _row_to_dict(cursor.fetchone())
            if row is None:
                raise ValueError("Installment update failed")

            conn.commit()
            return row
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def _collect_installment_ids(installment_ids: int | list[int]) -> list[int]:
        if isinstance(installment_ids, int):
            return [installment_ids]
        if not isinstance(installment_ids, list):
            raise ValueError("installment_id must be an integer or list of integers")
        if not installment_ids:
            raise ValueError("installment_ids cannot be empty")

        cleaned: list[int] = []
        for item in installment_ids:
            if isinstance(item, bool):
                raise ValueError("installment_ids must contain integers")
            try:
                cleaned.append(int(item))
            except (TypeError, ValueError):
                raise ValueError("installment_ids must contain integers")
        return cleaned

    @staticmethod
    def mark_installment_paid(user_id: int, installment_ids: int | list[int], *, paid_date: str | date | None = None) -> dict:
        if paid_date is None:
            paid_date_value = date.today()
        else:
            paid_date_value = coerce_date(paid_date, allow_null=True)
        if paid_date_value is None:
            paid_date_value = date.today()

        ids = InstallmentService._collect_installment_ids(installment_ids)
        conn = get_connection()
        cursor = conn.cursor()

        try:
            paid_results: list[dict] = []
            for installment_id in ids:
                cursor.execute(
                    """
                    SELECT
                        i.id,
                        i.plan_id,
                        i.amount,
                        i.status,
                        i.paid_date,
                        p.category_id,
                        p.source_id,
                        p.status AS plan_status
                    FROM installments i
                    JOIN installment_plans p ON p.id = i.plan_id
                    WHERE i.id = %s AND p.user_id = %s AND p.deleted_at IS NULL
                    """,
                    (installment_id, user_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError(f"Installment not found: {installment_id}")
                if row["status"] != "pending":
                    raise ValueError(f"Installment {installment_id} is not pending")
                if row["plan_status"] == "canceled":
                    raise ValueError(f"Installment {installment_id} belongs to a canceled plan")

                amount = to_decimal(row["amount"])
                tx_id = create_settlement_transaction(
                    cursor,
                    user_id,
                    tx_date=paid_date_value,
                    amount=amount,
                    category_id=row["category_id"],
                    source_id=row["source_id"],
                    description=f"Installment #{row['id']} paid",
                    reference_type="installment",
                    reference_id=installment_id,
                )

                cursor.execute(
                    """
                    UPDATE installments
                    SET status = 'paid', paid_date = %s, transaction_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (to_iso_date(paid_date_value), tx_id, installment_id),
                )

                paid_results.append(
                    {
                        "installment_id": int(row["id"]),
                        "plan_id": int(row["plan_id"]),
                        "transaction_id": tx_id,
                        "paid_date": to_iso_date(paid_date_value),
                    }
                )

            plan_ids = {item["plan_id"] for item in paid_results}
            for plan_id in plan_ids:
                cursor.execute(
                    """
                    UPDATE installment_plans
                    SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND user_id = %s
                      AND NOT EXISTS (
                        SELECT 1
                        FROM installments i
                        WHERE i.plan_id = %s AND i.status = 'pending'
                      )
                    """,
                    (plan_id, user_id, plan_id),
                )

            conn.commit()
            return {
                "paid_count": len(paid_results),
                "installments": paid_results,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def cancel_installment_plan(user_id: int, plan_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE installment_plans
                SET status = 'canceled', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status = 'active' AND deleted_at IS NULL
                """,
                (plan_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Plan not found or cannot be canceled")
            conn.commit()
            return {"plan_id": int(plan_id), "status": "canceled"}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_upcoming_installments(user_id: int, days: int = 30) -> list[dict]:
        days = to_int(days, "days", allow_zero=True)
        window_end = date.today() + timedelta(days=days)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    i.id, i.plan_id, i.installment_number, i.amount, i.due_date, i.status,
                    i.paid_date, i.transaction_id,
                    p.title AS plan_title, p.category_id
                FROM installments i
                JOIN installment_plans p ON p.id = i.plan_id
                WHERE p.user_id = %s
                  AND p.deleted_at IS NULL
                  AND i.status = 'pending'
                  AND i.due_date >= CURRENT_DATE
                  AND i.due_date <= %s
                ORDER BY i.due_date ASC
                """,
                (user_id, to_iso_date(window_end)),
            )
            return [_row_to_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_overdue_installments(user_id: int) -> list[dict]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    i.id, i.plan_id, i.installment_number, i.amount, i.due_date, i.status,
                    p.title AS plan_title, p.category_id
                FROM installments i
                JOIN installment_plans p ON p.id = i.plan_id
                WHERE p.user_id = %s
                  AND p.deleted_at IS NULL
                  AND i.status = 'pending'
                  AND i.due_date < CURRENT_DATE
                ORDER BY i.due_date ASC
                """,
                (user_id,),
            )
            return [_row_to_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_remaining_installment_debt(user_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT COALESCE(SUM(i.amount), 0) AS remaining_amount
                FROM installments i
                JOIN installment_plans p ON p.id = i.plan_id
                WHERE p.user_id = %s
                  AND p.status = 'active'
                  AND p.deleted_at IS NULL
                  AND i.status = 'pending'
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return {"remaining_amount": float(to_decimal(row["remaining_amount"]))}
        finally:
            cursor.close()
            release_connection(conn)
