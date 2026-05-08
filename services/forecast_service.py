"""Smart cashflow forecasting and risk analytics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from database import get_connection, release_connection
from app.services import reporting_service
from services.calendar_service import CalendarService


@dataclass
class DailyTrend:
    base_income: float
    base_expense: float
    weekday_income: dict[int, float]
    weekday_expense: dict[int, float]
    month_income: dict[int, float]
    month_expense: dict[int, float]

    def estimate_income(self, day: date) -> float:
        weekday_value = self.weekday_income.get(day.weekday(), self.base_income)
        month_value = self.month_income.get(day.month, self.base_income)
        return max(0.0, (weekday_value + month_value) / 2)

    def estimate_expense(self, day: date) -> float:
        weekday_value = self.weekday_expense.get(day.weekday(), self.base_expense)
        month_value = self.month_expense.get(day.month, self.base_expense)
        return max(0.0, (weekday_value + month_value) / 2)


@dataclass
class ForecastPoint:
    date: str
    projected_balance: float
    inflow: float
    outflow: float


@dataclass
class ForecastReport:
    start_date: str
    period_days: int
    current_balance: float
    daily_forecast: list[ForecastPoint]
    risk_days: list[str]
    insights: list[str]
    forecast_accuracy: float
    total_expected_income: float
    total_expected_expense: float
    total_predicted_surplus: float
    total_expected_deficit: float
    average_expense: float
    monthly_metrics: dict


def _parse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _to_date_value(value):
    """Coerce date-like DB values into a ``date`` instance."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return _parse_date(value)
    raise TypeError(f"Unsupported date value type: {type(value)!r}")


def _to_float_amount(value) -> float:
    return float(value if value is not None else 0.0)


def _iso(dte: date) -> str:
    return dte.strftime("%Y-%m-%d")


def _safe_division(value: float, divisor: float) -> float:
    if divisor == 0:
        return 0.0
    return value / divisor


class ForecastService:
    """Estimate future cashflow from historical transactions and scheduled events."""

    @staticmethod
    def forecast_balance(
        user_id: int,
        start_date: str | date | datetime | None = None,
        period_days: int = 45,
        months_back: int = 6,
        safety_threshold: float = 0.0,
    ) -> ForecastReport:
        if period_days <= 0:
            raise ValueError("period_days must be positive")

        if start_date is None:
            start = date.today()
        else:
            start = _parse_date(start_date)

        CalendarService.ensure_instances(user_id, horizon_days=max(period_days, 90))

        trend = ForecastService._build_historical_trend(user_id, months_back)
        events = ForecastService._load_upcoming_events(user_id, start, start + timedelta(days=period_days - 1))
        events_by_day = ForecastService._group_events_by_day(events)

        balance = ForecastService.get_current_balance(user_id)
        points: list[ForecastPoint] = []
        risk_days: list[str] = []

        total_income = 0.0
        total_expense = 0.0

        for offset in range(period_days):
            current_day = start + timedelta(days=offset)
            planned_in = trend.estimate_income(current_day)
            planned_out = trend.estimate_expense(current_day)

            for event in events_by_day.get(_iso(current_day), []):
                amount = _to_float_amount(event.get("amount"))
                if event["category_type"] == "income":
                    planned_in += amount
                else:
                    planned_out += amount

            net = planned_in - planned_out
            balance += net
            points.append(
                ForecastPoint(
                    date=_iso(current_day),
                    projected_balance=balance,
                    inflow=planned_in,
                    outflow=planned_out,
                )
            )
            total_income += planned_in
            total_expense += planned_out

            if balance < safety_threshold:
                risk_days.append(_iso(current_day))

        accuracy = ForecastService._calculate_accuracy_score(user_id)
        avg_expense = total_expense / max(period_days, 1)
        insights = ForecastService._build_insights(points, trend, avg_expense, risk_days, accuracy)
        monthly_metrics = ForecastService._build_monthly_metrics(
            user_id, points, total_expense, total_income, safety_threshold
        )

        total_surplus = sum(
            max(0.0, (point.inflow - point.outflow))
            for point in points
        )
        total_deficit = abs(sum(
            min(0.0, (point.inflow - point.outflow))
            for point in points
        ))

        return ForecastReport(
            start_date=_iso(start),
            period_days=period_days,
            current_balance=ForecastService.get_current_balance(user_id),
            daily_forecast=points,
            risk_days=risk_days,
            insights=insights,
            forecast_accuracy=accuracy,
            total_expected_income=total_income,
            total_expected_expense=total_expense,
            total_predicted_surplus=total_surplus,
            total_expected_deficit=total_deficit,
            average_expense=avg_expense,
            monthly_metrics=monthly_metrics,
        )

    @staticmethod
    def _build_monthly_metrics(
        user_id: int,
        points: list[ForecastPoint],
        total_expense: float,
        total_income: float,
        safety_threshold: float,
    ) -> dict:
        risk_days = [point.date for point in points if point.projected_balance < safety_threshold]

        # Forecasted deviation versus this month's budget if available.
        today = date.today()
        planned_budget = ForecastService._get_monthly_budget_amount(
            user_id, today.year, today.month
        )
        deviation_from_budget = total_expense - planned_budget if planned_budget is not None else 0.0

        avg_expense = total_expense / max(len(points), 1)
        recommended = []
        if deviation_from_budget > 0:
            recommended.append(
                f"Budget may exceed this month by {deviation_from_budget:,.0f}; reduce fixed costs by 10%."
            )
        if risk_days:
            recommended.append(
                f"{len(risk_days)} day(s) fall below safety threshold; increase planned cash reserve."
            )
        if not points:
            recommended.append("No forecast points generated; add events or transactions.")
        elif total_income < total_expense:
            recommended.append("Planned income is lower than planned expenses; align incoming jobs before the 5th.")

        return {
            "month": f"{today.year:04d}/{today.month:02d}",
            "number_of_risk_days": len(risk_days),
            "deviation_from_budget": deviation_from_budget,
            "total_expected_deficit": max(0.0, -(points[-1].projected_balance if points else 0.0)),
            "total_predicted_surplus": total_income - total_expense,
            "average_expenses_trend": avg_expense,
            "recommended_adjustment_actions": recommended[:3],
        }

    @staticmethod
    def _get_monthly_budget_amount(user_id: int, year: int, month: int) -> float | None:
        try:
            report = reporting_service.get_monthly_report(user_id, year, month)
        except Exception:
            return None
        return float(sum(row.planned_amount for row in report.category_breakdown if row.category_type == "cost"))

    @staticmethod
    def _load_upcoming_events(user_id: int, start: date, end: date) -> list[dict]:
        events = CalendarService.load_events_for_forecast(
            user_id,
            _iso(start),
            _iso(end),
        )
        # Forecast should include only unpaid future obligations/receipts.
        return [event for event in events if event["status"] in ("pending", "snoozed")]

    @staticmethod
    def _group_events_by_day(events: list[dict]) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for event in events:
            due_date = event.get("due_date")
            if isinstance(due_date, datetime):
                due_date = due_date.date()
            due_key = due_date.strftime("%Y-%m-%d") if isinstance(due_date, date) else str(due_date)
            grouped.setdefault(due_key, []).append(event)
        return grouped

    @staticmethod
    def get_current_balance(user_id: int) -> float:
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM sources WHERE user_id = %s AND deleted_at IS NULL",
                (user_id,),
            )
            row = cursor.fetchone()
            return float(row["total"] if row else 0.0)
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                release_connection(conn)

    @staticmethod
    def _build_historical_trend(user_id: int, months_back: int = 6) -> DailyTrend:
        today = date.today()
        start = today - timedelta(days=32 * max(months_back, 1))
        rows = ForecastService._get_transactions(user_id, start, today)
        if not rows:
            return DailyTrend(
                base_income=0.0,
                base_expense=0.0,
                weekday_income={},
                weekday_expense={},
                month_income={},
                month_expense={},
            )

        income_by_weekday: dict[int, list[float]] = {i: [] for i in range(7)}
        expense_by_weekday: dict[int, list[float]] = {i: [] for i in range(7)}
        income_by_month: dict[int, list[float]] = {i: [] for i in range(1, 13)}
        expense_by_month: dict[int, list[float]] = {i: [] for i in range(1, 13)}
        days_with_transactions: set[str] = set()

        for row in rows:
            try:
                tx_day = _to_date_value(row["date"])
            except (TypeError, ValueError):
                continue

            amount = _to_float_amount(row["amount"])
            weekday = tx_day.weekday()
            month_no = tx_day.month
            days_with_transactions.add(_iso(tx_day))
            if row["category_type"] == "income":
                income_by_weekday[weekday].append(amount)
                income_by_month[month_no].append(amount)
            else:
                expense_by_weekday[weekday].append(amount)
                expense_by_month[month_no].append(amount)

        weekday_income = {
            idx: ForecastService._weighted_moving_average(values)
            for idx, values in income_by_weekday.items()
        }
        weekday_expense = {
            idx: ForecastService._weighted_moving_average(values)
            for idx, values in expense_by_weekday.items()
        }
        month_income = {
            idx: ForecastService._weighted_moving_average(values)
            for idx, values in income_by_month.items()
        }
        month_expense = {
            idx: ForecastService._weighted_moving_average(values)
            for idx, values in expense_by_month.items()
        }

        total_income = sum(
            _to_float_amount(row["amount"])
            for row in rows
            if row["category_type"] == "income"
        )
        total_expense = sum(
            _to_float_amount(row["amount"])
            for row in rows
            if row["category_type"] == "cost"
        )
        day_count = max(1, len(days_with_transactions))

        return DailyTrend(
            base_income=_safe_division(total_income, day_count),
            base_expense=_safe_division(total_expense, day_count),
            weekday_income=weekday_income,
            weekday_expense=weekday_expense,
            month_income=month_income,
            month_expense=month_expense,
        )

    @staticmethod
    def _weighted_moving_average(values: list[float]) -> float:
        if not values:
            return 0.0
        if len(values) == 1:
            return float(values[0])

        weights = [1 + idx * 0.2 for idx in range(len(values))]
        weighted = sum(value * weight for value, weight in zip(values, weights))
        return weighted / sum(weights)

    @staticmethod
    def _get_transactions(user_id: int, start: date, end: date) -> list[dict]:
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.date, t.amount, COALESCE(c.type, 'cost') AS category_type
                FROM transactions t
                JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = %s
                  AND t.deleted_at IS NULL
                  AND t.date >= %s
                  AND t.date <= %s
                ORDER BY t.date ASC
                """,
                (user_id, _iso(start), _iso(end)),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                release_connection(conn)

    @staticmethod
    def _calculate_accuracy_score(user_id: int) -> float:
        """Calculate accuracy by forecasting one-month history and scoring RMSE."""
        today = date.today()
        if today <= date(2000, 1, 1):
            return 100.0

        end_date = today - timedelta(days=1)
        test_start = end_date - timedelta(days=30)
        train_start = test_start - timedelta(days=45)
        train_trend = ForecastService._build_historical_trend(user_id, months_back=2)

        test_rows = ForecastService._get_transactions(user_id, train_start, end_date)
        actual_by_day: dict[str, float] = {}
        for row in test_rows:
            try:
                tx_day = _to_date_value(row["date"])
            except (TypeError, ValueError):
                continue

            amount = _to_float_amount(row["amount"])
            if row["category_type"] != "income":
                amount = -amount
            day_key = tx_day.strftime("%Y-%m-%d")
            actual_by_day[day_key] = actual_by_day.get(day_key, 0.0) + amount

        errors: list[float] = []
        for day_delta in range(30):
            d = test_start + timedelta(days=day_delta)
            if _iso(d) not in actual_by_day:
                actual = 0.0
            else:
                actual = actual_by_day[_iso(d)]
            predicted = train_trend.estimate_income(d) - train_trend.estimate_expense(d)
            errors.append(predicted - actual)

        if not errors:
            return 100.0
        rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
        max_abs = max((abs(v) for v in actual_by_day.values()), default=0.0)
        if max_abs == 0:
            max_abs = max(abs(predicted) for predicted in errors) or 1.0
        score = max(0.0, 100.0 - (rmse / max_abs) * 100.0)
        return round(min(100.0, score), 2)

    @staticmethod
    def _build_insights(
        points: list[ForecastPoint],
        trend: DailyTrend,
        average_expense: float,
        risk_days: list[str],
        accuracy: float,
    ) -> list[str]:
        insights = [
            f"Forecast accuracy score: {accuracy:,.1f}/100",
            f"Average forecasted daily spend is {average_expense:,.0f}.",
        ]

        if risk_days:
            first = risk_days[0]
            insights.append(f"Balance falls below safety threshold on {first}.")
            insights.append("Consider shifting optional expenses earlier if possible.")
        else:
            insights.append("No projected negative-balance days in this horizon.")

        if trend.weekday_expense:
            worst_day = max(trend.weekday_expense, key=trend.weekday_expense.get)
            day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][worst_day]
            insights.append(f"{day_name} is historically the highest expense day.")

        if trend.month_expense:
            max_month = max(trend.month_expense, key=trend.month_expense.get)
            month_exp = trend.month_expense[max_month]
            if month_exp > 0:
                insights.append(
                    f"Income peak adjustment suggestion: plan incoming revenue around month {max_month} to cover {month_exp:,.0f} expense tendencies."
                )

        return insights[:7]

    @staticmethod
    def to_dict(report: ForecastReport) -> dict:
        return {
            "start_date": report.start_date,
            "period_days": report.period_days,
            "current_balance": report.current_balance,
            "daily_forecast": [
                {
                    "date": point.date,
                    "projected_balance": point.projected_balance,
                    "inflow": point.inflow,
                    "outflow": point.outflow,
                }
                for point in report.daily_forecast
            ],
            "risk_days": report.risk_days,
            "insights": report.insights,
            "forecast_accuracy": report.forecast_accuracy,
            "total_expected_income": report.total_expected_income,
            "total_expected_expense": report.total_expected_expense,
            "total_predicted_surplus": report.total_predicted_surplus,
            "total_expected_deficit": report.total_expected_deficit,
            "average_expense": report.average_expense,
            "monthly_metrics": report.monthly_metrics,
        }
