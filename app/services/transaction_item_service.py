"""Transaction item (line item) CRUD service."""

from database import get_connection, release_connection

_TX_ACCESS_WHERE = (
    "(t.wallet_id IS NULL AND t.user_id = %s) "
    "OR t.wallet_id IN ("
    "SELECT id FROM wallets WHERE user_id = %s AND deleted_at IS NULL "
    "UNION "
    "SELECT wallet_id FROM wallet_members WHERE user_id = %s)"
)


class TransactionItemService:

    # ── cursor-based helpers (caller owns the connection) ──────────────

    @staticmethod
    def create_item(cursor, transaction_id, item_data):
        """Insert a single item. Returns the new row as dict."""
        cursor.execute(
            """
            INSERT INTO transaction_items
                (transaction_id, name, quantity, unit, unit_price, total_price, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                transaction_id,
                item_data["name"],
                item_data["quantity"],
                item_data.get("unit"),
                item_data.get("unit_price"),
                item_data["total_price"],
                item_data.get("notes"),
            ),
        )
        return dict(cursor.fetchone())

    @staticmethod
    def create_items(cursor, transaction_id, items_data):
        """Bulk-insert items. Returns list of inserted rows."""
        inserted = []
        for item in items_data:
            inserted.append(
                TransactionItemService.create_item(cursor, transaction_id, item)
            )
        return inserted

    @staticmethod
    def get_items_by_transaction(cursor, transaction_id, user_id):
        """Return all active items for a transaction (ownership-checked)."""
        cursor.execute(
            f"""
            SELECT ti.*
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE ti.transaction_id = %s
              AND {_TX_ACCESS_WHERE}
              AND ti.deleted_at IS NULL
              AND t.deleted_at IS NULL
            ORDER BY ti.id
            """,
            (transaction_id, user_id, user_id, user_id),
        )
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_item(cursor, item_id, user_id):
        """Return a single item (ownership-checked). Returns None if not found."""
        cursor.execute(
            f"""
            SELECT ti.*
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE ti.id = %s
              AND {_TX_ACCESS_WHERE}
              AND ti.deleted_at IS NULL
              AND t.deleted_at IS NULL
            """,
            (item_id, user_id, user_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def soft_delete_items_by_transaction(cursor, transaction_id):
        """Soft-delete all items of a transaction."""
        cursor.execute(
            """
            UPDATE transaction_items
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE transaction_id = %s AND deleted_at IS NULL
            """,
            (transaction_id,),
        )

    @staticmethod
    def validate_items_sum(cursor, transaction_id, user_id):
        """Check that SUM(items.total_price) == transaction.amount.

        Returns (is_valid, items_sum, transaction_amount).
        If no items exist, returns (True, 0, amount).
        """
        cursor.execute(
            """
            SELECT amount FROM transactions
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            """,
            (transaction_id, user_id),
        )
        tx = cursor.fetchone()
        if tx is None:
            raise ValueError("تراکنش یافت نشد")

        cursor.execute(
            """
            SELECT COALESCE(SUM(total_price), 0) as items_sum
            FROM transaction_items
            WHERE transaction_id = %s AND deleted_at IS NULL
            """,
            (transaction_id,),
        )
        row = cursor.fetchone()
        items_sum = float(row["items_sum"])
        tx_amount = float(tx["amount"])

        return abs(items_sum - tx_amount) < 0.01, items_sum, tx_amount

    # ── standalone methods (acquire own connection) ────────────────────

    @staticmethod
    def update_item(item_id, user_id, item_data):
        """Update a single item. Returns updated row or raises ValueError."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            existing = TransactionItemService.get_item(cursor, item_id, user_id)
            if existing is None:
                raise ValueError("قلم یافت نشد")

            cursor.execute(
                """
                UPDATE transaction_items
                SET name = %s, quantity = %s, unit = %s,
                    unit_price = %s, total_price = %s, notes = %s
                WHERE id = %s AND deleted_at IS NULL
                RETURNING *
                """,
                (
                    item_data["name"],
                    item_data["quantity"],
                    item_data.get("unit"),
                    item_data.get("unit_price"),
                    item_data["total_price"],
                    item_data.get("notes"),
                    item_id,
                ),
            )
            updated = dict(cursor.fetchone())
            conn.commit()
            return updated
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def delete_item(item_id, user_id):
        """Soft-delete a single item. Raises ValueError if not found."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            existing = TransactionItemService.get_item(cursor, item_id, user_id)
            if existing is None:
                raise ValueError("قلم یافت نشد")

            cursor.execute(
                """
                UPDATE transaction_items
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND deleted_at IS NULL
                """,
                (item_id,),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def search_items(user_id, search_term, limit=50):
        """Find all transactions containing an item matching the search term."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT ti.*, t.date as transaction_date, t.amount as transaction_amount,
                       t.description as transaction_description,
                       c.name as category_name
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE {_TX_ACCESS_WHERE}
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND ti.name ILIKE %s
                ORDER BY t.date DESC
                LIMIT %s
                """,
                (user_id, user_id, user_id, f"%{search_term}%", limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_most_purchased(user_id, limit=10):
        """Most purchased items ranked by total spent."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT
                    ti.name,
                    COUNT(*) as purchase_count,
                    SUM(ti.total_price) as total_spent,
                    AVG(ti.total_price)::numeric(15,2) as avg_price,
                    AVG(ti.quantity)::numeric(10,2) as avg_quantity
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE {_TX_ACCESS_WHERE}
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                GROUP BY ti.name
                ORDER BY total_spent DESC
                LIMIT %s
                """,
                (user_id, user_id, user_id, limit),
            )
            results = []
            for r in cursor.fetchall():
                row = dict(r)
                row["total_spent"] = float(row["total_spent"])
                row["avg_price"] = float(row["avg_price"])
                row["avg_quantity"] = float(row["avg_quantity"])
                results.append(row)
            return results
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_item_stats(user_id, item_name):
        """Statistics for a specific item: avg price, monthly spending, purchase count."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Overall stats
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as purchase_count,
                    SUM(ti.total_price) as total_spent,
                    AVG(ti.total_price)::numeric(15,2) as avg_price,
                    MIN(ti.total_price) as min_price,
                    MAX(ti.total_price) as max_price,
                    MIN(t.date) as first_purchased,
                    MAX(t.date) as last_purchased
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE {_TX_ACCESS_WHERE}
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND ti.name = %s
                """,
                (user_id, user_id, user_id, item_name),
            )
            overall = cursor.fetchone()
            if overall is None or overall["purchase_count"] == 0:
                return None

            result = dict(overall)
            result["total_spent"] = float(result["total_spent"]) if result["total_spent"] else 0
            result["avg_price"] = float(result["avg_price"]) if result["avg_price"] else 0
            result["min_price"] = float(result["min_price"]) if result["min_price"] else 0
            result["max_price"] = float(result["max_price"]) if result["max_price"] else 0

            # Monthly breakdown
            cursor.execute(
                f"""
                SELECT
                    TO_CHAR(t.date, 'YYYY-MM') as month,
                    SUM(ti.total_price)::numeric(15,2) as monthly_total,
                    COUNT(*) as monthly_count
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE {_TX_ACCESS_WHERE}
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND ti.name = %s
                GROUP BY TO_CHAR(t.date, 'YYYY-MM')
                ORDER BY month DESC
                LIMIT 12
                """,
                (user_id, user_id, user_id, item_name),
            )
            monthly = []
            for r in cursor.fetchall():
                row = dict(r)
                row["monthly_total"] = float(row["monthly_total"])
                monthly.append(row)
            result["monthly_breakdown"] = monthly

            # Price history
            cursor.execute(
                f"""
                SELECT ti.total_price, ti.quantity, ti.unit_price, t.date
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE {_TX_ACCESS_WHERE}
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND ti.name = %s
                ORDER BY t.date DESC
                LIMIT 20
                """,
                (user_id, user_id, user_id, item_name),
            )
            history = []
            for r in cursor.fetchall():
                row = dict(r)
                row["total_price"] = float(row["total_price"])
                if row["unit_price"] is not None:
                    row["unit_price"] = float(row["unit_price"])
                if row["quantity"] is not None:
                    row["quantity"] = float(row["quantity"])
                history.append(row)
            result["price_history"] = history

            return result
        finally:
            cursor.close()
            release_connection(conn)
