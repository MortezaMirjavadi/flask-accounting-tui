"""Calendar service for financial events and recurrence management."""

from __future__ import annotations

import math
import psycopg2
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from database import get_connection, release_connection
from services.balance_utils import get_wallet_balance, to_decimal


ALLOWED_FREQUENCIES = ("once", "daily", "weekly", "monthly", "yearly")


@dataclass
class CalendarEvent:
    id: int
    user_id: int
    title: str
    description: Optional[str]
    amount: float
    category_id: int
    wallet_id: Optional[int]
    frequency: str
    repeat_interval: int
    start_date: str
    end_date: Optional[str]
    occurrence_limit: Optional[int]
    status: str


@dataclass
class EventInstance:
    id: int
    event_id: int
    user_id: int
    due_date: str
    title: str
    description: Optional[str]
    amount: float
    category_id: int
    category_name: str
    category_type: str
    wallet_id: Optional[int]
    status: str
    transaction_id: Optional[int]


@dataclass
class EventPayload:
    title: str
    description: Optional[str]
    amount: float
    category_id: int
    wallet_id: Optional[int]
    frequency: str
    repeat_interval: int
    start_date: str
    end_date: Optional[str]
    occurrence_limit: Optional[int]


def _iso(dte: date) -> str:
    """Convert a date object to YYYY-MM-DD."""
    return dte.strftime("%Y-%m-%d")


def _to_date(value) -> date:
    """Normalize date-like values into a :class:`datetime.date`."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    if value is None:
        raise TypeError("Date value is required")
    raise TypeError(f"Unsupported date value type: {type(value)!r}")


def _add_months(value: date, step: int) -> date:
    """Add calendar months while keeping the best possible day-of-month."""
    month_index = value.month - 1 + step
    year = value.year + month_index // 12
    month = month_index % 12 + 1

    # Keep day valid in target month.
    for day in (value.day, 28, 29, 30, 31):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 28)


class CalendarService:
    """High-level CRUD + recurrence operations for financial calendar events."""

    @staticmethod
    def get_balance_wallets(conn: psycopg2.extensions.connection) -> list[tuple]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT w.id, w.name,
                COALESCE((SELECT SUM(a.amount) FROM accounts a
                          WHERE a.wallet_id = w.id AND a.deleted_at IS NULL), 0)
                + COALESCE((SELECT SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE -t.amount END)
                            FROM transactions t
                            LEFT JOIN categories c ON c.id = t.category_id
                            WHERE t.wallet_id = w.id AND t.user_id = w.user_id
                              AND t.deleted_at IS NULL), 0)
                AS balance
            FROM wallets w
            WHERE w.deleted_at IS NULL
            """
        )
        return [(row["id"], row["name"], float(row["balance"] or 0.0)) for row in cursor.fetchall()]

    @staticmethod
    def get_active_category(cursor, category_id: int, user_id: int):
        cursor.execute(
            "SELECT id, type, name FROM categories WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (category_id, user_id),
        )
        return cursor.fetchone()

    @staticmethod
    def get_active_wallet(cursor, wallet_id: int, user_id: int):
        cursor.execute(
            "SELECT id, name FROM wallets WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (wallet_id, user_id),
        )
        return cursor.fetchone()

    @staticmethod
    def _validate_payload(user_id: int, payload: dict) -> EventPayload:
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip() or None
        amount = payload.get("amount")
        category_id = payload.get("category_id")
        wallet_id = payload.get("wallet_id")
        frequency = (payload.get("frequency") or "once").strip().lower()
        repeat_interval = payload.get("repeat_interval", 1)
        start_raw = payload.get("start_date")
        end_raw = payload.get("end_date")
        end_date = None
        occurrence_limit = payload.get("occurrence_limit")

        if not title:
            raise ValueError("عنوان الزامی است")

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("مبلغ باید عددی مثبت باشد")

        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            raise ValueError("شناسه دسته‌بندی معتبر الزامی است")

        if wallet_id is not None:
            try:
                wallet_id = int(wallet_id)
            except (TypeError, ValueError):
                raise ValueError("شناسه کیف پول باید عدد صحیح باشد")
            # Existence check only. Balance sufficiency is validated at confirm time.
            conn = get_connection()
            cursor = conn.cursor()
            try:
                if CalendarService.get_active_wallet(cursor, wallet_id, user_id) is None:
                    raise ValueError("کیف پول وجود ندارد")
            finally:
                cursor.close()
                release_connection(conn)

        if frequency not in ALLOWED_FREQUENCIES:
            raise ValueError(f"تناوب باید یکی از موارد زیر باشد: {', '.join(ALLOWED_FREQUENCIES)}")

        try:
            repeat_interval = int(repeat_interval)
            if repeat_interval < 1:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("فاصله تکرار باید بزرگتر یا مساوی ۱ باشد")

        if frequency == "once":
            repeat_interval = 1
        try:
            start = _to_date(start_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("تاریخ شروع باید به فرمت YYYY-MM-DD باشد") from exc

        today = date.today()
        if start < today:
            raise ValueError("تاریخ شروع باید امروز یا بعد باشد")

        if frequency != "once" and not description:
            raise ValueError("توضیحات برای رویدادهای تکراری الزامی است")

        if end_raw:
            try:
                end = _to_date(end_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("تاریخ پایان باید به فرمت YYYY-MM-DD باشد") from exc
            end_date = end.strftime("%Y-%m-%d")
            if end < start:
                raise ValueError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")

        if occurrence_limit is not None:
            try:
                occurrence_limit = int(occurrence_limit)
            except (TypeError, ValueError):
                raise ValueError("محدودیت تکرار باید عدد صحیح باشد")
            if occurrence_limit < 1:
                raise ValueError("محدودیت تکرار باید بزرگتر یا مساوی ۱ باشد")
            if frequency == "once" and occurrence_limit != 1:
                raise ValueError("محدودیت تکرار برای رویدادهای یکبار باید ۱ یا خالی باشد")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            if CalendarService.get_active_category(cursor, category_id, user_id) is None:
                raise ValueError("دسته‌بندی وجود ندارد")
            return EventPayload(
                title=title,
                description=description,
                amount=amount,
                category_id=category_id,
                wallet_id=wallet_id,
                frequency=frequency,
                repeat_interval=repeat_interval,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end_date,
                occurrence_limit=occurrence_limit,
            )
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def create_event(user_id: int, payload: dict) -> tuple[dict, list[dict]]:
        """Create recurring or single event and seed future due instances."""
        data = CalendarService._validate_payload(user_id, payload)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            if CalendarService._has_conflicting_instance(
                cursor,
                user_id,
                data.title,
                data.amount,
                data.start_date,
            ):
                raise ValueError("رویداد مشابهی قبلاً وجود دارد")

            cursor.execute(
                """
                INSERT INTO financial_events (
                    user_id, title, description, amount, category_id, wallet_id,
                    frequency, repeat_interval, start_date, end_date, occurrence_limit
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (
                    user_id,
                    data.title,
                    data.description,
                    data.amount,
                    data.category_id,
                    data.wallet_id,
                    data.frequency,
                    data.repeat_interval,
                    data.start_date,
                    data.end_date,
                    data.occurrence_limit,
                ),
            )
            event_id = cursor.fetchone()['id']
            conn.commit()
            CalendarService._generate_instances_for_event(
                cursor, event_id, user_id, _to_date(data.start_date), horizon_days=365
            )
            conn.commit()

            event = CalendarService._fetch_event(cursor, event_id, user_id)
            instances = CalendarService.get_instances(
                user_id, start_date=data.start_date, end_date=_iso(date.today() + timedelta(days=90))
            )
            return {
                "id": event["id"],
                "user_id": event["user_id"],
                "title": event["title"],
                "description": event["description"],
                "amount": event["amount"],
                "category_id": event["category_id"],
                "wallet_id": event["wallet_id"],
                "frequency": event["frequency"],
                "repeat_interval": event["repeat_interval"],
                "start_date": event["start_date"],
                "end_date": event["end_date"],
                "occurrence_limit": event["occurrence_limit"],
                "status": event["status"],
            }, [i for i in instances if i["event_id"] == event_id]
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def _has_conflicting_instance(
        cursor, user_id: int, title: str, amount: float, due_date: str, exclude_event_id: Optional[int] = None
    ) -> bool:
        cursor.execute(
            """
            SELECT 1
            FROM financial_event_instances i
            JOIN financial_events e ON e.id = i.event_id
            WHERE i.user_id = %s
              AND i.due_date = %s
              AND i.status IN ('pending', 'snoozed')
              AND e.status = 'active'
              AND e.title = %s
              AND ROUND(e.amount, 2) = ROUND(%s, 2)
              AND e.deleted_at IS NULL
              AND (%s IS NULL OR e.id != %s)
              LIMIT 1
            """,
            (user_id, due_date, title, amount, exclude_event_id, exclude_event_id),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _fetch_event(cursor, event_id: int, user_id: int):
        cursor.execute(
            """
            SELECT id, user_id, title, description, amount, category_id, wallet_id,
                   frequency, repeat_interval, start_date, end_date, occurrence_limit, status
            FROM financial_events
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            """,
            (event_id, user_id),
        )
        return cursor.fetchone()

    @staticmethod
    def get_event(event_id: int, user_id: int) -> dict | None:
        """Load a single event definition."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            row = CalendarService._fetch_event(cursor, event_id, user_id)
            return dict(row) if row else None
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def get_user_events(user_id: int, include_inactive=False, page=1, per_page=20) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            where_clause = " WHERE user_id = %s AND deleted_at IS NULL"
            params = [user_id]
            if not include_inactive:
                where_clause += " AND status = 'active'"

            count_sql = "SELECT COUNT(*) as total FROM financial_events" + where_clause
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            data_sql = (
                "SELECT id, user_id, title, description, amount, category_id, wallet_id,"
                " frequency, repeat_interval, start_date, end_date, occurrence_limit, status"
                " FROM financial_events" + where_clause + " ORDER BY start_date ASC, id DESC"
            )
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
            rows = [dict(row) for row in cursor.fetchall()]

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_instances(
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_cancelled: bool = False,
        wallet_id: Optional[int] = None,
    ) -> list[dict]:
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if start_date is None:
                start_date = date.today().strftime("%Y-%m-%d")
            if end_date is None:
                end_date = (date.today() + timedelta(days=90)).strftime("%Y-%m-%d")

            statuses = ("pending", "snoozed", "confirmed")
            if include_cancelled:
                statuses = ("pending", "snoozed", "confirmed", "cancelled", "skipped")

            placeholders = ",".join("%s" for _ in statuses)
            wallet_filter = ""
            params = [user_id, start_date, end_date, *statuses]
            if wallet_id is not None:
                wallet_filter = " AND e.wallet_id = %s"
                params.append(wallet_id)
            cursor.execute(
                f"""
                SELECT
                    i.id,
                    i.event_id,
                    i.user_id,
                    i.due_date,
                    i.status,
                    i.transaction_id,
                    i.snoozed_from,
                    e.title,
                    e.description,
                    e.amount,
                    e.category_id,
                    e.wallet_id,
                    c.name AS category_name,
                    COALESCE(c.type, 'cost') AS category_type
                FROM financial_event_instances i
                JOIN financial_events e ON e.id = i.event_id
                JOIN categories c ON c.id = e.category_id
                WHERE i.user_id = %s
                  AND i.due_date >= %s
                  AND i.due_date <= %s
                  AND i.status IN ({placeholders})
                  AND e.status = 'active'
                  AND e.deleted_at IS NULL{wallet_filter}
                ORDER BY i.due_date ASC, i.id ASC
                """,
                tuple(params),
            )
            return [
                {
                    "id": row["id"],
                    "event_id": row["event_id"],
                    "user_id": row["user_id"],
                    "due_date": row["due_date"],
                    "status": row["status"],
                    "transaction_id": row["transaction_id"],
                    "snoozed_from": row["snoozed_from"],
                    "title": row["title"],
                    "description": row["description"],
                    "amount": row["amount"],
                    "category_id": row["category_id"],
                    "wallet_id": row["wallet_id"],
                    "category_name": row["category_name"],
                    "category_type": row["category_type"],
                }
                for row in cursor.fetchall()
            ]
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                release_connection(conn)

    @staticmethod
    def get_instance(instance_id: int, user_id: int) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    i.id,
                    i.event_id,
                    i.user_id,
                    i.due_date,
                    i.status,
                    i.transaction_id,
                    i.snoozed_from,
                    e.title,
                    e.description,
                    e.amount,
                    e.category_id,
                    e.wallet_id,
                    c.type AS category_type,
                    c.name AS category_name
                FROM financial_event_instances i
                JOIN financial_events e ON e.id = i.event_id
                JOIN categories c ON c.id = e.category_id
                WHERE i.id = %s AND i.user_id = %s 
                """,
                (instance_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def update_event(event_id: int, user_id: int, payload: dict) -> dict:
        data = CalendarService._validate_payload(user_id, payload)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            event = CalendarService._fetch_event(cursor, event_id, user_id)
            if event is None:
                raise ValueError("رویداد یافت نشد")
            if event["status"] == "cancelled":
                raise ValueError("رویدادهای لغو شده قابل ویرایش نیستند")

            if CalendarService._has_conflicting_instance(
                cursor,
                user_id,
                data.title,
                data.amount,
                data.start_date,
                exclude_event_id=event_id,
            ):
                raise ValueError("رویداد مشابهی قبلاً وجود دارد")

            cursor.execute(
                """
                UPDATE financial_events
                SET title = %s, description = %s, amount = %s, category_id = %s, wallet_id = %s,
                    frequency = %s, repeat_interval = %s, start_date = %s, end_date = %s, occurrence_limit = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    data.title,
                    data.description,
                    data.amount,
                    data.category_id,
                    data.wallet_id,
                    data.frequency,
                    data.repeat_interval,
                    data.start_date,
                    data.end_date,
                    data.occurrence_limit,
                    event_id,
                    user_id,
                ),
            )
            cursor.execute(
                """
                UPDATE financial_event_instances
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND status IN ('pending', 'snoozed')
                """,
                (event_id,),
            )
            CalendarService._generate_instances_for_event(cursor, event_id, user_id, _to_date(data.start_date), horizon_days=365)
            conn.commit()

            updated = CalendarService._fetch_event(cursor, event_id, user_id)
            return {
                "id": updated["id"],
                "user_id": updated["user_id"],
                "title": updated["title"],
                "description": updated["description"],
                "amount": updated["amount"],
                "category_id": updated["category_id"],
                "wallet_id": updated["wallet_id"],
                "frequency": updated["frequency"],
                "repeat_interval": updated["repeat_interval"],
                "start_date": updated["start_date"],
                "end_date": updated["end_date"],
                "occurrence_limit": updated["occurrence_limit"],
                "status": updated["status"],
            }
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def cancel_event(event_id: int, user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM financial_events WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (event_id, user_id),
            )
            if cursor.fetchone() is None:
                return False
            cursor.execute(
                """
                UPDATE financial_events
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (event_id, user_id),
            )
            cursor.execute(
                """
                UPDATE financial_event_instances
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND status IN ('pending', 'snoozed')
                """,
                (event_id,),
            )
            conn.commit()
            return True
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def delete_event(event_id: int, user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE financial_events SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (event_id, user_id),
            )
            updated = cursor.rowcount
            if not updated:
                cursor.close()
                release_connection(conn)
                return False

            cursor.execute(
                "UPDATE financial_event_instances SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP "
                "WHERE event_id = %s AND status IN ('pending', 'snoozed')",
                (event_id,),
            )
            conn.commit()
            return True
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def pause_event(event_id: int, user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE financial_events
                SET status = 'paused', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status = 'active' AND deleted_at IS NULL
                """,
                (event_id, user_id),
            )
            if cursor.rowcount == 0:
                return False
            cursor.execute(
                """
                UPDATE financial_event_instances
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND status IN ('pending', 'snoozed')
                """,
                (event_id,),
            )
            conn.commit()
            return True
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def resume_event(event_id: int, user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE financial_events
                SET status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status = 'paused' AND deleted_at IS NULL
                """,
                (event_id, user_id),
            )
            if cursor.rowcount == 0:
                return False
            event = CalendarService._fetch_event(cursor, event_id, user_id)
            if event:
                CalendarService._generate_instances_for_event(
                    cursor,
                    event_id,
                    user_id,
                    start=max(_to_date(event["start_date"]), date.today()),
                )
            conn.commit()
            return True
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def snooze_instance(instance_id: int, user_id: int, new_due_date: str) -> dict:
        try:
            due = _to_date(new_due_date)
        except ValueError as exc:
            raise ValueError("تاریخ سررسید جدید باید به فرمت YYYY-MM-DD باشد") from exc
        if due < date.today():
            raise ValueError("تاریخ سررسید جدید باید امروز یا بعد باشد")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            instance = CalendarService.get_instance(instance_id, user_id)
            if instance is None:
                raise ValueError("نمونه یافت نشد")
            if instance["status"] == "confirmed":
                raise ValueError("امکان تأخیر نمونه تأیید شده وجود ندارد")
            if instance["status"] == "cancelled":
                raise ValueError("امکان تأخیر نمونه لغو شده وجود ندارد")

            if CalendarService._has_conflicting_instance(
                cursor,
                user_id,
                instance["title"],
                instance["amount"],
                new_due_date,
            ):
                raise ValueError("رویداد مشابهی قبلاً وجود دارد")

            cursor.execute(
                """
                UPDATE financial_event_instances
                SET due_date = %s, status = 'snoozed', snoozed_from = due_date, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (new_due_date, instance_id, user_id),
            )
            conn.commit()

            return CalendarService.get_instance(instance_id, user_id)
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def cancel_instance(instance_id: int, user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE financial_event_instances
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status IN ('pending', 'snoozed')
                """,
                (instance_id, user_id),
            )
            updated = cursor.rowcount
            conn.commit()
            return updated > 0
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def confirm_instance(instance_id: int, user_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    i.id,
                    i.event_id,
                    i.user_id,
                    i.due_date,
                    i.status,
                    e.title,
                    e.amount,
                    e.category_id,
                    e.wallet_id,
                    c.type AS category_type
                FROM financial_event_instances i
                JOIN financial_events e ON e.id = i.event_id
                JOIN categories c ON c.id = e.category_id
                WHERE i.id = %s AND i.user_id = %s AND i.transaction_id IS NULL
                """,
                (instance_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("نمونه یافت نشد یا قبلاً پرداخت شده است")

            if row["status"] not in ("pending", "snoozed"):
                raise ValueError("فقط نمونه‌های در انتظار یا با تأخیر قابل تأیید هستند")

            if row["category_type"] == "cost" and row["wallet_id"] is not None:
                balance = get_wallet_balance(cursor, row["wallet_id"], user_id)
                if balance < to_decimal(row["amount"]):
                    raise ValueError("موجودی کیف پول کافی نیست")

            cursor.execute(
                """
                INSERT INTO transactions (user_id, date, amount, category_id, wallet_id, description)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (
                    user_id,
                    row["due_date"],
                    row["amount"],
                    row["category_id"],
                    row["wallet_id"],
                    f"{row['title']} (Paid via calendar)",
                ),
            )
            tx_id = cursor.fetchone()['id']

            if row["wallet_id"] is not None:
                cursor.execute(
                    """
                    UPDATE wallets
                    SET amount = amount + %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (
                        row["amount"] if row["category_type"] == "income" else -row["amount"],
                        row["wallet_id"],
                        user_id,
                    ),
                )

            cursor.execute(
                """
                UPDATE financial_event_instances
                SET status = 'confirmed', transaction_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (tx_id, instance_id),
            )
            conn.commit()

            return {
                "transaction_id": tx_id,
                "instance_id": instance_id,
                "user_id": user_id,
                "date": row["due_date"],
            }
        finally:
            cursor.close()
        release_connection(conn)

    @staticmethod
    def ensure_instances(user_id: int, horizon_days: int = 365) -> int:
        """Generate missing future instances for all active events."""
        created = 0
        conn = None
        cursor = None
        today = date.today()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM financial_events
                WHERE user_id = %s AND status = 'active' AND deleted_at IS NULL
                """,
                (user_id,),
            )
            for event in cursor.fetchall():
                count_before = CalendarService._generate_instances_for_event(cursor, event["id"], user_id, today, horizon_days)
                created += count_before
            conn.commit()
            return created
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                release_connection(conn)

    @staticmethod
    def _generate_instances_for_event(
        cursor,
        event_id: int,
        user_id: int,
        start: date,
        horizon_days: int = 365,
    ) -> int:
        cursor.execute(
            "SELECT * FROM financial_events WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (event_id, user_id),
        )
        event = cursor.fetchone()
        if event is None or event["status"] != "active":
            return 0

        event_start = _to_date(event["start_date"])
        from_dt = max(event_start, start)
        end_date = _to_date(event["end_date"]) if event["end_date"] else (date.today() + timedelta(days=horizon_days))

        horizon_end = min(date.today() + timedelta(days=horizon_days), end_date)
        occurrences = 0
        if event["frequency"] == "once":
            recurrence_dates = [event_start]
        else:
            recurrence_dates = list(
                CalendarService._iter_recurrence(
                    event_start,
                    event["frequency"],
                    int(event["repeat_interval"]),
                    int(event["occurrence_limit"]) if event["occurrence_limit"] is not None else None,
                    end_date,
                )
            )

        for due in recurrence_dates:
            if due < from_dt or due > horizon_end:
                continue

            if CalendarService._instance_exists(cursor, event_id, due.strftime("%Y-%m-%d")):
                continue
            if CalendarService._has_conflicting_instance(cursor, user_id, event["title"], event["amount"], due.strftime("%Y-%m-%d")):
                continue
            cursor.execute(
                """
                INSERT INTO financial_event_instances (event_id, user_id, due_date)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (event_id, user_id, due.strftime("%Y-%m-%d")),
            )
            occurrences += 1
        return occurrences

    @staticmethod
    def _iter_recurrence(
        start: date,
        frequency: str,
        repeat_interval: int,
        occurrence_limit: Optional[int],
        end_date: Optional[date],
    ) -> Iterable[date]:
        if frequency == "once":
            yield start
            return

        current = start
        idx = 0
        while True:
            if end_date and current > end_date:
                break
            if occurrence_limit is not None and idx >= occurrence_limit:
                break

            yield current
            idx += 1

            if frequency == "daily":
                current += timedelta(days=repeat_interval)
            elif frequency == "weekly":
                current += timedelta(weeks=repeat_interval)
            elif frequency == "monthly":
                current = _add_months(current, repeat_interval)
            elif frequency == "yearly":
                try:
                    current = current.replace(year=current.year + repeat_interval)
                except ValueError:
                    current = current.replace(month=2, day=28, year=current.year + repeat_interval)
            else:
                return

    @staticmethod
    def _instance_exists(cursor, event_id: int, due_date: str) -> bool:
        cursor.execute(
            "SELECT 1 FROM financial_event_instances WHERE event_id = %s AND due_date = %s LIMIT 1",
            (event_id, due_date),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def load_events_for_forecast(user_id: int, start_date: str, end_date: str) -> list[dict]:
        """Load generated instances and fallback by static recurring pattern."""
        return CalendarService.get_instances(
            user_id,
            start_date=start_date,
            end_date=end_date,
            include_cancelled=False,
        )
