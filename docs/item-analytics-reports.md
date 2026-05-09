# Item Analytics & Personal Inflation Tracker

## Overview

A comprehensive item-level analytics and personal inflation tracking system built on top of the `transaction_items` table. It provides 9 reports, a CPI-like personal inflation index, anomaly detection, and a full TUI dashboard.

---

## Why This Matters: Business Value

Most personal finance tools stop at the transaction level — they tell you *how much* you spent at the supermarket, but not *what* you bought. This feature goes one level deeper. By tracking individual line items inside each transaction, it answers questions that transaction-level data alone cannot.

### The Problem It Solves

You know you spent 850,000 at the supermarket last week. But without item-level data, you cannot answer:

- Is milk getting more expensive, or are you just buying more of it?
- Which store sells chicken at the best price?
- How much do you spend on groceries every month, broken down by product?
- When will you need to buy rice again based on your consumption pattern?
- Is your personal cost of living rising faster than the official inflation rate?

This system captures line items at the point of transaction entry and turns them into actionable financial intelligence.

### What Each Report Covers


| #   | Report                         | What It Answers                                                           | Who Benefits                                                                     |
| --- | ------------------------------ | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 1   | **Top Purchased Items**        | Which products do you spend the most on overall?                          | Anyone who wants to understand where the money actually goes at a product level  |
| 2   | **Item Price History**         | How has the price of a specific item changed over time?                   | Anyone tracking whether a product is getting more expensive at their usual store |
| 3   | **Monthly Item Basket**        | What does your typical monthly shopping basket look like?                 | Budget-conscious households that want to plan monthly grocery spending           |
| 4   | **Category-Level Items**       | Which items drive spending in each category (groceries, household, etc.)? | Anyone who wants to see the breakdown behind their category totals               |
| 5   | **Spending Velocity**          | How often do you buy each item, and when will you need it next?           | Anyone who wants to predict recurring expenses and plan purchases                |
| 6   | **Price Comparison by Store**  | Where is each product cheapest?                                           | Anyone who shops at multiple stores and wants to optimize spending               |
| 7   | **Personal Inflation Tracker** | Is your personal cost of living rising? By how much?                      | Anyone who suspects prices are rising faster than they realize                   |
| 8   | **Price Spike Alerts**         | Which items suddenly got much more expensive?                             | Anyone who wants early warning when a product they buy regularly jumps in price  |
| 9   | **Best Store per Item**        | For each product, which store offers the lowest average price?            | Anyone who wants a data-driven shopping strategy                                 |


### Practical Scenarios

**Scenario 1 — Budget Planning:**
You want to set a realistic monthly grocery budget. Instead of guessing, you look at the Monthly Basket report and see that your household consistently spends around 3,200,000/month on groceries, with milk, chicken, rice, and bread accounting for 60% of that. You set your budget at 3,500,000 with confidence.

**Scenario 2 — Inflation Awareness:**
You suspect prices are going up. The Personal Inflation Tracker confirms your suspicion — your weighted personal inflation is +11.8% over the last 3 months, driven by a 19% spike in egg prices and 15% in chicken. You now have concrete data to adjust your budget or change suppliers.

**Scenario 3 — Smart Shopping:**
You buy milk from two different stores. The Price Comparison report shows that Store A averages 60,000 per unit while Store B averages 55,000. Over 12 purchases, that is a 60,000 difference — small per purchase but meaningful over a year. The Best Store report makes this visible at a glance.

**Scenario 4 — Consumption Forecasting:**
The Spending Velocity report shows you buy rice every 35 days on average, last purchased 20 days ago. The predicted next purchase is in 15 days. You also see that your monthly rice cost is approximately 97,000. This helps you plan cash flow and avoid last-minute purchases at inconvenient (expensive) stores.

**Scenario 5 — Anomaly Detection:**
You normally pay 62,000 for a dozen eggs. This week the Price Spike Alert flags eggs at 78,000 — a 25% jump. Without this alert, you might not notice the increase until you review your monthly spending. With it, you can investigate whether it is a temporary spike or a permanent price change and adjust accordingly.

---

## Architecture

```
┌──────────────┐     HTTP      ┌──────────────────┐     SQL      ┌─────────────────┐
│   TUI Screen │ ──────────► │  Flask Route      │ ──────────► │  Service Layer   │
│  (Textual)   │ ◄────────── │  (Blueprint)      │ ◄────────── │  (psycopg2)      │
└──────────────┘   JSON       └──────────────────┘   rows       └─────────────────┘
                                                                            │
                                                                            ▼
                                                                   ┌─────────────────┐
                                                                   │   PostgreSQL     │
                                                                   │ transaction_items│
                                                                   │ transactions     │
                                                                   │ categories       │
                                                                   │ sources          │
                                                                   └─────────────────┘
```

### Files


| File                                  | Purpose                                                   |
| ------------------------------------- | --------------------------------------------------------- |
| `app/services/item_report_service.py` | Service layer — all SQL queries and business logic        |
| `app/routes/reports.py`               | Flask API endpoints (added to existing reports blueprint) |
| `tui/screens/item_reports.py`         | TUI screens — menu + detail views                         |
| `tui/screens/reports.py`              | Updated to include "Item Analytics" menu option           |
| `tui/sidebar_menu.py`                 | Updated sidebar menu with item analytics entry            |


---

## Database Schema

The reports query these existing tables:

```sql
-- transaction_items (line items)
CREATE TABLE transaction_items (
    id            SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    quantity      NUMERIC(10,2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit          VARCHAR(50),
    unit_price    NUMERIC(15,2),
    total_price   NUMERIC(15,2) NOT NULL CHECK (total_price >= 0),
    notes         TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at    TIMESTAMP
);

CREATE INDEX idx_transaction_items_transaction ON transaction_items(transaction_id);
```

### Recommended Additional Indexes

```sql
-- Speed up item name lookups (search, grouping, inflation)
CREATE INDEX idx_transaction_items_name ON transaction_items(name)
    WHERE deleted_at IS NULL;

-- Speed up date-range queries on transactions
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date)
    WHERE deleted_at IS NULL;

-- Composite index for common join pattern
CREATE INDEX idx_transaction_items_txn_name
    ON transaction_items(transaction_id, name)
    WHERE deleted_at IS NULL;
```

---

## API Endpoints

All endpoints are prefixed with `/reports` (registered on the existing reports blueprint).

Authentication: `X-Username` header (resolved to `user_id` server-side).

---

### 1. Top Purchased Items

**Endpoint:** `GET /reports/items/top`

**Query Parameters:**


| Param   | Type | Default | Description         |
| ------- | ---- | ------- | ------------------- |
| `limit` | int  | 20      | Max items to return |


**Response Schema:**

```json
[
  {
    "item_name": "milk",
    "total_quantity": 24.0,
    "total_spent": 2880000.0,
    "purchase_count": 12,
    "avg_price": 120000.0,
    "last_price": 130000.0
  }
]
```

**Service Method:** `ItemReportService.get_top_items(user_id, limit, date_from, date_to)`

**SQL:**

```sql
SELECT
    ti.name AS item_name,
    SUM(ti.quantity)::numeric(12,2)          AS total_quantity,
    SUM(ti.total_price)::numeric(15,2)      AS total_spent,
    COUNT(*)::int                            AS purchase_count,
    AVG(ti.total_price)::numeric(15,2)       AS avg_price,
    (ARRAY_AGG(ti.total_price ORDER BY t.date DESC))[1]::numeric(15,2) AS last_price
FROM transaction_items ti
JOIN transactions t ON ti.transaction_id = t.id
WHERE t.user_id = %s
  AND ti.deleted_at IS NULL
  AND t.deleted_at IS NULL
GROUP BY ti.name
ORDER BY total_spent DESC
LIMIT %s
```

**Dataclass:** `TopItem`


| Field            | Type  | Description                                 |
| ---------------- | ----- | ------------------------------------------- |
| `item_name`      | str   | Item name                                   |
| `total_quantity` | float | Sum of all quantities purchased             |
| `total_spent`    | float | Sum of all total_price values               |
| `purchase_count` | int   | Number of transactions containing this item |
| `avg_price`      | float | Average total_price per purchase            |
| `last_price`     | float | Most recent total_price                     |


---

### 2. Item Price History

**Endpoint:** `GET /reports/items/price-history`

**Query Parameters:**


| Param   | Type   | Default | Required | Description             |
| ------- | ------ | ------- | -------- | ----------------------- |
| `name`  | string | —       | yes      | Item name (exact match) |
| `limit` | int    | 50      | no       | Max records             |


**Response Schema:**

```json
[
  {
    "date": "2026-05-01",
    "price": 130000.0,
    "quantity": 2.0
  },
  {
    "date": "2026-04-15",
    "price": 120000.0,
    "quantity": 1.0
  }
]
```

**Service Method:** `ItemReportService.get_price_history(user_id, item_name, limit)`

**SQL:**

```sql
SELECT
    t.date::text           AS date,
    ti.total_price::numeric(15,2)  AS price,
    ti.quantity::numeric(10,2)     AS quantity
FROM transaction_items ti
JOIN transactions t ON ti.transaction_id = t.id
WHERE t.user_id = %s
  AND ti.deleted_at IS NULL
  AND t.deleted_at IS NULL
  AND ti.name = %s
ORDER BY t.date DESC
LIMIT %s
```

**Dataclass:** `PricePoint`


| Field      | Type  | Description                   |
| ---------- | ----- | ----------------------------- |
| `date`     | str   | Transaction date (YYYY-MM-DD) |
| `price`    | float | Item total_price at that date |
| `quantity` | float | Quantity purchased            |


---

### 3. Monthly Item Basket

**Endpoint:** `GET /reports/items/monthly-basket`

**Query Parameters:**


| Param    | Type | Default | Description                   |
| -------- | ---- | ------- | ----------------------------- |
| `months` | int  | 6       | Number of months to look back |


**Response Schema:**

```json
[
  {
    "month": "2026-05",
    "item_name": "milk",
    "total_quantity": 4.0,
    "avg_price": 120000.0,
    "monthly_cost": 480000.0
  },
  {
    "month": "2026-05",
    "item_name": "bread",
    "total_quantity": 8.0,
    "avg_price": 40000.0,
    "monthly_cost": 320000.0
  }
]
```

**Service Method:** `ItemReportService.get_monthly_basket(user_id, months)`

**SQL:**

```sql
SELECT
    TO_CHAR(t.date, 'YYYY-MM') AS month,
    ti.name                    AS item_name,
    SUM(ti.quantity)::numeric(12,2)     AS total_quantity,
    AVG(ti.total_price)::numeric(15,2)  AS avg_price,
    SUM(ti.total_price)::numeric(15,2)  AS monthly_cost
FROM transaction_items ti
JOIN transactions t ON ti.transaction_id = t.id
WHERE t.user_id = %s
  AND ti.deleted_at IS NULL
  AND t.deleted_at IS NULL
  AND t.date >= %s   -- computed as: today - (months * 30) days
GROUP BY TO_CHAR(t.date, 'YYYY-MM'), ti.name
ORDER BY month DESC, monthly_cost DESC
```

**Dataclass:** `MonthlyBasketItem`


| Field            | Type  | Description              |
| ---------------- | ----- | ------------------------ |
| `month`          | str   | YYYY-MM                  |
| `item_name`      | str   | Item name                |
| `total_quantity` | float | Total qty that month     |
| `avg_price`      | float | Average price that month |
| `monthly_cost`   | float | Total cost that month    |


---

### 4. Category-Level Item Aggregation

**Endpoint:** `GET /reports/items/by-category`

**Query Parameters:**


| Param   | Type | Default | Description         |
| ------- | ---- | ------- | ------------------- |
| `limit` | int  | 50      | Max items to return |


**Response Schema:**

```json
[
  {
    "item_name": "chicken",
    "category_name": "Groceries",
    "total_spent": 4800000.0,
    "total_quantity": 20.0
  }
]
```

**Service Method:** `ItemReportService.get_items_by_category(user_id, limit)`

**SQL:**

```sql
SELECT
    ti.name                     AS item_name,
    COALESCE(c.name, 'Unknown') AS category_name,
    SUM(ti.total_price)::numeric(15,2)  AS total_spent,
    SUM(ti.quantity)::numeric(12,2)     AS total_quantity
FROM transaction_items ti
JOIN transactions t ON ti.transaction_id = t.id
LEFT JOIN categories c ON t.category_id = c.id
WHERE t.user_id = %s
  AND ti.deleted_at IS NULL
  AND t.deleted_at IS NULL
GROUP BY ti.name, c.name
ORDER BY total_spent DESC
LIMIT %s
```

**Dataclass:** `CategoryItem`


| Field            | Type  | Description                               |
| ---------------- | ----- | ----------------------------------------- |
| `item_name`      | str   | Item name                                 |
| `category_name`  | str   | Category the transaction belongs to       |
| `total_spent`    | float | Total spent on this item in this category |
| `total_quantity` | float | Total quantity                            |


---

### 5. Spending Velocity (Consumption Speed)

**Endpoint:** `GET /reports/items/velocity`

**Query Parameters:**


| Param           | Type | Default | Description                          |
| --------------- | ---- | ------- | ------------------------------------ |
| `min_purchases` | int  | 3       | Minimum purchases to include an item |


**Response Schema:**

```json
[
  {
    "item_name": "milk",
    "purchase_count": 12,
    "avg_days_between": 28.5,
    "last_purchase_date": "2026-05-01",
    "predicted_next_date": "2026-05-29",
    "monthly_estimated_cost": 128000.0
  }
]
```

**Service Method:** `ItemReportService.get_spending_velocity(user_id, min_purchases)`

**SQL:**

```sql
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
        COUNT(*)        AS purchase_count,
        AVG(total_price)::numeric(15,2) AS avg_price,
        MAX(date)       AS last_date,
        CASE WHEN COUNT(*) > 1
            THEN AVG(date - prev_date)
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
```

**Post-processing (Python):**

```python
# Predict next purchase
predicted = last_date + timedelta(days=int(avg_days))

# Estimate monthly cost
monthly_est = avg_price * (30.0 / avg_days)
```

**Dataclass:** `VelocityItem`


| Field                    | Type        | Description                                      |
| ------------------------ | ----------- | ------------------------------------------------ |
| `item_name`              | str         | Item name                                        |
| `purchase_count`         | int         | Number of purchases                              |
| `avg_days_between`       | float       | Average days between consecutive purchases       |
| `last_purchase_date`     | str         | Date of most recent purchase                     |
| `predicted_next_date`    | str or null | Predicted next purchase date                     |
| `monthly_estimated_cost` | float       | Estimated monthly cost based on consumption rate |


---

### 6. Source-Based Price Comparison

**Endpoint:** `GET /reports/items/price-comparison`

**Query Parameters:**


| Param  | Type   | Default | Description                               |
| ------ | ------ | ------- | ----------------------------------------- |
| `name` | string | null    | Filter to a specific item name (optional) |


**Response Schema:**

```json
[
  {
    "item_name": "milk",
    "source_name": "Supermarket A",
    "avg_price": 60000.0,
    "min_price": 55000.0,
    "max_price": 65000.0,
    "purchase_count": 8
  },
  {
    "item_name": "milk",
    "source_name": "Supermarket B",
    "avg_price": 58000.0,
    "min_price": 55000.0,
    "max_price": 62000.0,
    "purchase_count": 4
  }
]
```

**Service Method:** `ItemReportService.get_source_prices(user_id, item_name)`

**SQL:**

```sql
SELECT
    ti.name                      AS item_name,
    COALESCE(s.name, '-')        AS source_name,
    AVG(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS avg_price,
    MIN(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS min_price,
    MAX(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS max_price,
    COUNT(*)::int                AS purchase_count
FROM transaction_items ti
JOIN transactions t ON ti.transaction_id = t.id
LEFT JOIN sources s ON t.source_id = s.id
WHERE t.user_id = %s
  AND ti.deleted_at IS NULL
  AND t.deleted_at IS NULL
  [AND ti.name = %s]  -- optional filter
GROUP BY ti.name, s.name
ORDER BY ti.name, avg_price
```

**Dataclass:** `SourcePrice`


| Field            | Type  | Description                       |
| ---------------- | ----- | --------------------------------- |
| `item_name`      | str   | Item name                         |
| `source_name`    | str   | Source/store name                 |
| `avg_price`      | float | Average unit price at this source |
| `min_price`      | float | Lowest unit price seen            |
| `max_price`      | float | Highest unit price seen           |
| `purchase_count` | int   | Times purchased at this source    |


---

### 7. Personal Inflation Tracker

**Endpoint:** `GET /reports/inflation/personal`

**Query Parameters:**


| Param           | Type | Default | Description                             |
| --------------- | ---- | ------- | --------------------------------------- |
| `period_months` | int  | 3       | Lookback period in months               |
| `min_purchases` | int  | 2       | Min purchases per month to include item |


**Response Schema:**

```json
{
  "items": [
    {
      "item_name": "milk",
      "avg_price_t0": 120000.0,
      "avg_price_t1": 138000.0,
      "inflation_rate": 0.15,
      "weight": 0.35,
      "purchase_count": 6
    },
    {
      "item_name": "bread",
      "avg_price_t0": 38000.0,
      "avg_price_t1": 41000.0,
      "inflation_rate": 0.0789,
      "weight": 0.25,
      "purchase_count": 4
    }
  ],
  "personal_cpi": 0.1182,
  "total_items_tracked": 5,
  "period_months": 3
}
```

**Service Method:** `ItemReportService.get_personal_inflation(user_id, period_months, min_purchases)`

#### Algorithm

1. **Determine period boundaries:** Find the earliest and latest months with transaction data within the lookback window.
2. **Compute monthly average unit prices:** For each item, compute `AVG(total_price / quantity)` grouped by month.
3. **Identify T0 and T1:** T0 = first month in period, T1 = last month in period.
4. **Calculate per-item inflation:**
  ```
   inflation_rate = (avg_price_t1 - avg_price_t0) / avg_price_t0
  ```
5. **Calculate item weight:**
  ```
   weight = item_total_qty / grand_total_qty
  ```
   Where `grand_total_qty` is the sum of all tracked items' quantities across both months.
6. **Compute Personal CPI:**
  ```
   Personal_CPI = SUM(inflation_rate * weight)
  ```

**SQL (main query):**

```sql
WITH monthly_prices AS (
    SELECT
        ti.name,
        DATE_TRUNC('month', t.date)::date          AS month_start,
        AVG(ti.total_price / NULLIF(ti.quantity, 0))::numeric(15,2) AS avg_unit_price,
        SUM(ti.quantity)::numeric(12,2)             AS total_qty,
        COUNT(*)::int                               AS cnt
    FROM transaction_items ti
    JOIN transactions t ON ti.transaction_id = t.id
    WHERE t.user_id = %s
      AND ti.deleted_at IS NULL
      AND t.deleted_at IS NULL
      AND t.date >= %s    -- period_start
      AND t.date < %s     -- period_end + 1 month
    GROUP BY ti.name, DATE_TRUNC('month', t.date)
),
t0 AS (
    SELECT name, avg_unit_price, total_qty, cnt
    FROM monthly_prices WHERE month_start = %s  -- period_start
),
t1 AS (
    SELECT name, avg_unit_price, total_qty, cnt
    FROM monthly_prices WHERE month_start = %s  -- period_end
)
SELECT
    t0.name AS item_name,
    t0.avg_unit_price::numeric(15,2) AS avg_price_t0,
    t1.avg_unit_price::numeric(15,2) AS avg_price_t1,
    t0.total_qty + t1.total_qty      AS total_qty,
    t0.cnt + t1.cnt                  AS purchase_count,
    CASE WHEN t0.avg_unit_price > 0
        THEN ((t1.avg_unit_price - t0.avg_unit_price) / t0.avg_unit_price)::numeric(8,4)
        ELSE 0
    END AS inflation_rate
FROM t0
JOIN t1 ON t0.name = t1.name
WHERE t0.cnt >= %s AND t1.cnt >= %s  -- min_purchases
ORDER BY inflation_rate DESC
```

**Dataclasses:**

`InflationItem`:


| Field            | Type  | Description                                      |
| ---------------- | ----- | ------------------------------------------------ |
| `item_name`      | str   | Item name                                        |
| `avg_price_t0`   | float | Average unit price at start of period            |
| `avg_price_t1`   | float | Average unit price at end of period              |
| `inflation_rate` | float | (T1 - T0) / T0, e.g. 0.15 = +15%                 |
| `weight`         | float | This item's share of total consumption (0.0–1.0) |
| `purchase_count` | int   | Total purchases across both months               |


`InflationReport`:


| Field                 | Type                | Description                      |
| --------------------- | ------------------- | -------------------------------- |
| `items`               | list[InflationItem] | Per-item inflation breakdown     |
| `personal_cpi`        | float               | Weighted personal inflation rate |
| `total_items_tracked` | int                 | Number of items that qualified   |
| `period_months`       | int                 | Lookback period used             |


---

### 8. Price Spike Detection (Anomaly Alerts)

**Endpoint:** `GET /reports/inflation/spikes`

**Query Parameters:**


| Param             | Type  | Default | Description                                                      |
| ----------------- | ----- | ------- | ---------------------------------------------------------------- |
| `threshold`       | float | 0.3     | Alert if latest price is this fraction above average (0.3 = 30%) |
| `lookback_months` | int   | 3       | Months of history to analyze                                     |


**Response Schema:**

```json
[
  {
    "item_name": "eggs",
    "avg_price": 62000.0,
    "latest_price": 78000.0,
    "latest_date": "2026-05-05",
    "change_pct": 0.2581
  }
]
```

**Service Method:** `ItemReportService.detect_price_spikes(user_id, threshold, lookback_months)`

**SQL:**

```sql
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
      AND t.date >= %s  -- lookback cutoff
),
item_avgs AS (
    SELECT name, AVG(unit_price)::numeric(15,2) AS avg_price
    FROM recent_prices
    GROUP BY name
    HAVING COUNT(*) >= 2
),
latest_prices AS (
    SELECT name, unit_price::numeric(15,2) AS latest_price, date::text
    FROM recent_prices WHERE rn = 1
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
WHERE lp.latest_price > ia.avg_price * (1 + %s)  -- threshold
ORDER BY change_pct DESC
```

---

### 9. Best Store per Item

**Endpoint:** `GET /reports/items/best-stores`

**Query Parameters:**


| Param   | Type | Default | Description         |
| ------- | ---- | ------- | ------------------- |
| `limit` | int  | 20      | Max items to return |


**Response Schema:**

```json
[
  {
    "item_name": "milk",
    "best_source": "Supermarket B",
    "avg_price": 58000.0,
    "purchase_count": 4
  }
]
```

**Service Method:** `ItemReportService.get_best_stores(user_id, limit)`

**SQL:**

```sql
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
),
ranked AS (
    SELECT
        item_name, source_name, avg_price, purchase_count,
        ROW_NUMBER() OVER (PARTITION BY item_name ORDER BY avg_price) AS rn
    FROM source_prices
)
SELECT item_name, source_name, avg_price, purchase_count
FROM ranked
WHERE rn = 1
ORDER BY item_name
LIMIT %s
```

Uses `ROW_NUMBER()` window function to pick the cheapest source per item.

---

## TUI Screens

### Navigation

```
Sidebar
  └── Reports & Analysis
        └── Reports
              ├── Dashboard (existing)
              └── Item Analytics & Inflation    ← NEW
                    ├── 1. Top Purchased Items
                    ├── 2. Spending Velocity
                    ├── 3. Personal Inflation Tracker
                    ├── 4. Price Comparison by Store
                    ├── 5. Price Spike Alerts
                    ├── 6. Monthly Item Basket
                    └── 7. Best Store per Item
```

### ItemReportsScreen (Menu)

- `Escape` — back
- `1`–`7` — quick select a report
- `Enter` — select highlighted item

### ItemReportViewScreen (Detail)

- `Tab` — next report type
- `Shift+Tab` — previous report type
- `R` — refresh current report
- `Escape` — back to menu

### TUI Display Examples

**Top Purchased Items:**

```
TOP PURCHASED ITEMS
──────────────────────────────────────────────────────────────────────────────
Item                 Qty           Spent   Count       Avg Price     Last Price
──────────────────────────────────────────────────────────────────────────────
milk                 24.0    2,880,000.0      12      120,000.0     130,000.0
chicken              10.0    4,000,000.0      10      400,000.0     420,000.0
bread                48.0    1,920,000.0      24       80,000.0      85,000.0
──────────────────────────────────────────────────────────────────────────────
Total items tracked: 3
```

**Spending Velocity:**

```
SPENDING VELOCITY (Consumption Speed)
──────────────────────────────────────────────────────────────────────────────
Item               Count  Avg Days  Last Purchased    Next Predicted    Monthly Est
──────────────────────────────────────────────────────────────────────────────
milk                   12      28.5   2026-05-01        2026-05-29       128,000.0
bread                  24      14.2   2026-05-05        2026-05-19       170,000.0
──────────────────────────────────────────────────────────────────────────────
Estimated monthly recurring cost: 298,000.0
```

**Personal Inflation:**

```
PERSONAL INFLATION TRACKER
──────────────────────────────────────────────────────────────────────
Item              Avg Price (T0)  Current (T1)     Change   Weight
──────────────────────────────────────────────────────────────────────
milk                   120,000.0     138,000.0   +15.0%    35.0%
bread                   38,000.0      41,000.0    +7.9%    25.0%
eggs                    62,000.0      74,000.0   +19.4%    20.0%
chicken                210,000.0     242,000.0   +15.2%    15.0%
rice                    97,000.0      99,000.0    +2.1%     5.0%
──────────────────────────────────────────────────────────────────────
Weighted Personal Inflation: +13.2%
Items tracked: 5  |  Period: 3 months

PRICE SPIKE ALERTS (>20% above average):
──────────────────────────────────────────────────────────────────────
  ⚠  eggs                avg:    62,000.0  now:    74,000.0  +19.4%
```

**Price Comparison:**

```
PRICE COMPARISON BY STORE
──────────────────────────────────────────────────────────────────────
Item                Store                Avg          Min          Max  Count
──────────────────────────────────────────────────────────────────────
milk                Supermarket A    60,000.0    55,000.0    65,000.0      8
milk                Supermarket B    58,000.0    55,000.0    62,000.0      4
──────────────────────────────────────────────────────────────────────
chicken             Supermarket A   210,000.0   195,000.0   225,000.0      6
chicken             Butcher         190,000.0   180,000.0   200,000.0      4
```

---

## Service Layer Reference

### Class: `ItemReportService`

File: `app/services/item_report_service.py`

All methods are `@staticmethod`. Methods that need their own connection acquire it via `get_connection()` / `release_connection()`. All use parameterized queries (no SQL injection).


| Method                                                          | Returns                   | Connection | Notes                                         |
| --------------------------------------------------------------- | ------------------------- | ---------- | --------------------------------------------- |
| `get_top_items(user_id, limit, date_from, date_to)`             | `list[TopItem]`           | Own        | Supports date range filtering                 |
| `get_price_history(user_id, item_name, limit)`                  | `list[PricePoint]`        | Own        | Exact name match                              |
| `get_monthly_basket(user_id, months)`                           | `list[MonthlyBasketItem]` | Own        | Uses Python-computed cutoff date              |
| `get_items_by_category(user_id, limit)`                         | `list[CategoryItem]`      | Own        | Joins categories via transactions             |
| `get_spending_velocity(user_id, min_purchases)`                 | `list[VelocityItem]`      | Own        | Uses LAG() window function                    |
| `get_source_prices(user_id, item_name)`                         | `list[SourcePrice]`       | Own        | Optional item_name filter                     |
| `get_personal_inflation(user_id, period_months, min_purchases)` | `InflationReport`         | Own        | Two-query approach: find period, then compute |
| `detect_price_spikes(user_id, threshold, lookback_months)`      | `list[dict]`              | Own        | ROW_NUMBER() for latest price                 |
| `get_best_stores(user_id, limit)`                               | `list[dict]`              | Own        | ROW_NUMBER() to pick cheapest source          |


### Connection Pattern

```python
conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute(query, params)
    results = [process(row) for row in cursor.fetchall()]
    return results
finally:
    cursor.close()
    release_connection(conn)
```

No explicit `commit()` needed — all reports are read-only.

---

## Error Handling

All endpoints follow this pattern:

```python
try:
    result = ItemReportService.some_method(user_id, ...)
    return jsonify(result)
except Exception as exc:
    return jsonify({"error": str(exc)}), 400
```


| Error                  | Status | Cause                                      |
| ---------------------- | ------ | ------------------------------------------ |
| Missing required param | 400    | e.g. `name` not provided for price-history |
| No data found          | 200    | Returns empty list `[]`                    |
| Database error         | 400    | Exception message in response              |


---

## Caching & Performance Notes

1. **No server-side caching** is currently implemented. All queries hit the database on every request.
2. **Recommended caching strategy:**
  - Cache `get_top_items` and `get_personal_inflation` results for 5–15 minutes (these are expensive aggregate queries).
  - Use a simple dict cache keyed by `(user_id, endpoint, params)`.
  - Invalidate on transaction/item CRUD operations.
3. **Query optimization:**
  - All queries filter on `deleted_at IS NULL` to exclude soft-deleted records.
  - The `transaction_items.name` column is used extensively for GROUP BY — an index on `(name) WHERE deleted_at IS NULL` is recommended.
  - Date range queries benefit from an index on `transactions(user_id, date)`.
4. **Pagination:** Not currently implemented. All reports return full result sets limited by `LIMIT`. For large datasets, add `OFFSET`/`LIMIT` pagination.

---

## Usage Examples

### curl

```bash
# Top 10 purchased items
curl -H "X-Username: john" "http://localhost:5000/reports/items/top?limit=10"

# Price history for milk
curl -H "X-Username: john" "http://localhost:5000/reports/items/price-history?name=milk"

# Personal inflation (last 6 months, min 1 purchase per month)
curl -H "X-Username: john" "http://localhost:5000/reports/inflation/personal?period_months=6&min_purchases=1"

# Price spikes (alert if >20% above average)
curl -H "X-Username: john" "http://localhost:5000/reports/inflation/spikes?threshold=0.2"

# Best store for each item
curl -H "X-Username: john" "http://localhost:5000/reports/items/best-stores"
```

### TUI

1. Open the TUI: `python run_tui.py`
2. Navigate to **Reports & Analysis** > **Reports** > **Item Analytics & Inflation**
3. Select any report from the menu
4. Use **Tab** / **Shift+Tab** to switch between report views
5. Press **R** to refresh data
6. Press **Escape** to go back

