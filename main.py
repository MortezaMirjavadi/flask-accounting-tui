#!/usr/bin/env python3
"""Standalone entry point for the financial calendar + forecast TUI module."""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from textual.app import App

from database import get_connection, release_connection, init_db
from tui.calendar_view import CalendarScreen


def _get_or_create_user(username: str) -> int:
    """Return existing user id for `username` or create a demo account."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        existing = cursor.fetchone()
        if existing is not None:
            return int(existing["id"])

        password_hash = "demo"
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, password_hash),
        )
        conn.commit()
        return int(cursor.fetchone()['id'])
    finally:
        cursor.close()
        release_connection(conn)


def _ensure_category(cursor, user_id: int, name: str, category_type: str) -> int:
    cursor.execute(
        "SELECT id FROM categories WHERE user_id = %s AND name = %s AND deleted_at IS NULL",
        (user_id, name),
    )
    row = cursor.fetchone()
    if row is not None:
        return int(row["id"])

    cursor.execute(
        "INSERT INTO categories (user_id, name, type) VALUES (%s, %s, %s)",
        (user_id, name, category_type),
    )
    return int(cursor.fetchone()['id'])


def _ensure_source(cursor, user_id: int, name: str, amount: float) -> int:
    cursor.execute(
        "SELECT id FROM sources WHERE user_id = %s AND name = %s AND deleted_at IS NULL",
        (user_id, name),
    )
    row = cursor.fetchone()
    if row is not None:
        return int(row["id"])

    cursor.execute(
        "INSERT INTO sources (user_id, name, amount) VALUES (%s, %s, %s)",
        (user_id, name, amount),
    )
    return int(cursor.fetchone()['id'])


def _seed_transactions(cursor, user_id: int, salary_category_id: int, cost_category_id: int, source_id: int) -> None:
    cursor.execute(
        "SELECT 1 FROM transactions WHERE user_id = %s AND date = %s AND amount = %s AND category_id = %s LIMIT 1",
        (user_id, (date.today() - timedelta(days=1)).isoformat(), 900000, salary_category_id),
    )
    if cursor.fetchone() is not None:
        return

    sample_rows = []
    for offset in range(3):
        workday = date.today() - timedelta(days=28 + offset)
        sample_rows.append(
            (
                user_id,
                workday.isoformat(),
                300000,
                cost_category_id,
                source_id,
                f"Demo grocery spend ({workday.isoformat()})",
            )
        )

    salary_day = date.today() - timedelta(days=1)
    sample_rows.append(
        (
            user_id,
            salary_day.isoformat(),
            500000,
            salary_category_id,
            source_id,
            "Demo salary",
        )
    )

    cursor.executemany(
        "INSERT INTO transactions (user_id, date, amount, category_id, source_id, description) VALUES (%s, %s, %s, %s, %s, %s)",
        sample_rows,
    )

    # Apply source effects once to keep balances consistent with transaction history.
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = %s",
        (user_id,),
    )
    # Keep source in sync with historical fixture so forecast starts from realistic balance.
    total = float(cursor.fetchone()["total"] or 0.0)
    cursor.execute(
        "UPDATE sources SET amount = amount + %s WHERE id = %s AND user_id = %s",
        (total, source_id, user_id),
    )


def _seed_financial_events(cursor, user_id: int, categories: dict[str, int], source_id: int) -> None:
    from services.calendar_service import CalendarService

    cursor.execute("SELECT 1 FROM financial_events WHERE user_id = %s AND title = %s LIMIT 1", (user_id, "Salary"))
    if cursor.fetchone() is not None:
        return

    today = date.today()
    # Use today or future dates so validation passes
    salary_day = today.isoformat()
    rent_day = today.replace(day=min(today.day + 2, 28)).isoformat()
    utilities_day = today.replace(day=min(today.day + 5, 28)).isoformat()
    insurance_day = today.replace(day=min(today.day + 8, 28)).isoformat()

    payloads = [
        {
            "title": "Salary",
            "description": "Monthly salary",
            "amount": 500000.0,
            "category_id": categories["Salary Income"],
            "source_id": source_id,
            "frequency": "monthly",
            "repeat_interval": 1,
            "start_date": salary_day,
            "end_date": None,
            "occurrence_limit": None,
        },
        {
            "title": "Rent",
            "description": "Monthly rent payment",
            "amount": 450000.0,
            "category_id": categories["Rent"],
            "source_id": source_id,
            "frequency": "monthly",
            "repeat_interval": 1,
            "start_date": rent_day,
            "end_date": None,
            "occurrence_limit": None,
        },
        {
            "title": "Utilities",
            "description": "Utilities subscription",
            "amount": 125000.0,
            "category_id": categories["Utilities"],
            "source_id": source_id,
            "frequency": "monthly",
            "repeat_interval": 1,
            "start_date": utilities_day,
            "end_date": None,
            "occurrence_limit": None,
        },
        {
            "title": "Insurance",
            "description": "Quarterly insurance",
            "category_id": categories["Insurance"],
            "amount": 300000.0,
            "source_id": source_id,
            "frequency": "monthly",
            "repeat_interval": 3,
            "start_date": insurance_day,
            "end_date": None,
            "occurrence_limit": None,
        },
        {
            "title": "Freelance Bonus",
            "description": "Bonus income bonus",
            "amount": 200000.0,
            "category_id": categories["Freelance"],
            "source_id": source_id,
            "frequency": "once",
            "repeat_interval": 1,
            "start_date": (today + timedelta(days=18)).isoformat(),
            "end_date": None,
            "occurrence_limit": 1,
        },
    ]

    for payload in payloads:
        try:
            CalendarService.create_event(user_id, payload)
        except ValueError as exc:
            # Log validation issues during seeding for debugging
            print(f"[SEED] Skipped {payload['title']}: {exc}")
        except Exception:
            # Ignore if a concurrent run left partial data; avoid crashing boot.
            pass


def seed_demo_data(user_id: int) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Categories
        categories = {
            "Salary Income": _ensure_category(cursor, user_id, "Salary Income", "income"),
            "Freelance": _ensure_category(cursor, user_id, "Freelance", "income"),
            "Rent": _ensure_category(cursor, user_id, "Rent", "cost"),
            "Insurance": _ensure_category(cursor, user_id, "Insurance", "cost"),
            "Utilities": _ensure_category(cursor, user_id, "Utilities", "cost"),
        }

        source_id = _ensure_source(cursor, user_id, "Main Bank", 1200000)

        _seed_transactions(cursor, user_id, categories["Salary Income"], categories["Rent"], source_id)

        # Commit base data so CalendarService can see the source in its own connection
        conn.commit()

        _seed_financial_events(cursor, user_id, categories, source_id)

        conn.commit()
    finally:
        cursor.close()
        release_connection(conn)


class _CalendarApp(App):
    """Minimal wrapper app for standalone calendar usage."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

    def on_mount(self):
        self.push_screen(CalendarScreen(user_id=self.user_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run financial calendar TUI")
    parser.add_argument("--user", default="demo", help="Demo username (for local seed mode)")
    parser.add_argument("--seed-only", action="store_true", help="Only setup demo data and exit")
    args = parser.parse_args()

    init_db()
    user_id = _get_or_create_user(args.user)
    seed_demo_data(user_id)

    if args.seed_only:
        return

    app = _CalendarApp(user_id=user_id)
    app.run()


if __name__ == "__main__":
    main()
