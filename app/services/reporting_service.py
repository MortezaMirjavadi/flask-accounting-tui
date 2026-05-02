from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date as gregorian_date, datetime, timedelta
from typing import Optional

import jdatetime

from app.utils.helpers import gregorian_to_jalali, jalali_to_gregorian
from database import get_connection, release_connection


def _to_float(value):
    return float(value) if value is not None else 0.0


@dataclass
class ReportTransaction:
    id: int
    date: str
    weekday: str
    amount: float
    category_id: Optional[int]
    category_name: str
    category_type: str
    source_name: str
    description: str


@dataclass
class CategoryAmount:
    category_id: Optional[int]
    category_name: str
    category_type: str
    amount: float


@dataclass
class DailyComparison:
    previous_7_day_avg_expense: float
    difference: float
    percent_change: Optional[float]


@dataclass
class MonthlyBudgetUsageStatus:
    consumed_amount: float
    planned_amount: float
    percent_consumed: float


@dataclass
class DailyReport:
    date: str
    weekday: str
    total_income: float
    total_expenses: float
    net: float
    category_breakdown: list[CategoryAmount]
    top_spending_category: Optional[CategoryAmount]
    last_5_transactions: list[ReportTransaction]
    comparison_vs_previous_7_days_avg: DailyComparison
    current_month_budget_usage_status: MonthlyBudgetUsageStatus


@dataclass
class WeeklyComparison:
    previous_week_expenses: float
    current_week_expenses: float
    percent_change: Optional[float]


@dataclass
class WeeklyReport:
    start_date: str
    end_date: str
    total_income: float
    total_expenses: float
    net: float
    average_daily_expense: float
    top_5_categories_by_spending: list[CategoryAmount]
    comparison_vs_last_week: WeeklyComparison
    ascii_bar_chart: str


@dataclass
class MonthlySummary:
    total_income: float
    total_expenses: float
    net: float
    savings_rate: float


@dataclass
class MonthlyCategoryBreakdown:
    category_id: Optional[int]
    category_name: str
    planned_amount: float
    actual_amount: float
    remaining: float
    percent_used: float
    status_indicator: str


@dataclass
class MonthlyBudgetHealth:
    categories_over_budget: int
    categories_close_to_limit: int
    highest_deviation_category: Optional[str]
    highest_deviation_amount: float


@dataclass
class SourceHealth:
    source_id: int
    source_name: str
    starting_balance: float
    ending_balance: float
    balance_change: float


@dataclass
class TrendAnalysis:
    spending_change_percent: Optional[float]
    income_change_percent: Optional[float]
    highest_changed_category: Optional[str]
    highest_changed_category_amount: float
    highest_changed_category_percent: Optional[float]


@dataclass
class SpendingVelocity:
    velocity: float
    forecast: float
    predicted_budget_overrun_amount: float


@dataclass
class MonthlyReport:
    year: int
    month: int
    month_label: str
    summary: MonthlySummary
    category_breakdown: list[MonthlyCategoryBreakdown]
    budget_health: MonthlyBudgetHealth
    source_health: list[SourceHealth]
    trend_analysis: TrendAnalysis
    spending_velocity: SpendingVelocity
    smart_insights: list[str] = field(default_factory=list)


class ReportingService:
    _JALALI_WEEKDAYS = ("Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

    @staticmethod
    def _weekday_name_from_jalali_date(jalali_date: str) -> str:
        try:
            jalali_date_obj = jdatetime.date.fromisoformat(jalali_date)
            return ReportingService._JALALI_WEEKDAYS[jalali_date_obj.weekday()]
        except (ValueError, TypeError):
            return ""

    @staticmethod
    def get_daily_report(user_id: int, date: str) -> DailyReport:
        greg_date = jalali_to_gregorian(date)
        conn = get_connection()
        cursor = conn.cursor()
        weekday_name = ReportingService._weekday_name_from_jalali_date(date)
        records = ReportingService._fetch_transactions(cursor, user_id, greg_date, greg_date)
        monthly_usage = ReportingService._get_month_budget_usage(cursor, user_id, date)
        previous_avg = ReportingService._get_previous_7_day_avg_expense(cursor, user_id, greg_date)
        cursor.close()
        release_connection(conn)

        income = sum(record.amount for record in records if record.category_type == "income")
        expenses = sum(record.amount for record in records if record.category_type == "cost")
        categories = ReportingService._category_breakdown(records)
        top_spending = ReportingService._top_spending_category(records)
        last_five = sorted(records, key=lambda item: (item.date, item.id), reverse=True)[:5]

        percent_change = None
        if previous_avg > 0:
            percent_change = ((expenses - previous_avg) / previous_avg) * 100

        return DailyReport(
            date=date,
            weekday=weekday_name,
            total_income=income,
            total_expenses=expenses,
            net=income - expenses,
            category_breakdown=categories,
            top_spending_category=top_spending,
            last_5_transactions=last_five,
            comparison_vs_previous_7_days_avg=DailyComparison(
                previous_7_day_avg_expense=previous_avg,
                difference=expenses - previous_avg,
                percent_change=percent_change,
            ),
            current_month_budget_usage_status=monthly_usage,
        )

    @staticmethod
    def get_weekly_report(user_id: int, start_date: str) -> WeeklyReport:
        greg_start = datetime.strptime(jalali_to_gregorian(start_date), "%Y-%m-%d").date()
        greg_end = greg_start + timedelta(days=6)
        conn = get_connection()
        cursor = conn.cursor()

        records = ReportingService._fetch_transactions(
            cursor, user_id, greg_start.strftime("%Y-%m-%d"), greg_end.strftime("%Y-%m-%d")
        )
        previous_start = greg_start - timedelta(days=7)
        previous_end = greg_start - timedelta(days=1)
        previous_records = ReportingService._fetch_transactions(
            cursor, user_id, previous_start.strftime("%Y-%m-%d"), previous_end.strftime("%Y-%m-%d")
        )
        cursor.close()
        release_connection(conn)

        income = sum(record.amount for record in records if record.category_type == "income")
        expenses = sum(record.amount for record in records if record.category_type == "cost")
        previous_expenses = sum(record.amount for record in previous_records if record.category_type == "cost")
        percent_change = None
        if previous_expenses > 0:
            percent_change = ((expenses - previous_expenses) / previous_expenses) * 100

        top_categories = ReportingService._category_spending(records)[:5]

        return WeeklyReport(
            start_date=start_date,
            end_date=gregorian_to_jalali(greg_end.strftime("%Y-%m-%d")),
            total_income=income,
            total_expenses=expenses,
            net=income - expenses,
            average_daily_expense=expenses / 7,
            top_5_categories_by_spending=top_categories,
            comparison_vs_last_week=WeeklyComparison(
                previous_week_expenses=previous_expenses,
                current_week_expenses=expenses,
                percent_change=percent_change,
            ),
            ascii_bar_chart=ReportingService._ascii_bar_chart(top_categories),
        )

    @staticmethod
    def get_monthly_report(user_id: int, year: int, month: int) -> MonthlyReport:
        month_start, month_end, total_days = ReportingService._jalali_month_range(year, month)
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        prev_start, prev_end, _ = ReportingService._jalali_month_range(prev_year, prev_month)

        conn = get_connection()
        cursor = conn.cursor()
        current_records = ReportingService._fetch_transactions(cursor, user_id, month_start, month_end)
        previous_records = ReportingService._fetch_transactions(cursor, user_id, prev_start, prev_end)
        budget_rows = ReportingService._fetch_budget_rows(cursor, user_id, year, month)
        source_health = ReportingService._build_source_health(cursor, user_id, month_start, month_end)
        cursor.close()
        release_connection(conn)

        total_income = sum(record.amount for record in current_records if record.category_type == "income")
        total_expenses = sum(record.amount for record in current_records if record.category_type == "cost")
        net = total_income - total_expenses
        savings_rate = (net / total_income) if total_income > 0 else 0.0

        category_breakdown = ReportingService._build_monthly_category_breakdown(current_records, budget_rows)
        budget_health = ReportingService._build_budget_health(category_breakdown)
        trend_analysis = ReportingService._build_trend_analysis(current_records, previous_records)
        velocity = ReportingService._build_spending_velocity(
            current_records, budget_rows, year, month, total_days
        )
        insights = ReportingService._build_monthly_insights(
            trend_analysis, velocity, budget_health, category_breakdown
        )

        return MonthlyReport(
            year=year,
            month=month,
            month_label=f"{year:04d}/{month:02d}",
            summary=MonthlySummary(
                total_income=total_income,
                total_expenses=total_expenses,
                net=net,
                savings_rate=savings_rate,
            ),
            category_breakdown=category_breakdown,
            budget_health=budget_health,
            source_health=source_health,
            trend_analysis=trend_analysis,
            spending_velocity=velocity,
            smart_insights=insights,
        )

    @staticmethod
    def _fetch_transactions(cursor, user_id: int, start_date: str, end_date: str) -> list[ReportTransaction]:
        cursor.execute(
            """
            SELECT
                t.id,
                t.date,
                t.amount,
                t.description,
                t.category_id,
                COALESCE(c.name, 'Unknown') AS category_name,
                COALESCE(c.type, 'cost') AS category_type,
                COALESCE(s.name, '-') AS source_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN sources s ON t.source_id = s.id
            WHERE t.user_id = %s
              AND t.deleted_at IS NULL
              AND t.date >= %s
              AND t.date <= %s
            ORDER BY t.date DESC, t.id DESC
            """,
            (user_id, start_date, end_date),
        )
        rows = cursor.fetchall()
        return [
            ReportTransaction(
                id=row["id"],
                date=gregorian_to_jalali(row["date"]),
                weekday=ReportingService._weekday_name_from_jalali_date(gregorian_to_jalali(row["date"])),
                amount=_to_float(row["amount"]),
                category_id=row["category_id"],
                category_name=row["category_name"] or "Unknown",
                category_type=row["category_type"] or "cost",
                source_name=row["source_name"] or "-",
                description=row["description"] or "",
            )
            for row in rows
        ]

    @staticmethod
    def _category_breakdown(records: list[ReportTransaction]) -> list[CategoryAmount]:
        totals: dict[tuple[Optional[int], str, str], float] = {}
        for record in records:
            key = (record.category_id, record.category_name, record.category_type)
            totals[key] = totals.get(key, 0.0) + record.amount
        return [
            CategoryAmount(category_id=key[0], category_name=key[1], category_type=key[2], amount=amount)
            for key, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ]

    @staticmethod
    def _category_spending(records: list[ReportTransaction]) -> list[CategoryAmount]:
        totals: dict[tuple[Optional[int], str, str], float] = {}
        for record in records:
            if record.category_type != "cost":
                continue
            key = (record.category_id, record.category_name, record.category_type)
            totals[key] = totals.get(key, 0.0) + record.amount
        return [
            CategoryAmount(category_id=key[0], category_name=key[1], category_type=key[2], amount=amount)
            for key, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ]

    @staticmethod
    def _top_spending_category(records: list[ReportTransaction]) -> Optional[CategoryAmount]:
        spending = ReportingService._category_spending(records)
        return spending[0] if spending else None

    @staticmethod
    def _get_previous_7_day_avg_expense(cursor, user_id: int, greg_date: str) -> float:
        current = datetime.strptime(greg_date, "%Y-%m-%d").date()
        totals = []
        for offset in range(1, 8):
            day = current - timedelta(days=offset)
            day_str = day.strftime("%Y-%m-%d")
            cursor.execute(
                """
                SELECT COALESCE(SUM(t.amount), 0) AS total
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s
                  AND t.deleted_at IS NULL
                  AND t.date = %s
                  AND c.type = 'cost'
                """,
                (user_id, day_str),
            )
            row = cursor.fetchone()
            totals.append(_to_float(row["total"]) if row else 0.0)
        return sum(totals) / 7

    @staticmethod
    def _get_month_budget_usage(cursor, user_id: int, jalali_date: str) -> MonthlyBudgetUsageStatus:
        year = int(jalali_date[:4])
        month = int(jalali_date[5:7])
        month_start, month_end, _ = ReportingService._jalali_month_range(year, month)
        budget_rows = ReportingService._fetch_budget_rows(cursor, user_id, year, month)
        planned = sum(_to_float(row["planned_amount"]) for row in budget_rows)

        cursor.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s
              AND t.deleted_at IS NULL
              AND t.date >= %s
              AND t.date <= %s
              AND c.type = 'cost'
            """,
            (user_id, month_start, month_end),
        )
        row = cursor.fetchone()
        consumed = _to_float(row["total"]) if row else 0.0
        percent = (consumed / planned * 100) if planned > 0 else 0.0
        return MonthlyBudgetUsageStatus(
            consumed_amount=consumed,
            planned_amount=planned,
            percent_consumed=percent,
        )

    @staticmethod
    def _fetch_budget_rows(cursor, user_id: int, year: int, month: int) -> list[dict]:
        cursor.execute(
            """
            SELECT
                bi.category_id,
                COALESCE(c.name, 'Unknown') AS category_name,
                COALESCE(c.type, 'cost') AS category_type,
                bi.planned_amount
            FROM budget_periods bp
            JOIN budget_items bi ON bp.id = bi.budget_period_id
            LEFT JOIN categories c ON bi.category_id = c.id
            WHERE bp.user_id = %s
              AND bp.year = %s
              AND bp.month = %s
              AND bp.deleted_at IS NULL
              AND bi.deleted_at IS NULL
            """,
            (user_id, year, month),
        )
        budget_rows = []
        for row in cursor.fetchall():
            item = dict(row)
            item["planned_amount"] = _to_float(item.get("planned_amount"))
            budget_rows.append(item)
        return budget_rows

    @staticmethod
    def _build_monthly_category_breakdown(
        records: list[ReportTransaction], budget_rows: list[dict]
    ) -> list[MonthlyCategoryBreakdown]:
        actuals: dict[Optional[int], float] = {}
        names: dict[Optional[int], str] = {}
        for record in records:
            if record.category_type != "cost":
                continue
            actuals[record.category_id] = actuals.get(record.category_id, 0.0) + record.amount
            names[record.category_id] = record.category_name

        merged: dict[Optional[int], MonthlyCategoryBreakdown] = {}
        for row in budget_rows:
            planned = _to_float(row["planned_amount"])
            actual = actuals.get(row["category_id"], 0.0)
            merged[row["category_id"]] = ReportingService._make_monthly_category_row(
                row["category_id"], row["category_name"], planned, actual
            )

        for category_id, actual in actuals.items():
            if category_id in merged:
                continue
            merged[category_id] = ReportingService._make_monthly_category_row(
                category_id, names.get(category_id, "Unknown"), 0.0, actual
            )

        return sorted(merged.values(), key=lambda item: item.actual_amount, reverse=True)

    @staticmethod
    def _make_monthly_category_row(category_id, category_name, planned, actual):
        remaining = planned - actual
        if planned > 0:
            percent_used = (actual / planned) * 100
        else:
            percent_used = 100.0 if actual > 0 else 0.0

        if percent_used > 100:
            status = "OVER"
        elif percent_used > 80:
            status = "CLOSE"
        else:
            status = "OK"

        return MonthlyCategoryBreakdown(
            category_id=category_id,
            category_name=category_name,
            planned_amount=planned,
            actual_amount=actual,
            remaining=remaining,
            percent_used=percent_used,
            status_indicator=status,
        )

    @staticmethod
    def _build_budget_health(rows: list[MonthlyCategoryBreakdown]) -> MonthlyBudgetHealth:
        over_budget = [row for row in rows if row.status_indicator == "OVER"]
        close = [row for row in rows if row.status_indicator == "CLOSE"]
        highest = max(rows, key=lambda item: item.actual_amount - item.planned_amount, default=None)
        highest_name = highest.category_name if highest else None
        highest_amount = (highest.actual_amount - highest.planned_amount) if highest else 0.0
        return MonthlyBudgetHealth(
            categories_over_budget=len(over_budget),
            categories_close_to_limit=len(close),
            highest_deviation_category=highest_name,
            highest_deviation_amount=highest_amount,
        )

    @staticmethod
    def _build_source_health(cursor, user_id: int, start_date: str, end_date: str) -> list[SourceHealth]:
        cursor.execute(
            "SELECT id, name, amount FROM sources WHERE user_id = %s AND deleted_at IS NULL ORDER BY name",
            (user_id,),
        )
        sources = cursor.fetchall()
        period_delta = ReportingService._source_delta_map(cursor, user_id, start_date, end_date)
        after_delta = ReportingService._source_delta_after_map(cursor, user_id, end_date)

        results = []
        for source in sources:
            source_id = source["id"]
            current_amount = _to_float(source["amount"])
            ending_balance = current_amount - after_delta.get(source_id, 0.0)
            balance_change = period_delta.get(source_id, 0.0)
            starting_balance = ending_balance - balance_change
            results.append(
                SourceHealth(
                    source_id=source_id,
                    source_name=source["name"],
                    starting_balance=starting_balance,
                    ending_balance=ending_balance,
                    balance_change=balance_change,
                )
            )
        return results

    @staticmethod
    def _source_delta_map(cursor, user_id: int, start_date: str, end_date: str) -> dict[int, float]:
        deltas: dict[int, float] = {}

        cursor.execute(
            """
            SELECT
                t.source_id AS source_id,
                SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE -t.amount END) AS delta
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s
              AND t.deleted_at IS NULL
              AND t.source_id IS NOT NULL
              AND t.date >= %s
              AND t.date <= %s
            GROUP BY t.source_id
            """,
            (user_id, start_date, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        cursor.execute(
            """
            SELECT from_source_id AS source_id, SUM(-amount) AS delta
            FROM transfers
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND date >= %s
              AND date <= %s
            GROUP BY from_source_id
            """,
            (user_id, start_date, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        cursor.execute(
            """
            SELECT to_source_id AS source_id, SUM(amount) AS delta
            FROM transfers
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND date >= %s
              AND date <= %s
            GROUP BY to_source_id
            """,
            (user_id, start_date, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        return deltas

    @staticmethod
    def _source_delta_after_map(cursor, user_id: int, end_date: str) -> dict[int, float]:
        deltas: dict[int, float] = {}

        cursor.execute(
            """
            SELECT
                t.source_id AS source_id,
                SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE -t.amount END) AS delta
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s
              AND t.deleted_at IS NULL
              AND t.source_id IS NOT NULL
              AND t.date > %s
            GROUP BY t.source_id
            """,
            (user_id, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        cursor.execute(
            """
            SELECT from_source_id AS source_id, SUM(-amount) AS delta
            FROM transfers
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND date > %s
            GROUP BY from_source_id
            """,
            (user_id, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        cursor.execute(
            """
            SELECT to_source_id AS source_id, SUM(amount) AS delta
            FROM transfers
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND date > %s
            GROUP BY to_source_id
            """,
            (user_id, end_date),
        )
        for row in cursor.fetchall():
            deltas[row["source_id"]] = (
                deltas.get(row["source_id"], 0.0) + _to_float(row["delta"])
            )

        return deltas

    @staticmethod
    def _build_trend_analysis(
        current_records: list[ReportTransaction], previous_records: list[ReportTransaction]
    ) -> TrendAnalysis:
        current_expenses = sum(item.amount for item in current_records if item.category_type == "cost")
        previous_expenses = sum(item.amount for item in previous_records if item.category_type == "cost")
        current_income = sum(item.amount for item in current_records if item.category_type == "income")
        previous_income = sum(item.amount for item in previous_records if item.category_type == "income")

        spending_change = None
        if previous_expenses > 0:
            spending_change = ((current_expenses - previous_expenses) / previous_expenses) * 100
        income_change = None
        if previous_income > 0:
            income_change = ((current_income - previous_income) / previous_income) * 100

        current_by_cat = {item.category_name: item.amount for item in ReportingService._category_spending(current_records)}
        previous_by_cat = {item.category_name: item.amount for item in ReportingService._category_spending(previous_records)}
        all_names = set(current_by_cat) | set(previous_by_cat)

        highest_name = None
        highest_amount = 0.0
        highest_percent = None
        for name in all_names:
            current_val = current_by_cat.get(name, 0.0)
            previous_val = previous_by_cat.get(name, 0.0)
            delta = current_val - previous_val
            if highest_name is None or abs(delta) > abs(highest_amount):
                highest_name = name
                highest_amount = delta
                if previous_val > 0:
                    highest_percent = (delta / previous_val) * 100
                else:
                    highest_percent = None

        return TrendAnalysis(
            spending_change_percent=spending_change,
            income_change_percent=income_change,
            highest_changed_category=highest_name,
            highest_changed_category_amount=highest_amount,
            highest_changed_category_percent=highest_percent,
        )

    @staticmethod
    def _build_spending_velocity(
        current_records: list[ReportTransaction], budget_rows: list[dict], year: int, month: int, total_days: int
    ) -> SpendingVelocity:
        today_jalali = jdatetime.date.fromgregorian(date=gregorian_date.today())
        days_passed = total_days
        if today_jalali.year == year and today_jalali.month == month:
            days_passed = max(1, today_jalali.day)

        spent_so_far = sum(item.amount for item in current_records if item.category_type == "cost")
        velocity = spent_so_far / max(days_passed, 1)
        forecast = velocity * total_days
        planned_total = sum(_to_float(row["planned_amount"]) for row in budget_rows)
        overrun = max(0.0, forecast - planned_total)
        return SpendingVelocity(
            velocity=velocity,
            forecast=forecast,
            predicted_budget_overrun_amount=overrun,
        )

    @staticmethod
    def _build_monthly_insights(
        trend: TrendAnalysis,
        velocity: SpendingVelocity,
        budget_health: MonthlyBudgetHealth,
        category_rows: list[MonthlyCategoryBreakdown],
    ) -> list[str]:
        insights: list[str] = []

        if trend.highest_changed_category and trend.highest_changed_category_percent is not None:
            verb = "increased" if trend.highest_changed_category_amount > 0 else "decreased"
            insights.append(
                f"{trend.highest_changed_category} spending {verb} {abs(trend.highest_changed_category_percent):.1f}% compared to last month."
            )

        if velocity.predicted_budget_overrun_amount > 0:
            insights.append(
                f"At the current pace, you will exceed your budget by {velocity.predicted_budget_overrun_amount:,.0f}."
            )
        else:
            insights.append(
                f"At the current pace, monthly spending is forecast at {velocity.forecast:,.0f}."
            )

        if budget_health.categories_over_budget > 0:
            insights.append(
                f"{budget_health.categories_over_budget} categories are already over budget."
            )

        close = [row for row in category_rows if row.status_indicator == "CLOSE"]
        if close:
            worst = max(close, key=lambda item: item.percent_used)
            insights.append(
                f"{worst.category_name} is close to its limit at {worst.percent_used:.1f}%."
            )

        if budget_health.highest_deviation_category:
            insights.append(
                f"Highest deviation belongs to {budget_health.highest_deviation_category} at {budget_health.highest_deviation_amount:,.0f}."
            )

        return insights[:5]

    @staticmethod
    def _ascii_bar_chart(categories: list[CategoryAmount], width: int = 24) -> str:
        if not categories:
            return "No spending data."
        max_amount = max(item.amount for item in categories) or 1
        lines = []
        for item in categories:
            filled = int((item.amount / max_amount) * width)
            bar = "█" * filled
            lines.append(f"{item.category_name:<12} {item.amount:>10,.0f} {bar}")
        return "\n".join(lines)

    @staticmethod
    def _jalali_month_range(year: int, month: int):
        first_day = jdatetime.date(year, month, 1)
        if month < 12:
            next_month = jdatetime.date(year, month + 1, 1)
        else:
            next_month = jdatetime.date(year + 1, 1, 1)
        last_day = next_month.togregorian() - timedelta(days=1)
        total_days = last_day.day
        return (
            first_day.togregorian().strftime("%Y-%m-%d"),
            last_day.strftime("%Y-%m-%d"),
            total_days,
        )


def get_daily_report(user_id: int, date: str):
    return ReportingService.get_daily_report(user_id, date)


def get_weekly_report(user_id: int, start_date: str):
    return ReportingService.get_weekly_report(user_id, start_date)


def get_monthly_report(user_id: int, year: int, month: int):
    return ReportingService.get_monthly_report(user_id, year, month)


def report_to_dict(report):
    return asdict(report)
