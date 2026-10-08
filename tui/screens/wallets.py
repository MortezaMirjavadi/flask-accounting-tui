"""Wallet management screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Static, Rule
)

from tui.api import api_get, api_post, api_put, api_delete, extract_items, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class WalletsScreen(Screen):
    """Wallets menu."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("WALLETS", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. List Wallets")),
                ListItem(Label("2. Add Wallet")),
                ListItem(Label("3. Back to Main Menu")),
                id="src_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-3] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_do_list()
        elif idx == 1:
            self.action_do_add()
        elif idx == 2:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_list(self):
        self.app.push_screen(WalletListScreen())

    def action_do_add(self):
        self.app.push_screen(WalletAddScreen())


class WalletListScreen(Screen):
    """Wallet list with filtering."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("t", "show_transfer_report", "Transfers"),
        Binding("f", "apply_filter", "Filter"),
        Binding("r", "reset_filter", "Reset"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("WALLET LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Filter by name", id="src_filter_name")
                yield Button("🔍 Filter", variant="primary", id="src_filter_btn")
                yield Button("🔄 Reset", variant="default", id="src_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="src_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="src_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [T] Transfers  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  T=Transfers  F=Filter  R=Reset  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#src_table", DataTable)
        table.add_columns("ID", "Name", "Currency", "Type")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#src_table", DataTable)
        table.clear()
        resp = api_get("/wallets", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = extract_items(data)
        if not self._data:
            table.add_row("-", "No wallets found", "-", "-")
        else:
            rows = [
                (str(s["id"]), s["name"], s.get("currency", "IRR"),
                 s.get("wallet_type", "personal"))
                for s in self._data
            ]
            table.add_rows(rows)
        self.update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "src_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "src_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        name = self.query_one("#src_filter_name", Input).value.strip()
        params = {}
        if name:
            params["name"] = name
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#src_filter_name", Input).value = ""
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#src_detail", Static)
        src_id = self._get_selected_id()
        if src_id is None:
            detail.update("Select a wallet to see details.")
            return
        src = next((s for s in getattr(self, "_data", []) if s["id"] == src_id), None)
        if src is None:
            detail.update("Select a wallet to see details.")
            return

        # Fetch balance
        bal_resp = api_get(f"/wallets/{src_id}/balance", username=self.app.user.get("username"))
        bal_data, bal_err = handle_response(bal_resp)
        if bal_err or bal_data is None:
            bal_info = "Balance: N/A"
        else:
            bal = bal_data.get("balance", 0)
            bal_info = f"Balance: {format_toman(bal)}"

        detail.update(
            f"[b]ID:[/b]        {src['id']}\n"
            f"[b]Name:[/b]      {src['name']}\n"
            f"[b]Currency:[/b]  {src.get('currency', 'IRR')}\n"
            f"[b]Type:[/b]      {src.get('wallet_type', 'personal')}\n"
            f"[b]{bal_info}[/b]\n"
        )

    def action_go_back(self):
        self.app.pop_screen()

    def on_key(self, event):
        key = event.key.lower()
        if key == "e":
            event.stop()
            self.action_edit_selected()
        elif key == "d":
            event.stop()
            self.action_delete_selected()
        elif key == "t":
            event.stop()
            self.action_show_transfer_report()

    def _get_selected_id(self):
        table = self.query_one("#src_table", DataTable)
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

    def action_edit_selected(self):
        src_id = self._get_selected_id()
        if src_id is None:
            self.app.push_screen(MessageBox("No wallet selected.", "Info"))
            return

        def on_save():
            self.load_data()

        self.app.push_screen(WalletEditScreen(src_id, on_save=on_save))

    def action_delete_selected(self):
        src_id = self._get_selected_id()
        if src_id is None:
            self.app.push_screen(MessageBox("No wallet selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/wallets/{src_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected wallet?", "Confirm"), on_confirm)

    def action_show_transfer_report(self):
        src_id = self._get_selected_id()
        if src_id is None:
            self.app.push_screen(MessageBox("No wallet selected.", "Info"))
            return
        src = next((item for item in getattr(self, "_data", []) if item["id"] == src_id), None)
        src_name = src["name"] if src else "Wallet"
        self.app.push_screen(WalletTransferReportScreen(src_id, src_name))


class WalletAddScreen(Screen):
    """Add new wallet screen."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    CURRENCIES = ["IRR", "USD", "EUR", "GBP", "AED"]
    WALLET_TYPES = ["personal", "shared"]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("ADD WALLET", classes="menu_header")
            yield Rule()
            yield Label("Name:")
            yield Input(placeholder="Wallet name", id="src_name")
            yield Label("Currency:")
            yield Input(placeholder="IRR", id="src_currency", value="IRR")
            yield Label("Wallet Type (personal/shared):")
            yield Input(placeholder="personal", id="src_wallet_type", value="personal")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save")
                yield Button("✖ Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        name = self.query_one("#src_name", Input).value.strip()
        currency = self.query_one("#src_currency", Input).value.strip().upper() or "IRR"
        wallet_type = self.query_one("#src_wallet_type", Input).value.strip().lower() or "personal"

        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if currency not in self.CURRENCIES:
            self.app.push_screen(MessageBox(f"Currency must be one of: {', '.join(self.CURRENCIES)}", "Validation"))
            return
        if wallet_type not in self.WALLET_TYPES:
            self.app.push_screen(MessageBox("Wallet type must be 'personal' or 'shared'", "Validation"))
            return

        payload = {"name": name, "currency": currency, "wallet_type": wallet_type}
        resp = api_post("/wallets", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Wallet added successfully.", "Success"))
            self.query_one("#src_name", Input).value = ""
            self.query_one("#src_currency", Input).value = "IRR"
            self.query_one("#src_wallet_type", Input).value = "personal"


class WalletEditScreen(Screen):
    """Edit wallet screen."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    CURRENCIES = ["IRR", "USD", "EUR", "GBP", "AED"]
    WALLET_TYPES = ["personal", "shared"]

    def __init__(self, src_id: int, on_save=None, **kwargs):
        self.src_id = src_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("EDIT WALLET", classes="menu_header")
            yield Rule()
            yield Label("Name:")
            yield Input(placeholder="Wallet name", id="src_name")
            yield Label("Currency:")
            yield Input(placeholder="IRR", id="src_currency")
            yield Label("Wallet Type (personal/shared):")
            yield Input(placeholder="personal", id="src_wallet_type")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save")
                yield Button("✖ Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/wallets/{self.src_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self.query_one("#src_name", Input).value = data.get("name", "")
        self.query_one("#src_currency", Input).value = data.get("currency", "IRR")
        self.query_one("#src_wallet_type", Input).value = data.get("wallet_type", "personal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        name = self.query_one("#src_name", Input).value.strip()
        currency = self.query_one("#src_currency", Input).value.strip().upper() or "IRR"
        wallet_type = self.query_one("#src_wallet_type", Input).value.strip().lower() or "personal"

        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if currency not in self.CURRENCIES:
            self.app.push_screen(MessageBox(f"Currency must be one of: {', '.join(self.CURRENCIES)}", "Validation"))
            return
        if wallet_type not in self.WALLET_TYPES:
            self.app.push_screen(MessageBox("Wallet type must be 'personal' or 'shared'", "Validation"))
            return

        payload = {"name": name, "currency": currency, "wallet_type": wallet_type}
        resp = api_put(f"/wallets/{self.src_id}", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()


class WalletTransferReportScreen(Screen):
    """Transfer report for a single wallet."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, src_id: int, src_name: str, **kwargs):
        self.src_id = src_id
        self.src_name = src_name
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label(f"TRANSFER REPORT - {self.src_name}", classes="menu_header")
            yield Rule()
            yield Static(id="src_transfer_summary")
            yield Rule()
            yield DataTable(id="src_transfer_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Esc] Back", id="help")
            yield StatusBar("Transfer in/out records for selected wallet", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#src_transfer_table", DataTable)
        table.add_columns("ID", "Date", "Direction", "Amount", "Counterparty", "Note")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self):
        table = self.query_one("#src_transfer_table", DataTable)
        summary = self.query_one("#src_transfer_summary", Static)
        table.clear()
        resp = api_get(f"/wallets/{self.src_id}/transfers", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        totals = (data or {}).get("summary", {})
        summary.update(
            f"[b]Transfer In:[/b]  {format_toman(totals.get('total_transfer_in', 0))}    "
            f"[b]Transfer Out:[/b]  {format_toman(totals.get('total_transfer_out', 0))}    "
            f"[b]Net:[/b]  {format_toman(totals.get('net_transfer', 0))}"
        )

        records = (data or {}).get("records", [])
        if not records:
            table.add_row("-", "-", "No transfers", "-", "-", "-")
            return

        for record in records:
            direction = "IN" if record.get("direction") == "in" else "OUT"
            counterparty = (
                record.get("from_wallet_name")
                if record.get("direction") == "in"
                else record.get("to_wallet_name")
            ) or "-"
            table.add_row(
                str(record["id"]),
                record.get("date", ""),
                direction,
                format_toman(record.get("amount", 0)),
                counterparty,
                (record.get("notes") or "")[:30],
            )

    def action_go_back(self):
        self.app.pop_screen()
