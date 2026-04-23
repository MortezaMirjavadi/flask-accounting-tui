"""Transaction management screens."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Select, Static, Rule
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class TransactionsScreen(Screen):
    """Transactions menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_list_by_category", "By Category"),
        Binding("3", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("TRANSACTIONS", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. List Transactions")),
                ListItem(Label("2. List by Category")),
                ListItem(Label("3. Add Transaction")),
                ListItem(Label("4. Back to Main Menu")),
                id="tx_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-3] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_do_list()
        elif idx == 1:
            self.action_do_list_by_category()
        elif idx == 2:
            self.action_do_add()
        elif idx == 3:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_list(self):
        self.app.push_screen(TransactionListScreen())

    def action_do_list_by_category(self):
        self.app.push_screen(TransactionByCategoryScreen())

    def action_do_add(self):
        self.app.push_screen(TransactionAddScreen())


class TransactionListScreen(Screen):
    """Transaction list with filtering."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("f", "apply_filter", "Filter"),
        Binding("r", "reset_filter", "Reset"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("TRANSACTION LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Date from (1405-01-01)", id="tx_filter_from")
                yield Input(placeholder="Date to (1405-12-29)", id="tx_filter_to")
                yield Input(placeholder="Min amount", id="tx_filter_min")
                yield Input(placeholder="Max amount", id="tx_filter_max")
                yield Input(placeholder="Description", id="tx_filter_desc")
                yield Button("Filter", variant="primary", id="tx_filter_btn")
                yield Button("Reset", variant="default", id="tx_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="tx_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="tx_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  F=Filter  R=Reset  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tx_table", DataTable)
        table.add_columns("ID", "Date", "Amount", "Category", "Source", "Description")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#tx_table", DataTable)
        table.clear()
        resp = api_get("/transactions", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "-", "-", "No transactions", "-", "-")
        else:
            for t in self._data:
                table.add_row(
                    str(t["id"]),
                    t.get("date", ""),
                    format_toman(t.get("amount", 0)),
                    t.get("category_name", "N/A"),
                    t.get("source_name") or "-",
                    (t.get("description") or "")[:25],
                )
        self.update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tx_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "tx_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        date_from = self.query_one("#tx_filter_from", Input).value.strip()
        date_to = self.query_one("#tx_filter_to", Input).value.strip()
        min_amt = self.query_one("#tx_filter_min", Input).value.strip()
        max_amt = self.query_one("#tx_filter_max", Input).value.strip()
        desc = self.query_one("#tx_filter_desc", Input).value.strip()
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if min_amt:
            try:
                params["min_amount"] = float(min_amt)
            except ValueError:
                pass
        if max_amt:
            try:
                params["max_amount"] = float(max_amt)
            except ValueError:
                pass
        if desc:
            params["description"] = desc
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#tx_filter_from", Input).value = ""
        self.query_one("#tx_filter_to", Input).value = ""
        self.query_one("#tx_filter_min", Input).value = ""
        self.query_one("#tx_filter_max", Input).value = ""
        self.query_one("#tx_filter_desc", Input).value = ""
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#tx_detail", Static)
        tx_id = self._get_selected_id()
        if tx_id is None:
            detail.update("Select a transaction to see details.")
            return
        tx = next((t for t in getattr(self, "_data", []) if t["id"] == tx_id), None)
        if tx is None:
            detail.update("Select a transaction to see details.")
            return
        detail.update(
            f"[b]ID:[/b]          {tx['id']}\n"
            f"[b]Date:[/b]        {tx.get('date', '')}\n"
            f"[b]Amount:[/b]      {format_toman(tx.get('amount', 0))}\n"
            f"[b]Category:[/b]    {tx.get('category_name', 'N/A')}\n"
            f"[b]Source:[/b]      {tx.get('source_name') or '-'}\n"
            f"[b]Description:[/b] {tx.get('description') or '-'}\n"
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

    def _get_selected_id(self):
        table = self.query_one("#tx_table", DataTable)
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
        tx_id = self._get_selected_id()
        if tx_id is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return
        
        def on_save():
            self.load_data()
        
        self.app.push_screen(TransactionEditScreen(tx_id, on_save=on_save))

    def action_delete_selected(self):
        tx_id = self._get_selected_id()
        if tx_id is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/transactions/{tx_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected transaction?", "Confirm"), on_confirm)


class TransactionByCategoryScreen(Screen):
    """Transactions grouped by category (accordion view)."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("TRANSACTIONS BY CATEGORY", classes="menu_header")
            yield Rule()
            yield Static(id="accordion_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Expand/Collapse  [E] Edit  [D] Delete  [Esc] Back", id="help")
            yield StatusBar("Enter=Toggle  E=Edit  D=Delete  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._categories = []
        self._transactions = []
        self._expanded = set()
        self._selected_category_idx = 0
        self._selected_tx_idx = 0
        self._mode = "category"
        self.load_data()

    def load_data(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        cats, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._categories = cats or []

        resp = api_get("/transactions", username=self.app.user.get("username"))
        txs, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._transactions = txs or []
        self._render_accordion()

    def _render_accordion(self):
        content = self.query_one("#accordion_content", Static)
        lines = []
        if not self._categories:
            content.update("No categories found.")
            return

        for cat_idx, cat in enumerate(self._categories):
            cat_id = cat["id"]
            cat_name = cat["name"]
            cat_type = cat["type"]
            cat_txs = [t for t in self._transactions if t.get("category_id") == cat_id]
            total = sum(t.get("amount", 0) for t in cat_txs)

            is_selected = self._mode == "category" and self._selected_category_idx == cat_idx
            marker = ">" if is_selected else " "
            arrow = "▼" if cat_id in self._expanded else "▶"
            color = "green" if cat_type == "income" else "red"

            lines.append(f"{marker} {arrow} [{color}]{cat_name}[/{color}] ({cat_type})  {len(cat_txs)} txs  Total: {format_toman(total)}")

            if cat_id in self._expanded:
                if not cat_txs:
                    lines.append("      No transactions")
                else:
                    for tx_idx, t in enumerate(cat_txs):
                        tx_selected = (
                            self._mode == "transaction"
                            and self._selected_category_idx == cat_idx
                            and self._selected_tx_idx == tx_idx
                        )
                        tx_marker = ">" if tx_selected else " "
                        lines.append(
                            f"   {tx_marker}  {t.get('date','')}  {format_toman(t.get('amount',0)):>20}  "
                            f"{(t.get('source_name') or '-'):<12}  {(t.get('description') or '-')[:30]}"
                        )
            lines.append("")

        content.update("\n".join(lines))

    def on_key(self, event):
        key = event.key
        if key == "up":
            event.stop()
            self._navigate(-1)
        elif key == "down":
            event.stop()
            self._navigate(1)
        elif key == "enter":
            event.stop()
            self._toggle_expand()
        elif key.lower() == "e":
            event.stop()
            self.action_edit_selected()
        elif key.lower() == "d":
            event.stop()
            self.action_delete_selected()

    def _navigate(self, direction):
        if not self._categories:
            return

        if self._mode == "category":
            self._selected_category_idx += direction
            self._selected_category_idx = max(0, min(self._selected_category_idx, len(self._categories) - 1))
            self._selected_tx_idx = 0
        else:
            cat_id = self._categories[self._selected_category_idx]["id"]
            cat_txs = [t for t in self._transactions if t.get("category_id") == cat_id]
            self._selected_tx_idx += direction
            self._selected_tx_idx = max(0, min(self._selected_tx_idx, len(cat_txs) - 1))

        self._render_accordion()

    def _toggle_expand(self):
        if self._mode == "transaction":
            self._mode = "category"
            self._selected_tx_idx = 0
            self._render_accordion()
            return

        if not self._categories:
            return
        cat = self._categories[self._selected_category_idx]
        cat_id = cat["id"]
        cat_txs = [t for t in self._transactions if t.get("category_id") == cat_id]

        if cat_id in self._expanded:
            self._expanded.discard(cat_id)
        else:
            self._expanded.add(cat_id)
            if cat_txs:
                self._mode = "transaction"
                self._selected_tx_idx = 0
        self._render_accordion()

    def _get_selected_tx_id(self):
        if self._mode != "transaction" or not self._categories:
            return None
        cat = self._categories[self._selected_category_idx]
        cat_txs = [t for t in self._transactions if t.get("category_id") == cat["id"]]
        if 0 <= self._selected_tx_idx < len(cat_txs):
            return cat_txs[self._selected_tx_idx]["id"]
        return None

    def action_edit_selected(self):
        tx_id = self._get_selected_tx_id()
        if tx_id is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return
        
        def on_save():
            self.load_data()
        
        self.app.push_screen(TransactionEditScreen(tx_id, on_save=on_save))

    def action_delete_selected(self):
        tx_id = self._get_selected_tx_id()
        if tx_id is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/transactions/{tx_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected transaction?", "Confirm"), on_confirm)

    def action_go_back(self):
        self.app.pop_screen()


class TransactionAddScreen(Screen):
    """Add new transaction screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("ADD TRANSACTION", classes="menu_header")
            yield Rule()
            yield Label("Date (Jalali YYYY-MM-DD):")
            yield Input(placeholder="1405-01-31", id="tx_date")
            yield Label("Amount:")
            yield Input(placeholder="100000", id="tx_amount")
            yield Label("Category:")
            yield Select([], prompt="Loading...", id="tx_category")
            yield Label("Source (optional):")
            yield Select([], prompt="Loading...", id="tx_source")
            yield Label("Description (optional):")
            yield Input(placeholder="Description", id="tx_desc")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        # Set current Jalali date as default
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        self.query_one("#tx_date", Input).value = date_str
        
        self.load_categories()
        self.load_sources()

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        sel = self.query_one("#tx_category", Select)
        if err:
            sel.set_options([])
            return
        if not data:
            sel.set_options([])
            sel.prompt = "No categories"
        else:
            options = [(f"{c['name']} ({c['type']})", c["id"]) for c in data]
            sel.set_options(options)
            sel.prompt = "Select category"

    def load_sources(self):
        resp = api_get("/sources", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        sel = self.query_one("#tx_source", Select)
        if err:
            sel.set_options([])
            sel.prompt = "No sources"
            return
        if not data:
            sel.set_options([])
            sel.prompt = "No sources"
        else:
            options = [(s["name"], s["id"]) for s in data]
            sel.set_options(options)
            sel.prompt = "Select source"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def save(self):
        date = self.query_one("#tx_date", Input).value.strip()
        amount_str = self.query_one("#tx_amount", Input).value.strip()
        cat_id = self.query_one("#tx_category", Select).value
        src_id = self.query_one("#tx_source", Select).value
        desc = self.query_one("#tx_desc", Input).value.strip()

        if not date:
            self.app.push_screen(MessageBox("Date is required", "Validation"))
            return
        date = date.replace("/", "-").replace(".", "-")
        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        if cat_id is None or cat_id == Select.BLANK:
            self.app.push_screen(MessageBox("Category is required", "Validation"))
            return

        payload = {
            "date": date,
            "amount": amount,
            "category_id": cat_id,
            "description": desc,
        }
        if src_id is not None and src_id != Select.BLANK:
            payload["source_id"] = src_id
        
        resp = api_post("/transactions", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Transaction added successfully.", "Success"))
            self.query_one("#tx_date", Input).value = ""
            self.query_one("#tx_amount", Input).value = ""
            self.query_one("#tx_desc", Input).value = ""

    def action_go_back(self):
        self.app.pop_screen()


class TransactionEditScreen(Screen):
    """Edit transaction screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, tx_id: int, on_save=None, **kwargs):
        self.tx_id = tx_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("EDIT TRANSACTION", classes="menu_header")
            yield Rule()
            yield Label("Date (Jalali YYYY-MM-DD):")
            yield Input(placeholder="1405-01-31", id="tx_date")
            yield Label("Amount:")
            yield Input(placeholder="100000", id="tx_amount")
            yield Label("Category:")
            yield Select([], prompt="Loading...", id="tx_category")
            yield Label("Source (optional):")
            yield Select([], prompt="Loading...", id="tx_source")
            yield Label("Description (optional):")
            yield Input(placeholder="Description", id="tx_desc")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        # Set current Jalali date as default
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        self.query_one("#tx_date", Input).value = date_str
        
        self.load_categories()
        self.load_sources()
        
        resp = api_get(f"/transactions/{self.tx_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        
        self.query_one("#tx_date", Input).value = data.get("date", "")
        self.query_one("#tx_amount", Input).value = str(data.get("amount", ""))
        self.query_one("#tx_desc", Input).value = data.get("description", "")
        
        cat_id = data.get("category_id")
        if cat_id is not None:
            self.query_one("#tx_category", Select).value = cat_id
        
        src_id = data.get("source_id")
        if src_id is not None:
            self.query_one("#tx_source", Select).value = src_id

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        sel = self.query_one("#tx_category", Select)
        if err:
            sel.set_options([])
            return
        if not data:
            sel.set_options([])
            sel.prompt = "No categories"
        else:
            options = [(f"{c['name']} ({c['type']})", c["id"]) for c in data]
            sel.set_options(options)
            sel.prompt = "Select category"

    def load_sources(self):
        resp = api_get("/sources", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        sel = self.query_one("#tx_source", Select)
        if err:
            sel.set_options([])
            sel.prompt = "No sources"
            return
        if not data:
            sel.set_options([])
            sel.prompt = "No sources"
        else:
            options = [(s["name"], s["id"]) for s in data]
            sel.set_options(options)
            sel.prompt = "Select source"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def save(self):
        date = self.query_one("#tx_date", Input).value.strip()
        amount_str = self.query_one("#tx_amount", Input).value.strip()
        cat_id = self.query_one("#tx_category", Select).value
        src_id = self.query_one("#tx_source", Select).value
        desc = self.query_one("#tx_desc", Input).value.strip()

        if not date:
            self.app.push_screen(MessageBox("Date is required", "Validation"))
            return
        date = date.replace("/", "-").replace(".", "-")
        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        if cat_id is None or cat_id == Select.BLANK:
            self.app.push_screen(MessageBox("Category is required", "Validation"))
            return

        payload = {
            "date": date,
            "amount": amount,
            "category_id": cat_id,
            "description": desc,
        }
        if src_id is not None and src_id != Select.BLANK:
            payload["source_id"] = src_id
        
        resp = api_put(f"/transactions/{self.tx_id}", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()
