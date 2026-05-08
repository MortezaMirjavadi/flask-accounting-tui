"""Alert and reminder generation for due payments and cashflow risks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from services.calendar_service import CalendarService
from services.forecast_service import ForecastService


@dataclass
class Alert:
    title: str
    message: str
    severity: str
    due_date: str | None = None
    amount: float | None = None


def _to_date_value(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date value type: {type(value)!r}")


def _safe_to_int(value: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    return max(0, value)


class AlertService:
    """Create contextual alerts for upcoming bills and forecast risk."""

    @staticmethod
    def generate_alerts(
        user_id: int,
        due_window_days: int = 7,
        risk_window_days: int = 45,
        safety_threshold: float = 0.0,
    ) -> list[Alert]:
        due_window_days = _safe_to_int(due_window_days)
        risk_window_days = _safe_to_int(risk_window_days) or 45

        today = date.today()
        alerts: list[Alert] = []

        CalendarService.ensure_instances(user_id, horizon_days=max(90, risk_window_days))
        upcoming = CalendarService.get_instances(
            user_id,
            start_date=today.strftime("%Y-%m-%d"),
            end_date=(today + timedelta(days=max(risk_window_days, 90))).strftime("%Y-%m-%d"),
        )

        for event in upcoming:
            try:
                due = _to_date_value(event["due_date"])
            except (TypeError, ValueError):
                continue
            days_left = (due - today).days
            if days_left > due_window_days or event["status"] not in ("pending", "snoozed"):
                continue

            title = "Upcoming Income" if event["category_type"] == "income" else "Upcoming Bill"
            alerts.append(
                Alert(
                    title=title,
                    message=(
                        f"{event['title']} {'arrives' if event['category_type'] == 'income' else 'due'} "
                        f"{days_left} day(s) from now for {event['amount']:,.0f}."
                    ),
                    severity="warning",
                    due_date=due.isoformat(),
                    amount=float(event["amount"]),
                )
            )

        forecast = ForecastService.forecast_balance(
            user_id,
            start_date=today.strftime("%Y-%m-%d"),
            period_days=risk_window_days,
            safety_threshold=safety_threshold,
        )

        # Risk-day alerts from forecast
        for day in forecast.risk_days[:5]:
            alerts.append(
                Alert(
                    title="Insufficient Funds",
                    message=f"Predicted low balance on {day}.",
                    severity="critical",
                    due_date=day,
                    amount=None,
                )
            )

        if forecast.total_expected_deficit > 0:
            alerts.append(
                Alert(
                    title="Forecast Deficit",
                    message=(
                        f"Expected deficit during period: {forecast.total_expected_deficit:,.0f}."
                    ),
                    severity="warning",
                )
            )

        # Major expense without nearby income
        income_dates = {
            day["due_date"].isoformat()
            if isinstance(day["due_date"], date)
            else str(day["due_date"])
            for day in upcoming
            if day["category_type"] == "income" and day["status"] in ("pending", "snoozed")
        }
        max_daily_outflow = max((point.outflow for point in forecast.daily_forecast), default=0.0)
        for point in forecast.daily_forecast:
            has_income_near = point.date in income_dates
            if point.outflow >= max(1.0, max_daily_outflow * 0.30) and not has_income_near:
                alerts.append(
                    Alert(
                        title="Cashflow Gap",
                        message=(
                            f"No nearby confirmed income around {point.date}; large outflow of {point.outflow:,.0f} is forecasted."
                        ),
                        severity="warning",
                        due_date=point.date,
                    )
                )
                # avoid noisy duplicates
                if len(alerts) >= 12:
                    break

        # Deduplicate while preserving order
        deduped: list[Alert] = []
        seen = set()
        for alert in alerts:
            key = (alert.title, alert.due_date, alert.message)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(alert)
        return deduped[:12]

    @staticmethod
    def to_dict(alerts: list[Alert]) -> list[dict]:
        return [
            {
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "due_date": alert.due_date,
                "amount": alert.amount,
            }
            for alert in alerts
        ]
