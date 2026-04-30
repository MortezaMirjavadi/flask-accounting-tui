"""Jalali date picker widget with dropdown selectors."""

from datetime import date, timedelta

import jdatetime
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Select, Static


class JalaliDatePicker(Static):
    """Jalali date picker with dropdown year/month/day selectors."""

    DEFAULT_CSS = """
    JalaliDatePicker {
        width: 100%;
        height: auto;
        border: solid $primary-darken-2;
        background: $surface-darken-1;
        padding: 1;
    }
    JalaliDatePicker:focus {
        border: solid $primary;
    }
    JalaliDatePicker .picker_header {
        text-align: center;
        color: $primary-lighten-2;
        text-style: bold;
        height: 1;
        margin: 0 0 1 0;
    }
    JalaliDatePicker .picker_columns {
        width: 100%;
        height: auto;
        padding: 0;
    }
    JalaliDatePicker .picker_col {
        width: 1fr;
        height: auto;
        padding: 0 1;
        margin: 0 1 0 0;
    }
    JalaliDatePicker .picker_col_header {
        text-align: center;
        color: $primary;
        text-style: bold;
        background: $primary-darken-3;
        height: 1;
        margin: 0 0 1 0;
    }
    JalaliDatePicker Select {
        width: 100%;
        margin: 0;
    }
    JalaliDatePicker .picker_controls {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0 0 0;
    }
    JalaliDatePicker .picker_controls Button {
        width: 12;
        margin: 0 1;
    }
    JalaliDatePicker .picker_hint {
        text-align: center;
        color: $text-muted;
        height: 1;
        margin: 1 0 0 0;
    }
    """

    MIN_YEAR = 1300
    MAX_YEAR = 1500

    _MONTH_NAMES = (
        "Farvardin",
        "Ordibehesht",
        "Khordad",
        "Tir",
        "Mordad",
        "Shahrivar",
        "Mehr",
        "Aban",
        "Azar",
        "Dey",
        "Bahman",
        "Esfand",
    )

    _YEAR_OPTIONS = tuple((str(year), str(year)) for year in range(MIN_YEAR, MAX_YEAR + 1))

    def __init__(self, initial_gregorian: str = None, **kwargs):
        super().__init__(**kwargs)
        self.year = 1400
        self.month = 1
        self.day = 1
        self._syncing = False
        self._day_option_count = 0

        if initial_gregorian:
            parts = initial_gregorian.strip().split("-")
            if len(parts) == 3:
                g_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                j_date = jdatetime.date.fromgregorian(date=g_date)
                self._set_date(j_date.year, j_date.month, j_date.day)
            else:
                self._set_today()
        else:
            self._set_today()

    def compose(self) -> ComposeResult:
        yield Label(" Jalali Date Picker ", classes="picker_header")
        with Horizontal(classes="picker_columns"):
            with Vertical(classes="picker_col"):
                yield Label("Year", classes="picker_col_header")
                yield Select(options=self._YEAR_OPTIONS, id="picker_year", allow_blank=False)
            with Vertical(classes="picker_col"):
                yield Label("Month", classes="picker_col_header")
                yield Select(options=self._month_options(), id="picker_month", allow_blank=False)
            with Vertical(classes="picker_col"):
                yield Label("Day", classes="picker_col_header")
                yield Select(options=self._day_options(), id="picker_day", allow_blank=False)
        with Horizontal(classes="picker_controls"):
            yield Button("Today", id="today_btn")
        yield Static(id="date_display")
        yield Static("[Enter] apply date | [T] Today", classes="picker_hint")

    def on_mount(self):
        self._sync_controls(apply_day_options=True)
        self._update_display()

    def _set_today(self):
        today = jdatetime.date.fromgregorian(date=date.today())
        self._set_date(today.year, today.month, today.day)

    def _set_date(self, year: int, month: int, day: int):
        self.year = max(self.MIN_YEAR, min(self.MAX_YEAR, year))
        self.month = max(1, min(12, month))
        max_day = self._month_length(self.year, self.month)
        self.day = max(1, min(day, max_day))
        self._day_option_count = max_day
        if self.is_mounted:
            self._sync_controls(apply_day_options=True)
            self._update_display()

    def _month_length(self, year: int, month: int) -> int:
        """Return number of days in a Jalali month."""
        if month < 12:
            next_month = jdatetime.date(year, month + 1, 1)
        else:
            next_month = jdatetime.date(year + 1, 1, 1)
        return (next_month - timedelta(days=1)).day

    def _month_options(self):
        return [(f"{name} ({idx:02d})", str(idx)) for idx, name in enumerate(self._MONTH_NAMES, start=1)]

    def _day_options(self):
        try:
            max_day = self._month_length(self.year, self.month)
        except ValueError:
            max_day = 31
        return [(f"{day:02d}", str(day)) for day in range(1, max_day + 1)]

    def _sync_controls(self, apply_day_options: bool = False):
        self._syncing = True
        try:
            year_select = self.query_one("#picker_year", Select)
            month_select = self.query_one("#picker_month", Select)
            day_select = self.query_one("#picker_day", Select)

            year_select.value = str(self.year)
            month_select.value = str(self.month)

            if apply_day_options:
                day_select.set_options(self._day_options())
                self._day_option_count = len(self._day_options())
            elif self._day_option_count == 0:
                # Ensure initial state has options set for first render.
                day_select.set_options(self._day_options())
                self._day_option_count = len(self._day_options())

            day_select.value = str(self.day)
        finally:
            self._syncing = False

    def _ensure_day_options(self, force: bool = False) -> bool:
        """Ensure day options match current month/year and return True when refreshed."""
        if not self.is_mounted:
            return False

        required_count = self._month_length(self.year, self.month)
        if not force and self._day_option_count == required_count:
            return False

        day_select = self.query_one("#picker_day", Select)
        day_select.set_options(self._day_options())
        self._day_option_count = required_count
        return True

    def _clamp_day_to_month(self) -> bool:
        max_day = self._month_length(self.year, self.month)
        if self.day <= max_day:
            return False
        self.day = max_day
        return True

    def _update_display(self):
        display = self.query_one("#date_display", Static)
        display.update(f"  Selected: {self.year:04d}-{self.month:02d}-{self.day:02d}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._syncing:
            return
        if event.value is Select.BLANK or event.value is None or event.value == "":
            return

        select = getattr(event, "select", None)
        if select is None:
            return
        control_id = select.id

        try:
            selected_value = int(event.value)
        except (TypeError, ValueError):
            return

        if control_id == "picker_year":
            if selected_value != self.year:
                self.year = selected_value
                day_changed = self._clamp_day_to_month()
                if self._ensure_day_options() or day_changed:
                    self.query_one("#picker_day", Select).value = str(self.day)
                self._update_display()
            return

        if control_id == "picker_month":
            if selected_value != self.month:
                self.month = selected_value
                day_changed = self._clamp_day_to_month()
                self._ensure_day_options(force=day_changed)
                if day_changed:
                    self.query_one("#picker_day", Select).value = str(self.day)
                self._update_display()
            return

        if control_id == "picker_day":
            if selected_value != self.day:
                self.day = selected_value
                self._update_display()
            return

    def on_key(self, event) -> None:
        if event.key.lower() == "t":
            event.stop()
            self._set_today()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "today_btn":
            self._set_today()

    def get_gregorian_date(self) -> str:
        """Return selected date in Gregorian YYYY-MM-DD format."""
        j_date = jdatetime.date(self.year, self.month, self.day)
        return j_date.togregorian().strftime("%Y-%m-%d")

    def get_jalali_date(self) -> str:
        """Return selected date in Jalali YYYY-MM-DD format."""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
