"""Base classes with common functionality for screens."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Digits, Footer, Header, Input, Label, Rule, Select, Static

from tui.api import api_get, api_delete, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class BaseListScreen(Screen):
    """Base class for list screens with common functionality."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
    ]
    
    # Override in subclasses
    api_endpoint = ""
    columns = []
    detail_fields = []
    
    def __init__(self, **kwargs):
        self._data = []
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label(self.title, classes="menu_header")
            yield Rule()
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="data_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="detail_panel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip(self.help_text, id="help")
            yield StatusBar(self.status_text, id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    @property
    def title(self) -> str:
        raise NotImplementedError

    @property
    def help_text(self) -> str:
        return "[↑/↓] Navigate  [E] Edit  [D] Delete  [Esc] Back"

    @property
    def status_text(self) -> str:
        return "E=Edit  D=Delete  Esc=Back"

    def on_mount(self) -> None:
        table = self.query_one("#data_table", DataTable)
        for col in self.columns:
            table.add_column(col)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#data_table", DataTable)
        table.clear()
        
        resp = api_get(self.api_endpoint, params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        
        self._data = data or []
        self.populate_table(table)
        self.update_detail()

    def populate_table(self, table: DataTable):
        """Override to populate table with data."""
        raise NotImplementedError

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#detail_panel", Static)
        item_id = self._get_selected_id()
        
        if item_id is None:
            detail.update("Select an item to see details.")
            return
        
        item = next((i for i in self._data if i["id"] == item_id), None)
        if item is None:
            detail.update("Select an item to see details.")
            return
        
        detail.update(self.format_detail(item))

    def format_detail(self, item: dict) -> str:
        """Override to format detail view."""
        lines = []
        for field in self.detail_fields:
            key, label = field if isinstance(field, tuple) else (field, field.replace("_", " ").title())
            value = item.get(key, "")
            lines.append(f"[b]{label}:[/b] {value}")
        return "\n".join(lines)

    def _get_selected_id(self):
        table = self.query_one("#data_table", DataTable)
        if not table.rows:
            return None
        
        cursor = table.cursor_row
        if cursor is None or cursor < 0 or cursor >= len(table.rows):
            return None
        
        try:
            row_key = table.coordinate_to_cell_key((cursor, 0)).row_key
            cells = table.get_row(row_key)
            return int(cells[0])
        except Exception:
            return None

    def on_key(self, event):
        key = event.key.lower()
        if key == "e":
            event.stop()
            self.action_edit_selected()
        elif key == "d":
            event.stop()
            self.action_delete_selected()

    def action_go_back(self):
        self.app.pop_screen()

    def action_edit_selected(self):
        raise NotImplementedError

    def action_delete_selected(self):
        item_id = self._get_selected_id()
        if item_id is None:
            self.app.push_screen(MessageBox("No item selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if confirmed:
                self._do_delete(item_id)

        self.app.push_screen(
            ConfirmBox(f"Delete this {self.item_name}?", "Confirm Delete"),
            on_confirm,
        )

    def _do_delete(self, item_id: int):
        resp = api_delete(f"{self.api_endpoint}/{item_id}", username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.load_data()

    @property
    def item_name(self) -> str:
        return "item"


class DashboardScreen(Screen):
    """Home dashboard showing sources and today's transactions."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_source", "Add Source"),
        Binding("t", "add_transaction", "Add Transaction"),
    ]

    CSS = """
    DashboardScreen {
        layout: vertical;
        align: left top;
        content-align: left top;
    }

    #dash-header {
        height: 1;
        width: 100%;
        text-align: center;
        color: $primary-lighten-2;
        text-style: bold;
        margin: 0 0 1 0;
    }

    #dash-split {
        width: 100%;
        height: 1fr;
    }

    #dash-left {
        width: 45%;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 0 1;
        min-width: 0;
    }

    #dash-right {
        width: 55%;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 0 1;
        min-width: 0;
    }

    .dash-section-title {
        width: 1fr;
        height: 3;
        text-style: bold;
        color: $primary;
        content-align: left middle;
        padding: 0 0 0 1;
    }

    #sources-table {
        width: 100%;
        height: 1fr;
        min-height: 5;
    }

    #tx-table {
        width: 100%;
        height: 1fr;
        min-height: 5;
    }

    #balance-container {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        align: center middle;
    }

    #balance-label {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        text-style: bold;
        margin: 0;
    }

    #balance-digits {
        width: auto;
        height: auto;
        text-align: center;
        color: $success;
        text-style: bold;
        margin: 0;
    }

    #balance-unit {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        margin: 0;
    }

    #sources-count {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text;
        margin: 0;
    }

    #tx-summary-row {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
    }

    .tx-metric {
        width: 1fr;
        height: auto;
        align: center middle;
    }

    .tx-metric-label {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        text-style: bold;
        margin: 0;
    }

    .tx-metric-digits {
        width: auto;
        height: auto;
        text-align: center;
        margin: 0;
    }

    .income-color {
        color: $success;
    }

    .cost-color {
        color: $error;
    }

    .net-color {
        color: $primary;
    }

    .tx-metric-unit {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        margin: 0;
    }

    #tx-count {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text;
        margin: 0;
    }

    .dash-btn-row {
        height: 3;
        width: 100%;
        margin: 0;
        align: left middle;
    }

    .dash-btn-row Button {
        width: auto;
        margin: 0 1 0 0;
        min-width: 18;
    }

    #dash-bottom {
        height: 1;
        width: 100%;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Personal Finance Dashboard", id="dash-header")
        with Horizontal(id="dash-split"):
            # Left panel — Sources
            with Vertical(id="dash-left"):
                with Horizontal(classes="dash-btn-row"):
                    yield Label("Sources", classes="dash-section-title")
                    yield Button("Add Source", variant="error", id="btn-add-source")
                with Vertical(id="balance-container"):
                    yield Label("Total Balance", id="balance-label")
                    yield Digits("0", id="balance-digits")
                    yield Static("Toman", id="balance-unit")
                    yield Static("Loading...", id="sources-count")
                yield DataTable(id="sources-table")

            # Right panel — Today's Transactions
            with Vertical(id="dash-right"):
                with Horizontal(classes="dash-btn-row"):
                    yield Label("Today's Transactions", classes="dash-section-title")
                    yield Button("Add Transaction", variant="error", id="btn-add-tx")
                with Horizontal(id="tx-summary-row"):
                    with Vertical(classes="tx-metric"):
                        yield Label("Income", classes="tx-metric-label")
                        yield Digits("0", id="tx-income", classes="tx-metric-digits income-color")
                        yield Static("Toman", classes="tx-metric-unit")
                    with Vertical(classes="tx-metric"):
                        yield Label("Cost", classes="tx-metric-label")
                        yield Digits("0", id="tx-cost", classes="tx-metric-digits cost-color")
                        yield Static("Toman", classes="tx-metric-unit")
                    with Vertical(classes="tx-metric"):
                        yield Label("Net", classes="tx-metric-label")
                        yield Digits("0", id="tx-net", classes="tx-metric-digits net-color")
                        yield Static("Toman", classes="tx-metric-unit")
                yield Static("Loading...", id="tx-count")
                yield DataTable(id="tx-table")
        yield Static("", id="dash-bottom")

    def on_mount(self) -> None:
        src_table = self.query_one("#sources-table", DataTable)
        src_table.add_columns("ID", "Name", "Amount")
        src_table.cursor_type = "row"
        src_table.zebra_stripes = True

        tx_table = self.query_one("#tx-table", DataTable)
        tx_table.add_columns("Date", "Description", "Amount")
        tx_table.cursor_type = "row"
        tx_table.zebra_stripes = True

        self.load_sources()
        self.load_today_transactions()

    def load_sources(self):
        src_table = self.query_one("#sources-table", DataTable)
        src_table.clear()
        digits = self.query_one("#balance-digits", Digits)
        count_label = self.query_one("#sources-count", Static)

        resp = api_get("/sources", username=self.app.user.get("username"))
        data, err = handle_response(resp)

        if err:
            digits.update("0")
            count_label.update(f"[red]Error: {err}[/red]")
            return

        self._sources = data or []
        if not self._sources:
            digits.update("0")
            count_label.update("[dim]No sources found[/dim]")
            return

        total = sum(float(s.get("amount", 0)) for s in self._sources)
        rows = [
            (str(s["id"]), s["name"], format_toman(s.get("amount", 0)))
            for s in self._sources
        ]
        src_table.add_rows(rows)
        digits.update(f"{total:,.0f}")
        count_label.update(f"[b]Sources:[/b]  {len(self._sources)}")

    def load_today_transactions(self):
        tx_table = self.query_one("#tx-table", DataTable)
        tx_table.clear()
        income_digits = self.query_one("#tx-income", Digits)
        cost_digits = self.query_one("#tx-cost", Digits)
        net_digits = self.query_one("#tx-net", Digits)
        count_label = self.query_one("#tx-count", Static)

        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        today_str = jalali_now.strftime("%Y-%m-%d")

        resp = api_get(
            "/transactions",
            params={"date_from": today_str, "date_to": today_str, "include_transfers": 1},
            username=self.app.user.get("username"),
        )
        data, err = handle_response(resp)

        if err:
            income_digits.update("0")
            cost_digits.update("0")
            net_digits.update("0")
            count_label.update(f"[red]Error: {err}[/red]")
            return

        self._today_txs = data or []
        if not self._today_txs:
            income_digits.update("0")
            cost_digits.update("0")
            net_digits.update("0")
            count_label.update(f"[dim]No transactions today ({today_str})[/dim]")
            return

        total_income = 0.0
        total_cost = 0.0
        rows = []
        for t in self._today_txs:
            amount = float(t.get("amount", 0))
            cat_type = t.get("category_type", "")
            if cat_type == "income" or t.get("is_transfer"):
                total_income += amount
            else:
                total_cost += amount

            desc = t.get("description") or t.get("category_name") or "-"
            rows.append((t.get("date", ""), desc[:30], format_toman(amount)))

        tx_table.add_rows(rows)
        net = total_income - total_cost
        income_digits.update(f"{total_income:,.0f}")
        cost_digits.update(f"{total_cost:,.0f}")
        net_digits.update(f"{net:,.0f}")
        count_label.update(f"[dim]{len(self._today_txs)} transactions today[/dim]")

    def load_data(self):
        """Refresh all dashboard data from the API."""
        self.load_sources()
        self.load_today_transactions()

    def action_refresh(self):
        self.load_data()

    def action_add_source(self):
        from tui.screens.sources import SourceAddScreen
        self.app.push_screen(SourceAddScreen())

    def action_add_transaction(self):
        from tui.screens.transactions import TransactionAddScreen
        self.app.push_screen(TransactionAddScreen())

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add-source":
            self.action_add_source()
        elif event.button.id == "btn-add-tx":
            self.action_add_transaction()
