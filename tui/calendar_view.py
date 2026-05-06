"""Calendar screen for the main TUI application."""

from datetime import date, datetime, timedelta
from calendar import monthrange

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Rule

from services.alert_service import AlertService
from services.calendar_service import CalendarService
from services.forecast_service import ForecastService
from tui.jalali_date_picker import JalaliDatePicker
from tui.widgets import MessageBox


def _jalali_to_gregorian(text: str) -> str:
    """Parse Jalali YYYY-MM-DD and return Gregorian YYYY-MM-DD."""
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("Date must be in YYYY-MM-DD format")
    year, month, day = map(int, parts)
    jalali_date = jdatetime.date(year, month, day)
    gregorian_date = jalali_date.togregorian()
    return gregorian_date.strftime("%Y-%m-%d")


def _gregorian_to_jalali(gregorian_text: str) -> str:
    """Convert Gregorian YYYY-MM-DD to Jalali YYYY-MM-DD."""
    parts = gregorian_text.strip().split("-")
    if len(parts) != 3:
        return gregorian_text
    year, month, day = map(int, parts)
    g_date = date(year, month, day)
    jalali_date = jdatetime.date.fromgregorian(date=g_date)
    return jalali_date.strftime("%Y-%m-%d")


def _normalize_picker_date(value) -> str:
    """Normalize optional date values for the date picker input."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if value is None:
        return date.today().strftime("%Y-%m-%d")
    try:
        return str(value).strip()
    except Exception:
        return date.today().strftime("%Y-%m-%d")


class EventFormScreen(ModalScreen[dict | None]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, user_id: int, categories: list, sources: list, payload: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.categories = categories
        self.sources = sources
        self.payload = payload or {}

    def compose(self) -> ComposeResult:
        defaults = {
            "title": "", "description": "", "amount": "", "category_id": "",
            "source_id": "", "frequency": "once", "repeat_interval": "1",
            "start_date": date.today().strftime("%Y-%m-%d"),
            "end_date": "", "occurrence_limit": ""
        }
        defaults.update(self.payload)
        defaults["start_date"] = _normalize_picker_date(defaults.get("start_date"))

        cat_options = [(f"{name} ({cat_type})", str(cat_id)) for cat_id, name, cat_type in self.categories]
        src_options = [(name, str(src_id)) for src_id, name in self.sources]
        has_categories = bool(cat_options)
        if not has_categories:
            cat_options = [("No categories", "")]

        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            with VerticalScroll(classes="form_scroll"):
                yield Label("[b]Financial Event Editor[/b]")
                yield Rule()
                yield Input(id="title", placeholder="Title", value=defaults["title"])
                yield Input(id="amount", placeholder="Amount", value=str(defaults["amount"]))
                yield Select(
                    options=cat_options,
                    prompt="Select Category" if has_categories else "No categories",
                    allow_blank=True,
                    id="category_select",
                )
                if src_options:
                    yield Select(options=src_options, prompt="Select Source", allow_blank=True, id="source_select")
                yield JalaliDatePicker(initial_gregorian=defaults["start_date"], id="start_date_picker")
                with Horizontal(classes="button_row"):
                    yield Button("Save", variant="primary", id="save")
                    yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        if event.button.id != "save":
            return

        cat_select = self.query_one("#category_select", Select)
        category_id = cat_select.value if cat_select.value is not Select.NULL else ""
        src_select = self.query_one("#source_select", Select) if self.sources else None
        source_id = src_select.value if src_select and src_select.value not in (None, "", Select.NULL) else None
        date_picker = self.query_one("#start_date_picker", JalaliDatePicker)
        gregorian_start = date_picker.get_gregorian_date()
        payload = {
            "title": self.query_one("#title", Input).value,
            "amount": self.query_one("#amount", Input).value,
            "category_id": category_id,
            "source_id": source_id,
            "start_date": gregorian_start,
        }
        if payload["amount"] and payload["category_id"]:
            self.dismiss(payload)
        else:
            self.app.push_screen(MessageBox("Amount and category required", "Error", is_error=True))

    def action_cancel(self):
        self.dismiss(None)


class CalendarScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"), Binding("q", "go_back", "Back"),
        Binding("left", "prev_range", "Prev"), Binding("right", "next_range", "Next"),
        Binding("up", "move_up", "Up"), Binding("down", "move_down", "Down"),
        Binding("a", "add", "Add"), Binding("e", "edit", "Edit"), Binding("d", "delete", "Delete"),
    ]

    view_mode = "month"
    selected_date = date.today()

    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.instances = []
        self._categories = []
        self._sources = []

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("FINANCIAL CALENDAR", classes="menu_header")
            yield Rule()
            with Horizontal(id="dashboard"):
                yield Static(id="calendar_panel")
                with Vertical(id="side_panel"):
                    yield Static(id="selected_panel")
                    yield Static(id="forecast_panel")
                    yield Static(id="alert_panel")
        with Vertical(classes="bottom_bar"):
            yield Static("[L/R]Prev/Next [Up/Down]Week [A]Add [E]Edit [Del]Delete [Esc]Back", id="help")
            yield Static("Calendar View - Press Esc to return", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self):
        from database import get_connection, release_connection
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT id, name, type FROM categories WHERE user_id = %s AND deleted_at IS NULL", (self.user_id,))
            self._categories = [(r["id"], r["name"], r["type"]) for r in c.fetchall()]
            c.execute("SELECT id, name FROM sources WHERE user_id = %s AND deleted_at IS NULL", (self.user_id,))
            self._sources = [(r["id"], r["name"]) for r in c.fetchall()]
        finally:
            c.close()
        release_connection(conn)
        self.refresh_data()

    def refresh_data(self):
        start, end = self._view_range()
        CalendarService.ensure_instances(self.user_id, horizon_days=365)
        self.instances = CalendarService.get_instances(
            self.user_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        )
        forecast = ForecastService.forecast_balance(self.user_id, period_days=45)
        alerts = AlertService.generate_alerts(self.user_id)
        self.update_display(forecast, alerts)

    def _view_range(self):
        if self.view_mode == "day":
            return self.selected_date, self.selected_date
        if self.view_mode == "week":
            m = self.selected_date - timedelta(days=self.selected_date.weekday())
            return m, m + timedelta(days=6)
        if self.view_mode == "year":
            return date(self.selected_date.year, 1, 1), date(self.selected_date.year, 12, 31)
        md = monthrange(self.selected_date.year, self.selected_date.month)[1]
        return date(self.selected_date.year, self.selected_date.month, 1), date(self.selected_date.year, self.selected_date.month, md)

    def update_display(self, forecast, alerts):
        jalali_selected = _gregorian_to_jalali(self.selected_date.strftime("%Y-%m-%d"))
        body = f"=== {self.view_mode.upper()} ===\n{jalali_selected}\n\n"
        body += f"Instances: {len(self.instances)}\n"
        body += f"Balance: {forecast.current_balance:,.0f}\n"
        body += f"Risk days: {len(forecast.risk_days)}\n\n"

        by_date = {}
        for i in self.instances:
            due_key = i["due_date"]
            if hasattr(due_key, "strftime"):
                due_key = due_key.strftime("%Y-%m-%d")
            by_date.setdefault(due_key, []).append(i)

        curr = self._view_range()[0]
        while curr <= self._view_range()[1]:
            k = curr.strftime("%Y-%m-%d")
            if k in by_date:
                for ev in by_date[k]:
                    marker = "+" if ev["category_type"] == "income" else "-"
                    body += f"{curr.day:2d} {marker} {ev['title'][:15]} {ev['amount']:,.0f}\n"
            curr += timedelta(days=1)

        self.query_one("#calendar_panel", Static).update(body)
        lines = [f"Date: {jalali_selected}", f"Mode: {self.view_mode}", f"Events: {len(self.instances)}"]
        self.query_one("#selected_panel", Static).update("\n".join(lines))

        f_lines = [f"Balance: {forecast.current_balance:,.0f}", f"In: +{forecast.total_expected_income:,.0f}", f"Out: -{forecast.total_expected_expense:,.0f}"]
        self.query_one("#forecast_panel", Static).update("\n".join(f_lines))

        a_lines = [f"{a.title}: {a.message[:30]}" for a in alerts[:3]]
        self.query_one("#alert_panel", Static).update("\n".join(a_lines) if a_lines else "No alerts")

    def _shift_month(self, delta):
        y, m = self.selected_date.year, self.selected_date.month + delta
        while m < 1: m, y = 12, y - 1
        while m > 12: m, y = 1, y + 1
        md = monthrange(y, m)[1]
        self.selected_date = date(y, m, min(self.selected_date.day, md))
        self.refresh_data()

    def action_prev_range(self):
        if self.view_mode == "month": self._shift_month(-1)
        elif self.view_mode == "week": self.selected_date -= timedelta(days=7)
        else: self.selected_date = date(self.selected_date.year - 1, 1, 1)
        self.refresh_data()

    def action_next_range(self):
        if self.view_mode == "month": self._shift_month(1)
        elif self.view_mode == "week": self.selected_date += timedelta(days=7)
        else: self.selected_date = date(self.selected_date.year + 1, 1, 1)
        self.refresh_data()

    def action_move_up(self):
        self.selected_date -= timedelta(days=7)
        self.refresh_data()

    def action_move_down(self):
        self.selected_date += timedelta(days=7)
        self.refresh_data()

    def action_add(self):
        def on_save(payload):
            if payload:
                try:
                    CalendarService.create_event(self.user_id, payload)
                    self.refresh_data()
                except Exception as exc:
                    self.app.push_screen(MessageBox(str(exc), "Error", is_error=True))
        self.app.push_screen(EventFormScreen(self.user_id, self._categories, self._sources), on_save)

    def action_edit(self):
        pass

    def action_delete(self):
        pass

    def action_go_back(self):
        self.app.pop_screen()
