"""Debt & Receivable management service."""

import math
from datetime import date, timedelta

from database import get_connection, release_connection


class DebtService:
    """Core debt/receivable CRUD and business logic."""

    # ── Create ─────────────────────────────────────────────────────

    @staticmethod
    def create_debt(user_id, data):
        """Create a new debt or receivable. Returns (row_dict, error)."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            remaining = data["original_amount"]
            status = "active"
            due_date_val = data.get("due_date")
            if due_date_val:
                if isinstance(due_date_val, str):
                    due_date_val = date.fromisoformat(due_date_val)
                if due_date_val < date.today():
                    status = "overdue"

            cursor.execute(
                """
                INSERT INTO debts (
                    user_id, type, counterparty_name, counterparty_type,
                    title, description, original_amount, remaining_amount,
                    issue_date, due_date, status, priority,
                    wallet_id, reference_type, reference_id,
                    has_interest, interest_type, interest_rate
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING *
                """,
                (
                    user_id, data["type"], data["counterparty_name"],
                    data["counterparty_type"],
                    data["title"], data.get("description"),
                    data["original_amount"], remaining,
                    data["issue_date"], data.get("due_date"), status,
                    data["priority"],
                    data.get("wallet_id"), data.get("reference_type"),
                    data.get("reference_id"),
                    data.get("has_interest", False),
                    data.get("interest_type"), data.get("interest_rate"),
                ),
            )
            row = dict(cursor.fetchone())

            # Record initial status
            cursor.execute(
                """
                INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                VALUES (%s, NULL, %s, 'Created')
                """,
                (row["id"], status),
            )
            conn.commit()
            return row, None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    # ── Update ─────────────────────────────────────────────────────

    @staticmethod
    def update_debt(debt_id, user_id, data):
        """Update debt metadata (not amounts or status). Returns (row, error)."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            existing = DebtService._get_owned(cursor, debt_id, user_id)
            if existing is None:
                return None, "بدهی یافت نشد"
            if existing["status"] in ("settled", "cancelled", "written_off"):
                return None, f"Cannot edit a {existing['status']} debt"

            cursor.execute(
                """
                UPDATE debts SET
                    counterparty_name = %s,
                    counterparty_type = %s,
                    title = %s,
                    description = %s,
                    due_date = %s,
                    priority = %s,
                    wallet_id = %s,
                    has_interest = %s,
                    interest_type = %s,
                    interest_rate = %s
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING *
                """,
                (
                    data.get("counterparty_name", existing["counterparty_name"]),
                    data.get("counterparty_type", existing["counterparty_type"]),
                    data.get("title", existing["title"]),
                    data.get("description", existing["description"]),
                    data.get("due_date", existing["due_date"]),
                    data.get("priority", existing["priority"]),
                    data.get("wallet_id", existing["wallet_id"]),
                    data.get("has_interest", existing["has_interest"]),
                    data.get("interest_type", existing["interest_type"]),
                    data.get("interest_rate", existing["interest_rate"]),
                    debt_id, user_id,
                ),
            )
            row = dict(cursor.fetchone())
            conn.commit()
            return row, None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    # ── Get / List ─────────────────────────────────────────────────

    @staticmethod
    def get_debt(debt_id, user_id):
        """Get a single debt with payment count and total paid."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            return DebtService._get_detail(cursor, debt_id, user_id)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def list_debts(user_id, debt_type=None, status=None, counterparty=None,
                   page=1, per_page=20, wallet_id=None):
        """List debts with optional filters and pagination."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            where_clause = " WHERE d.user_id = %s AND d.deleted_at IS NULL"
            params = [user_id]

            if wallet_id:
                where_clause += " AND d.wallet_id = %s"
                params.append(wallet_id)
            if debt_type:
                where_clause += " AND d.type = %s"
                params.append(debt_type)
            if status:
                if status == "overdue":
                    where_clause += " AND d.due_date < CURRENT_DATE AND d.remaining_amount > 0 AND d.status NOT IN ('settled','cancelled','written_off')"
                else:
                    where_clause += " AND d.status = %s"
                    params.append(status)
            if counterparty:
                where_clause += " AND d.counterparty_name ILIKE %s"
                params.append(f"%{counterparty}%")

            join_clause = (
                " FROM debts d"
                " LEFT JOIN ("
                "   SELECT debt_id, COUNT(*) AS payment_count, SUM(amount) AS total_paid"
                "   FROM debt_payments WHERE deleted_at IS NULL GROUP BY debt_id"
                " ) p ON d.id = p.debt_id"
            )

            count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            data_sql = (
                "SELECT d.*, COALESCE(p.payment_count, 0) AS payment_count,"
                " COALESCE(p.total_paid, 0) AS total_paid"
                + join_clause + where_clause + " ORDER BY d.created_at DESC"
            )
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
            rows = cursor.fetchall()

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        finally:
            cursor.close()
            release_connection(conn)

    # ── Payments ───────────────────────────────────────────────────

    @staticmethod
    def register_payment(debt_id, user_id, data):
        """Register a payment against a debt. Returns (payment_dict, error)."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            debt = DebtService._get_owned(cursor, debt_id, user_id)
            if debt is None:
                return None, "بدهی یافت نشد"
            if debt["status"] in ("settled", "cancelled", "written_off"):
                return None, f"Cannot pay a {debt['status']} debt"
            if debt["remaining_amount"] <= 0:
                return None, "بدهی قبلاً کاملاً پرداخت شده است"

            amount = data["amount"]
            if amount > debt["remaining_amount"]:
                return None, (
                    f"Payment {amount} exceeds remaining {debt['remaining_amount']}. "
                    "Use the exact remaining amount to settle."
                )

            # Insert payment
            cursor.execute(
                """
                INSERT INTO debt_payments (debt_id, amount, payment_date, payment_method, wallet_id, note)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (debt_id, amount, data["payment_date"],
                 data.get("payment_method", "cash"),
                 data.get("wallet_id"), data.get("note")),
            )
            payment = dict(cursor.fetchone())

            # Update remaining amount
            new_remaining = float(debt["remaining_amount"]) - amount
            new_status = "settled" if new_remaining <= 0 else (
                "partially_paid" if new_remaining < float(debt["original_amount"]) else debt["status"]
            )

            cursor.execute(
                "UPDATE debts SET remaining_amount = %s, status = %s WHERE id = %s",
                (new_remaining, new_status, debt_id),
            )

            # Record status change
            if new_status != debt["status"]:
                cursor.execute(
                    """
                    INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (debt_id, debt["status"], new_status,
                     f"Payment of {amount} received"),
                )

            conn.commit()
            return payment, None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def reverse_payment(payment_id, user_id):
        """Reverse a payment. Returns (True, error)."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT dp.*, d.user_id, d.remaining_amount, d.original_amount,
                       d.status AS debt_status
                FROM debt_payments dp
                JOIN debts d ON dp.debt_id = d.id
                WHERE dp.id = %s AND d.user_id = %s AND dp.deleted_at IS NULL
                """,
                (payment_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "پرداخت یافت نشد"

            amount = float(row["amount"])
            debt_id = row["debt_id"]
            new_remaining = float(row["remaining_amount"]) + amount

            # Soft-delete payment
            cursor.execute(
                "UPDATE debt_payments SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
                (payment_id,),
            )

            # Update debt
            new_status = "active" if new_remaining >= float(row["original_amount"]) else (
                "partially_paid" if new_remaining > 0 else "settled"
            )
            cursor.execute(
                "UPDATE debts SET remaining_amount = %s, status = %s WHERE id = %s",
                (new_remaining, new_status, debt_id),
            )

            cursor.execute(
                """
                INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                VALUES (%s, %s, %s, %s)
                """,
                (debt_id, row["debt_status"], new_status,
                 f"Payment #{payment_id} reversed ({amount})"),
            )

            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_payments(debt_id, user_id):
        """Get all payments for a debt."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Verify ownership
            debt = DebtService._get_owned(cursor, debt_id, user_id)
            if debt is None:
                return None, "بدهی یافت نشد"

            cursor.execute(
                """
                SELECT * FROM debt_payments
                WHERE debt_id = %s AND deleted_at IS NULL
                ORDER BY payment_date DESC
                """,
                (debt_id,),
            )
            return [dict(r) for r in cursor.fetchall()], None
        finally:
            cursor.close()
            release_connection(conn)

    # ── Status Transitions ─────────────────────────────────────────

    @staticmethod
    def write_off(debt_id, user_id, note=None):
        """Mark a debt as written off (uncollectible)."""
        return DebtService._transition(debt_id, user_id, "written_off",
                                        note or "Written off as uncollectible")

    @staticmethod
    def cancel_debt(debt_id, user_id, note=None):
        """Cancel a debt (erroneous or cancelled by agreement)."""
        return DebtService._transition(debt_id, user_id, "cancelled",
                                        note or "Cancelled")

    @staticmethod
    def settle_manually(debt_id, user_id, note=None):
        """Manually mark a debt as settled."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            debt = DebtService._get_owned(cursor, debt_id, user_id)
            if debt is None:
                return None, "بدهی یافت نشد"
            if debt["remaining_amount"] > 0:
                # Zero out remaining as adjustment
                cursor.execute(
                    "UPDATE debts SET remaining_amount = 0, status = 'settled' WHERE id = %s",
                    (debt_id,),
                )
            else:
                cursor.execute(
                    "UPDATE debts SET status = 'settled' WHERE id = %s",
                    (debt_id,),
                )
            cursor.execute(
                """
                INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                VALUES (%s, %s, 'settled', %s)
                """,
                (debt_id, debt["status"], note or "Manually settled"),
            )
            conn.commit()
            debt["status"] = "settled"
            debt["remaining_amount"] = 0
            return debt, None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def sync_statuses(user_id):
        """Auto-update overdue statuses for all active debts past due date."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE debts
                SET status = 'overdue'
                WHERE user_id = %s
                  AND deleted_at IS NULL
                  AND status = 'active'
                  AND due_date IS NOT NULL
                  AND due_date < CURRENT_DATE
                  AND remaining_amount > 0
                RETURNING id
                """,
                (user_id,),
            )
            updated_ids = [r["id"] for r in cursor.fetchall()]

            for debt_id in updated_ids:
                cursor.execute(
                    """
                    INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                    VALUES (%s, 'active', 'overdue', 'Auto-detected overdue')
                    """,
                    (debt_id,),
                )

            conn.commit()
            return len(updated_ids), None
        except Exception as exc:
            conn.rollback()
            return 0, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    # ── Analytics / Summary ────────────────────────────────────────

    @staticmethod
    def get_summary(user_id, wallet_id=None):
        """Debt dashboard summary."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Sync overdue first
            DebtService.sync_statuses(user_id)

            wallet_filter = ""
            params = [user_id]
            if wallet_id:
                wallet_filter = " AND wallet_id = %s"
                params.append(wallet_id)

            cursor.execute(
                f"""
                SELECT
                    type,
                    status,
                    COUNT(*)::int AS count,
                    SUM(remaining_amount)::numeric(15,2) AS total_remaining,
                    SUM(original_amount)::numeric(15,2) AS total_original
                FROM debts
                WHERE user_id = %s AND deleted_at IS NULL
                  AND status NOT IN ('settled', 'cancelled', 'written_off'){wallet_filter}
                GROUP BY type, status
                """,
                tuple(params),
            )
            rows = [dict(r) for r in cursor.fetchall()]

            receivable_total = 0
            payable_total = 0
            overdue_count = 0
            overdue_amount = 0
            by_status = {}

            for r in rows:
                amt = float(r["total_remaining"])
                if r["type"] == "receivable":
                    receivable_total += amt
                else:
                    payable_total += amt
                if r["status"] == "overdue":
                    overdue_count += r["count"]
                    overdue_amount += amt
                by_status.setdefault(r["type"], {})[r["status"]] = {
                    "count": r["count"],
                    "total_remaining": amt,
                    "total_original": float(r["total_original"]),
                }

            # Due soon (next 7 days)
            cursor.execute(
                """
                SELECT COUNT(*)::int AS count,
                       COALESCE(SUM(remaining_amount), 0)::numeric(15,2) AS total
                FROM debts
                WHERE user_id = %s AND deleted_at IS NULL
                  AND status IN ('active', 'partially_paid', 'overdue')
                  AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
                """,
                (user_id,),
            )
            due_soon = dict(cursor.fetchone())

            # Recent payments
            cursor.execute(
                """
                SELECT dp.amount, dp.payment_date, dp.payment_method,
                       d.title, d.type, d.counterparty_name
                FROM debt_payments dp
                JOIN debts d ON dp.debt_id = d.id
                WHERE d.user_id = %s AND dp.deleted_at IS NULL
                ORDER BY dp.payment_date DESC
                LIMIT 5
                """,
                (user_id,),
            )
            recent_payments = [dict(r) for r in cursor.fetchall()]

            return {
                "receivable_total": receivable_total,
                "payable_total": payable_total,
                "net_position": receivable_total - payable_total,
                "overdue_count": overdue_count,
                "overdue_amount": overdue_amount,
                "due_soon": due_soon,
                "by_status": by_status,
                "recent_payments": recent_payments,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_overdue(user_id, wallet_id=None):
        """List overdue debts."""
        DebtService.sync_statuses(user_id)
        return DebtService.list_debts(user_id, status="overdue", wallet_id=wallet_id)

    @staticmethod
    def get_due_soon(user_id, days=7, wallet_id=None):
        """List debts due within N days."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            end_date = date.today() + timedelta(days=days)
            wallet_filter = ""
            params = [user_id, end_date]
            if wallet_id:
                wallet_filter = " AND d.wallet_id = %s"
                params.append(wallet_id)
            cursor.execute(
                f"""
                SELECT d.*,
                       COALESCE(p.payment_count, 0) AS payment_count,
                       COALESCE(p.total_paid, 0) AS total_paid
                FROM debts d
                LEFT JOIN (
                    SELECT debt_id, COUNT(*) AS payment_count, SUM(amount) AS total_paid
                    FROM debt_payments WHERE deleted_at IS NULL
                    GROUP BY debt_id
                ) p ON d.id = p.debt_id
                WHERE d.user_id = %s AND d.deleted_at IS NULL
                  AND d.status IN ('active', 'partially_paid', 'overdue')
                  AND d.due_date IS NOT NULL
                  AND d.due_date BETWEEN CURRENT_DATE AND %s{wallet_filter}
                ORDER BY d.due_date
                """,
                tuple(params),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_status_history(debt_id, user_id):
        """Get status change history for a debt."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            debt = DebtService._get_owned(cursor, debt_id, user_id)
            if debt is None:
                return None, "بدهی یافت نشد"
            cursor.execute(
                """
                SELECT * FROM debt_status_history
                WHERE debt_id = %s
                ORDER BY changed_at
                """,
                (debt_id,),
            )
            return [dict(r) for r in cursor.fetchall()], None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_counterparty_balance(user_id, counterparty_name):
        """Get all debts and net balance for a specific counterparty."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT d.*,
                       COALESCE(p.total_paid, 0) AS total_paid
                FROM debts d
                LEFT JOIN (
                    SELECT debt_id, SUM(amount) AS total_paid
                    FROM debt_payments WHERE deleted_at IS NULL
                    GROUP BY debt_id
                ) p ON d.id = p.debt_id
                WHERE d.user_id = %s AND d.deleted_at IS NULL
                  AND d.counterparty_name = %s
                  AND d.status NOT IN ('cancelled', 'written_off')
                ORDER BY d.issue_date
                """,
                (user_id, counterparty_name),
            )
            rows = [dict(r) for r in cursor.fetchall()]

            receivable = sum(float(r["remaining_amount"]) for r in rows if r["type"] == "receivable")
            payable = sum(float(r["remaining_amount"]) for r in rows if r["type"] == "payable")

            return {
                "counterparty": counterparty_name,
                "debts": rows,
                "total_receivable": receivable,
                "total_payable": payable,
                "net_balance": receivable - payable,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_aging_report(user_id):
        """Aging report: current, 1-30, 31-60, 61-90, 90+ days overdue."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    type,
                    CASE
                        WHEN due_date IS NULL THEN 'no_due_date'
                        WHEN due_date >= CURRENT_DATE THEN 'current'
                        WHEN due_date >= CURRENT_DATE - INTERVAL '30 days' THEN '1_30'
                        WHEN due_date >= CURRENT_DATE - INTERVAL '60 days' THEN '31_60'
                        WHEN due_date >= CURRENT_DATE - INTERVAL '90 days' THEN '61_90'
                        ELSE '90_plus'
                    END AS age_bucket,
                    COUNT(*)::int AS count,
                    SUM(remaining_amount)::numeric(15,2) AS total_remaining
                FROM debts
                WHERE user_id = %s AND deleted_at IS NULL
                  AND status NOT IN ('settled', 'cancelled', 'written_off')
                GROUP BY type, age_bucket
                ORDER BY type, age_bucket
                """,
                (user_id,),
            )
            rows = [dict(r) for r in cursor.fetchall()]

            result = {"receivable": {}, "payable": {}}
            for r in rows:
                bucket = r["age_bucket"]
                result[r["type"]][bucket] = {
                    "count": r["count"],
                    "total": float(r["total_remaining"]),
                }
            return result
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_monthly_repayments(user_id, months=6):
        """Repayments grouped by month."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cutoff = date.today() - timedelta(days=months * 30)
            cursor.execute(
                """
                SELECT
                    TO_CHAR(dp.payment_date, 'YYYY-MM') AS month,
                    d.type,
                    COUNT(*)::int AS payment_count,
                    SUM(dp.amount)::numeric(15,2) AS total_amount
                FROM debt_payments dp
                JOIN debts d ON dp.debt_id = d.id
                WHERE d.user_id = %s AND dp.deleted_at IS NULL
                  AND dp.payment_date >= %s
                GROUP BY TO_CHAR(dp.payment_date, 'YYYY-MM'), d.type
                ORDER BY month DESC
                """,
                (user_id, cutoff),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_top_counterparties(user_id, limit=10):
        """Top counterparties by outstanding balance."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    counterparty_name,
                    type,
                    COUNT(*)::int AS debt_count,
                    SUM(remaining_amount)::numeric(15,2) AS total_remaining,
                    SUM(original_amount)::numeric(15,2) AS total_original
                FROM debts
                WHERE user_id = %s AND deleted_at IS NULL
                  AND status NOT IN ('settled', 'cancelled', 'written_off')
                GROUP BY counterparty_name, type
                ORDER BY total_remaining DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    # ── Internal helpers ───────────────────────────────────────────

    @staticmethod
    def _get_owned(cursor, debt_id, user_id):
        cursor.execute(
            "SELECT * FROM debts WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (debt_id, user_id),
        )
        return cursor.fetchone()

    @staticmethod
    def _get_detail(cursor, debt_id, user_id):
        debt = DebtService._get_owned(cursor, debt_id, user_id)
        if debt is None:
            return None
        d = dict(debt)
        cursor.execute(
            """
            SELECT COUNT(*)::int AS count, COALESCE(SUM(amount), 0)::numeric(15,2) AS total
            FROM debt_payments
            WHERE debt_id = %s AND deleted_at IS NULL
            """,
            (debt_id,),
        )
        stats = cursor.fetchone()
        d["payment_count"] = stats["count"]
        d["total_paid"] = float(stats["total"])
        return d

    @staticmethod
    def _transition(debt_id, user_id, new_status, note):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            debt = DebtService._get_owned(cursor, debt_id, user_id)
            if debt is None:
                return None, "بدهی یافت نشد"
            if debt["status"] == new_status:
                return None, f"Debt is already {new_status}"

            cursor.execute(
                "UPDATE debts SET status = %s WHERE id = %s",
                (new_status, debt_id),
            )
            cursor.execute(
                """
                INSERT INTO debt_status_history (debt_id, old_status, new_status, note)
                VALUES (%s, %s, %s, %s)
                """,
                (debt_id, debt["status"], new_status, note),
            )
            conn.commit()
            debt = dict(debt)
            debt["status"] = new_status
            return debt, None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)
