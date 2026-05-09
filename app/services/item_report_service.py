"""Item-level analytics and personal inflation tracking service."""

from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from typing import Optional

from database import get_connection, release_connection


# ── Data models ───────────────────────────────────────────────────────

@dataclass
class TopItem:
    item_name: str
    total_quantity: float
    total_spent: float
    purchase_count: int
    avg_price: float
    last_price: float


@dataclass
class PricePoint:
    date: str
    price: float
    quantity: float


@dataclass
class MonthlyBasketItem:
    month: str
    item_name: str
    total_quantity: float
    avg_price: float
    monthly_cost: float


@dataclass
class CategoryItem:
    item_name: str
    category_name: str
    total_spent: float
    total_quantity: float


@dataclass
class VelocityItem:
    item_name: str
    purchase_count: int
    avg_days_between: float
    last_purchase_date: str
    predicted_next_date: str
    monthly_estimated_cost: float


@dataclass
class SourcePrice:
    item_name: str
    source_name: str
    avg_price: float
    min_price: float
    max_price: float
    purchase_count: int


@dataclass
class InflationItem:
    item_name: str
    avg_price_t0: float
    avg_price_t1: float
    inflation_rate: float
    weight: float
    purchase_count: int


@dataclass
class InflationReport:
    items: list
    personal_cpi: float
    total_items_tracked: int
    period_months: int


# ── Service ───────────────────────────────────────────────────────────

class ItemReportService:

    # ── Report 1: Top Purchased Items ─────────────────────────────

    @staticmethod
    def get_top_items(user_id, limit=20, date_from=None, date_to=None):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    ti.name AS item_name,
                    SUM(ti.quantity)::numeric(12,2) AS total_quantity,
                    SUM(ti.total_price)::numeric(15,2) AS total_spent,
                    COUNT(*)::int AS purchase_count,
                    AVG(ti.total_price)::numeric(15,2) AS avg_price,
                    (ARRAY_AGG(ti.total_price ORDER BY t.date DESC))[1]::numeric(15,2) AS last_price
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
            """
            params = [user_id]

            if date_from:
                query += " AND t.date >= %s"
                params.append(date_from)
            if date_to:
                query += " AND t.date <= %s"
                params.append(date_to)

            query += """
                GROUP BY ti.name
                ORDER BY total_spent DESC
                LIMIT %s
            """
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(asdict(TopItem(
                    item_name=r["item_name"],
                    total_quantity=float(r["total_quantity"]),
                    total_spent=float(r["total_spent"]),
                    purchase_count=r["purchase_count"],
                    avg_price=float(r["avg_price"]),
                    last_price=float(r["last_price"]),
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Report 2: Item Price History ──────────────────────────────

    @staticmethod
    def get_price_history(user_id, item_name, limit=50):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    t.date::text AS date,
                    ti.total_price::numeric(15,2) AS price,
                    ti.quantity::numeric(10,2) AS quantity
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND ti.name = %s
                ORDER BY t.date DESC
                LIMIT %s
                """,
                (user_id, item_name, limit),
            )
            results = []
            for r in cursor.fetchall():
                results.append(asdict(PricePoint(
                    date=r["date"],
                    price=float(r["price"]),
                    quantity=float(r["quantity"]),
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Report 3: Monthly Item Basket ─────────────────────────────

    @staticmethod
    def get_monthly_basket(user_id, months=6):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cutoff = date.today() - timedelta(days=months * 30)
            cursor.execute(
                """
                SELECT
                    TO_CHAR(t.date, 'YYYY-MM') AS month,
                    ti.name AS item_name,
                    SUM(ti.quantity)::numeric(12,2) AS total_quantity,
                    AVG(ti.total_price)::numeric(15,2) AS avg_price,
                    SUM(ti.total_price)::numeric(15,2) AS monthly_cost
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND t.date >= %s
                GROUP BY TO_CHAR(t.date, 'YYYY-MM'), ti.name
                ORDER BY month DESC, monthly_cost DESC
                """,
                (user_id, cutoff),
            )
            results = []
            for r in cursor.fetchall():
                results.append(asdict(MonthlyBasketItem(
                    month=r["month"],
                    item_name=r["item_name"],
                    total_quantity=float(r["total_quantity"]),
                    avg_price=float(r["avg_price"]),
                    monthly_cost=float(r["monthly_cost"]),
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Report 4: Category-level Item Aggregation ─────────────────

    @staticmethod
    def get_items_by_category(user_id, limit=50):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    ti.name AS item_name,
                    COALESCE(c.name, 'Unknown') AS category_name,
                    SUM(ti.total_price)::numeric(15,2) AS total_spent,
                    SUM(ti.quantity)::numeric(12,2) AS total_quantity
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                GROUP BY ti.name, c.name
                ORDER BY total_spent DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            results = []
            for r in cursor.fetchall():
                results.append(asdict(CategoryItem(
                    item_name=r["item_name"],
                    category_name=r["category_name"],
                    total_spent=float(r["total_spent"]),
                    total_quantity=float(r["total_quantity"]),
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Report 5: Spending Velocity ───────────────────────────────

    @staticmethod
    def get_spending_velocity(user_id, min_purchases=3):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Find recurring items with enough purchase history
            cursor.execute(
                """
                WITH item_dates AS (
                    SELECT
                        ti.name,
                        t.date,
                        ti.total_price,
                        LAG(t.date) OVER (PARTITION BY ti.name ORDER BY t.date) AS prev_date
                    FROM transaction_items ti
                    JOIN transactions t ON ti.transaction_id = t.id
                    WHERE t.user_id = %s
                      AND ti.deleted_at IS NULL
                      AND t.deleted_at IS NULL
                ),
                item_stats AS (
                    SELECT
                        name,
                        COUNT(*) AS purchase_count,
                        AVG(total_price)::numeric(15,2) AS avg_price,
                        MAX(date) AS last_date,
                        CASE
                            WHEN COUNT(*) > 1 THEN
                                AVG(date - prev_date)
                            ELSE NULL
                        END AS avg_days_between
                    FROM item_dates
                    GROUP BY name
                    HAVING COUNT(*) >= %s
                )
                SELECT
                    name AS item_name,
                    purchase_count,
                    COALESCE(avg_days_between, 0)::numeric(8,1) AS avg_days_between,
                    last_date::text AS last_purchase_date,
                    avg_price
                FROM item_stats
                ORDER BY purchase_count DESC
                """,
                (user_id, min_purchases),
            )
            results = []
            for r in cursor.fetchall():
                avg_days = float(r["avg_days_between"])
                last_date_str = r["last_purchase_date"]
                avg_price = float(r["avg_price"])

                # Predict next purchase date
                if avg_days > 0 and last_date_str:
                    last_date = date.fromisoformat(last_date_str)
                    predicted = last_date + timedelta(days=int(avg_days))
                    predicted_str = predicted.isoformat()
                    # Estimate monthly cost: avg_price * (30 / avg_days)
                    monthly_est = round(avg_price * (30.0 / avg_days), 2)
                else:
                    predicted_str = None
                    monthly_est = 0.0

                results.append(asdict(VelocityItem(
                    item_name=r["item_name"],
                    purchase_count=r["purchase_count"],
                    avg_days_between=avg_days,
                    last_purchase_date=last_date_str,
                    predicted_next_date=predicted_str,
                    monthly_estimated_cost=monthly_est,
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Report 6: Source-based Price Comparison ───────────────────

    @staticmethod
    def get_source_prices(user_id, item_name=None):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    ti.name AS item_name,
                    COALESCE(s.name, '-') AS source_name,
                    AVG(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS avg_price,
                    MIN(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS min_price,
                    MAX(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS max_price,
                    COUNT(*)::int AS purchase_count
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                LEFT JOIN sources s ON t.source_id = s.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
            """
            params = [user_id]

            if item_name:
                query += " AND ti.name = %s"
                params.append(item_name)

            query += """
                GROUP BY ti.name, s.name
                HAVING COUNT(*) >= 1
                ORDER BY ti.name, avg_price
            """

            cursor.execute(query, params)
            results = []
            for r in cursor.fetchall():
                results.append(asdict(SourcePrice(
                    item_name=r["item_name"],
                    source_name=r["source_name"],
                    avg_price=float(r["avg_price"]),
                    min_price=float(r["min_price"]),
                    max_price=float(r["max_price"]),
                    purchase_count=r["purchase_count"],
                )))
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Personal Inflation Tracker ────────────────────────────────

    @staticmethod
    def get_personal_inflation(user_id, period_months=3, min_purchases=2):
        """
        Compute a CPI-like personal inflation index.

        1. Find items purchased in both the oldest and newest month of the period.
        2. For each item: inflation_rate = (avg_price_t1 - avg_price_t0) / avg_price_t0
        3. Weight = item total_qty / grand_total_qty
        4. Personal_CPI = SUM(inflation_rate * weight)
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Determine the period boundaries
            cutoff = date.today() - timedelta(days=period_months * 30)
            cursor.execute(
                """
                SELECT
                    MIN(DATE_TRUNC('month', t.date))::date AS period_start,
                    MAX(DATE_TRUNC('month', t.date))::date AS period_end
                FROM transaction_items ti
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE t.user_id = %s
                  AND ti.deleted_at IS NULL
                  AND t.deleted_at IS NULL
                  AND t.date >= %s
                """,
                (user_id, cutoff),
            )
            period_row = cursor.fetchone()
            if not period_row or not period_row["period_start"]:
                return asdict(InflationReport(
                    items=[], personal_cpi=0.0,
                    total_items_tracked=0, period_months=period_months,
                ))

            period_start = period_row["period_start"]
            period_end = period_row["period_end"]
            period_end_plus = period_end + timedelta(days=32)
            period_end_plus = period_end_plus.replace(day=1)  # First day of next month

            # Get item prices in T0 (first month) and T1 (last month)
            cursor.execute(
                """
                WITH monthly_prices AS (
                    SELECT
                        ti.name,
                        DATE_TRUNC('month', t.date)::date AS month_start,
                        AVG(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS avg_unit_price,
                        SUM(ti.quantity)::numeric(12,2) AS total_qty,
                        COUNT(*)::int AS cnt
                    FROM transaction_items ti
                    JOIN transactions t ON ti.transaction_id = t.id
                    WHERE t.user_id = %s
                      AND ti.deleted_at IS NULL
                      AND t.deleted_at IS NULL
                      AND t.date >= %s
                      AND t.date < %s
                    GROUP BY ti.name, DATE_TRUNC('month', t.date)
                ),
                t0 AS (
                    SELECT name, avg_unit_price, total_qty, cnt
                    FROM monthly_prices
                    WHERE month_start = %s
                ),
                t1 AS (
                    SELECT name, avg_unit_price, total_qty, cnt
                    FROM monthly_prices
                    WHERE month_start = %s
                )
                SELECT
                    t0.name AS item_name,
                    t0.avg_unit_price::numeric(15,2) AS avg_price_t0,
                    t1.avg_unit_price::numeric(15,2) AS avg_price_t1,
                    t0.total_qty + t1.total_qty AS total_qty,
                    t0.cnt + t1.cnt AS purchase_count,
                    CASE WHEN t0.avg_unit_price > 0
                        THEN ((t1.avg_unit_price - t0.avg_unit_price) / t0.avg_unit_price)::numeric(8,4)
                        ELSE 0
                    END AS inflation_rate
                FROM t0
                JOIN t1 ON t0.name = t1.name
                WHERE t0.cnt >= %s AND t1.cnt >= %s
                ORDER BY inflation_rate DESC
                """,
                (user_id, period_start, period_end_plus,
                 period_start, period_end,
                 min_purchases, min_purchases),
            )

            rows = cursor.fetchall()
            if not rows:
                return asdict(InflationReport(
                    items=[], personal_cpi=0.0,
                    total_items_tracked=0, period_months=period_months,
                ))

            grand_total_qty = sum(float(r["total_qty"]) for r in rows)

            items = []
            weighted_sum = 0.0

            for r in rows:
                total_qty = float(r["total_qty"])
                weight = total_qty / grand_total_qty if grand_total_qty > 0 else 0
                inflation_rate = float(r["inflation_rate"])
                weighted_sum += inflation_rate * weight

                items.append(asdict(InflationItem(
                    item_name=r["item_name"],
                    avg_price_t0=float(r["avg_price_t0"]),
                    avg_price_t1=float(r["avg_price_t1"]),
                    inflation_rate=round(inflation_rate, 4),
                    weight=round(weight, 4),
                    purchase_count=r["purchase_count"],
                )))

            personal_cpi = round(weighted_sum, 4)

            return asdict(InflationReport(
                items=items,
                personal_cpi=personal_cpi,
                total_items_tracked=len(items),
                period_months=period_months,
            ))
        finally:
            cursor.close()
            release_connection(conn)

    # ── Optional: Anomaly Detection ───────────────────────────────

    @staticmethod
    def detect_price_spikes(user_id, threshold=0.3, lookback_months=3):
        """Find items where the latest price is >threshold% above the average."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cutoff = date.today() - timedelta(days=lookback_months * 30)
            cursor.execute(
                """
                WITH recent_prices AS (
                    SELECT
                        ti.name,
                        ti.total_price / NULLIF(ti.quantity, 0) AS unit_price,
                        t.date,
                        ROW_NUMBER() OVER (PARTITION BY ti.name ORDER BY t.date DESC) AS rn
                    FROM transaction_items ti
                    JOIN transactions t ON ti.transaction_id = t.id
                    WHERE t.user_id = %s
                      AND ti.deleted_at IS NULL
                      AND t.deleted_at IS NULL
                      AND t.date >= %s
                ),
                item_avgs AS (
                    SELECT name, AVG(unit_price)::numeric(15,2) AS avg_price
                    FROM recent_prices
                    GROUP BY name
                    HAVING COUNT(*) >= 2
                ),
                latest_prices AS (
                    SELECT name, unit_price::numeric(15,2) AS latest_price, date::text
                    FROM recent_prices
                    WHERE rn = 1
                )
                SELECT
                    lp.name AS item_name,
                    ia.avg_price,
                    lp.latest_price,
                    lp.date AS latest_date,
                    CASE WHEN ia.avg_price > 0
                        THEN ((lp.latest_price - ia.avg_price) / ia.avg_price)::numeric(8,4)
                        ELSE 0
                    END AS change_pct
                FROM latest_prices lp
                JOIN item_avgs ia ON lp.name = ia.name
                WHERE lp.latest_price > ia.avg_price * (1 + %s)
                ORDER BY change_pct DESC
                """,
                (user_id, cutoff, threshold),
            )
            results = []
            for r in cursor.fetchall():
                results.append({
                    "item_name": r["item_name"],
                    "avg_price": float(r["avg_price"]),
                    "latest_price": float(r["latest_price"]),
                    "latest_date": r["latest_date"],
                    "change_pct": float(r["change_pct"]),
                })
            return results
        finally:
            cursor.close()
            release_connection(conn)

    # ── Optional: Best Store ──────────────────────────────────────

    @staticmethod
    def get_best_stores(user_id, limit=20):
        """For each item, find the source with the lowest average price."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                WITH source_prices AS (
                    SELECT
                        ti.name AS item_name,
                        COALESCE(s.name, '-') AS source_name,
                        AVG(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS avg_price,
                        COUNT(*)::int AS purchase_count
                    FROM transaction_items ti
                    JOIN transactions t ON ti.transaction_id = t.id
                    LEFT JOIN sources s ON t.source_id = s.id
                    WHERE t.user_id = %s
                      AND ti.deleted_at IS NULL
                      AND t.deleted_at IS NULL
                    GROUP BY ti.name, s.name
                    HAVING COUNT(*) >= 1
                ),
                ranked AS (
                    SELECT
                        item_name,
                        source_name,
                        avg_price,
                        purchase_count,
                        ROW_NUMBER() OVER (PARTITION BY item_name ORDER BY avg_price) AS rn
                    FROM source_prices
                )
                SELECT item_name, source_name, avg_price, purchase_count
                FROM ranked
                WHERE rn = 1
                ORDER BY item_name
                LIMIT %s
                """,
                (user_id, limit),
            )
            results = []
            for r in cursor.fetchall():
                results.append({
                    "item_name": r["item_name"],
                    "best_source": r["source_name"],
                    "avg_price": float(r["avg_price"]),
                    "purchase_count": r["purchase_count"],
                })
            return results
        finally:
            cursor.close()
            release_connection(conn)
