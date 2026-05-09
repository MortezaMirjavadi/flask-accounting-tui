"""Transaction management screens."""

from datetime import date, datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Checkbox, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Select, Static, Rule, TextArea
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response, format_toman
from tui.jalali_date_picker import JalaliDatePicker
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar, TransactionItemsModal


class TransactionsScreen(Screen):
    """Transactions menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_list_by_category", "By Category"),
        Binding("3", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
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
        if not getattr(self, "_sidebar_embedded", False):
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
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("TRANSACTION LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Date from (1405-01-01)", id="tx_filter_from")
                yield Input(placeholder="Date to (1405-12-29)", id="tx_filter_to")
                yield Select(
                    [
                        ("All types", "all"),
                        ("Income", "income"),
                        ("Cost", "cost"),
                        ("Transfer", "transfer"),
                    ],
                    id="tx_filter_type",
                    allow_blank=False,
                )
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
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        # Performance optimization: throttle detail updates
        self._selected_id = None
        self._last_update_time = 0
        self._update_throttle_ms = 50  # Only update every 50ms
        
        table = self.query_one("#tx_table", DataTable)
        table.add_columns("ID", "Date", "Amount", "Category", "Source", "Description")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#tx_table", DataTable)
        table.clear()
        params = dict(params or {})
        params["include_transfers"] = 1
        resp = api_get("/transactions", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        self._selected_id = None  # Reset selection cache
        if not self._data:
            table.add_row("-", "-", "-", "No transactions", "-", "-")
        else:
            # Batch update for better performance
            rows = [
                (
                    str(t["id"]),
                    t.get("date", ""),
                    format_toman(t.get("amount", 0)),
                    t.get("category_name", "N/A"),
                    t.get("source_name") or "-",
                    (t.get("description") or "")[:25],
                )
                for t in self._data
            ]
            table.add_rows(rows)
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
        category_type = self.query_one("#tx_filter_type", Select).value
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if category_type not in (None, "all"):
            params["category_type"] = category_type
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
        self.query_one("#tx_filter_type", Select).value = "all"
        self.query_one("#tx_filter_min", Input).value = ""
        self.query_one("#tx_filter_max", Input).value = ""
        self.query_one("#tx_filter_desc", Input).value = ""
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        """Throttled row highlight handler for better performance."""
        from time import time
        now = time() * 1000  # Convert to ms
        
        # Throttle updates to every 50ms to improve performance
        if now - self._last_update_time < self._update_throttle_ms:
            return
        
        self._last_update_time = now
        self.update_detail()

    def update_detail(self):
        """Optimized detail update with caching."""
        tx_id = self._get_selected_id()
        
        # Early return if same ID (avoid redundant updates)
        if tx_id == getattr(self, '_selected_id', None):
            return
        
        self._selected_id = tx_id
        detail = self.query_one("#tx_detail", Static)
        
        if tx_id is None:
            detail.update("Select a transaction to see details.")
            return
        tx = next((t for t in getattr(self, "_data", []) if t["id"] == tx_id), None)
        if tx is None:
            detail.update("Select a transaction to see details.")
            return
        detail.update(
            f"[b]ID:[/b]          {tx['id']}\n"
            f"[b]Type:[/b]        {'Transfer' if tx.get('is_transfer') else 'Transaction'}\n"
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
        tx = next((item for item in getattr(self, "_data", []) if item["id"] == tx_id), None)
        if tx is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return
        
        def on_save():
            self.load_data()
        
        self.app.push_screen(
            TransactionEditScreen(tx_id, record_type=tx.get("record_type", "transaction"), on_save=on_save)
        )

    def action_delete_selected(self):
        tx_id = self._get_selected_id()
        if tx_id is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return
        tx = next((item for item in getattr(self, "_data", []) if item["id"] == tx_id), None)
        if tx is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            path = f"/transactions/{tx_id}?record_type={tx.get('record_type', 'transaction')}"
            resp = api_delete(path, username=self.app.user.get("username"))
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
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("TRANSACTIONS BY CATEGORY", classes="menu_header")
            yield Rule()
            yield Static(id="accordion_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Expand/Collapse  [E] Edit  [D] Delete  [Esc] Back", id="help")
            yield StatusBar("Enter=Toggle  E=Edit  D=Delete  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
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

        resp = api_get("/transactions", params={"include_transfers": 1}, username=self.app.user.get("username"))
        txs, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._transactions = txs or []
        self._render_accordion()

    def _get_groups(self):
        groups = []
        for cat in self._categories:
            groups.append(
                {
                    "key": f"category:{cat['id']}",
                    "title": cat["name"],
                    "type": cat["type"],
                    "record_type": "category",
                    "transactions": [t for t in self._transactions if t.get("category_id") == cat["id"]],
                }
            )

        transfer_txs = [t for t in self._transactions if t.get("is_transfer")]
        if transfer_txs:
            groups.append(
                {
                    "key": "transfer-group",
                    "title": "Transfers",
                    "type": "transfer",
                    "record_type": "transfer_group",
                    "transactions": transfer_txs,
                }
            )

        return groups

    def _render_accordion(self):
        content = self.query_one("#accordion_content", Static)
        lines = []
        groups = self._get_groups()
        if not groups:
            content.update("No categories found.")
            return

        for cat_idx, group in enumerate(groups):
            cat_id = group["key"]
            cat_name = group["title"]
            cat_type = group["type"]
            cat_txs = group["transactions"]
            total = sum(self._to_amount_value(t.get("amount", 0)) for t in cat_txs)

            is_selected = self._mode == "category" and self._selected_category_idx == cat_idx
            marker = ">" if is_selected else " "
            arrow = "▼" if cat_id in self._expanded else "▶"
            color = "green" if cat_type == "income" else "red" if cat_type == "cost" else "cyan"

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

    @staticmethod
    def _to_amount_value(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

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
        groups = self._get_groups()
        if not groups:
            return

        if self._mode == "category":
            self._selected_category_idx += direction
            self._selected_category_idx = max(0, min(self._selected_category_idx, len(groups) - 1))
            self._selected_tx_idx = 0
        else:
            cat_txs = groups[self._selected_category_idx]["transactions"]
            self._selected_tx_idx += direction
            self._selected_tx_idx = max(0, min(self._selected_tx_idx, len(cat_txs) - 1))

        self._render_accordion()

    def _toggle_expand(self):
        if self._mode == "transaction":
            self._mode = "category"
            self._selected_tx_idx = 0
            self._render_accordion()
            return

        groups = self._get_groups()
        if not groups:
            return
        group = groups[self._selected_category_idx]
        cat_id = group["key"]
        cat_txs = group["transactions"]

        if cat_id in self._expanded:
            self._expanded.discard(cat_id)
        else:
            self._expanded.add(cat_id)
            if cat_txs:
                self._mode = "transaction"
                self._selected_tx_idx = 0
        self._render_accordion()

    def _get_selected_tx(self):
        groups = self._get_groups()
        if self._mode != "transaction" or not groups:
            return None
        cat_txs = groups[self._selected_category_idx]["transactions"]
        if 0 <= self._selected_tx_idx < len(cat_txs):
            return cat_txs[self._selected_tx_idx]
        return None

    def action_edit_selected(self):
        tx = self._get_selected_tx()
        if tx is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return
        
        def on_save():
            self.load_data()
        
        self.app.push_screen(
            TransactionEditScreen(int(tx["id"]), record_type=tx.get("record_type", "transaction"), on_save=on_save)
        )

    def action_delete_selected(self):
        tx = self._get_selected_tx()
        if tx is None:
            self.app.push_screen(MessageBox("No transaction selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(
                f"/transactions/{int(tx['id'])}?record_type={tx.get('record_type', 'transaction')}",
                username=self.app.user.get("username"),
            )
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

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+d", "toggle_date_picker", "Date Picker"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("ADD TRANSACTION", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Date (Jalali):")
                        with Horizontal(classes="date_field_row"):
                            yield Input(placeholder="1405-01-31", id="tx_date")
                            yield Button("📅", id="btn_date_picker", classes="date_picker_btn")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Amount:")
                        yield Input(placeholder="100000", id="tx_amount")
                yield Checkbox("Save as transfer", id="tx_is_transfer")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Category:", id="tx_primary_label")
                        yield Select([], prompt="Loading...", id="tx_primary_select")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Source:", id="tx_secondary_label")
                        yield Select([], prompt="Loading...", id="tx_secondary_select")
                yield Label("Note (optional):")
                yield TextArea(id="tx_desc")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Tag (optional):")
                        yield Select([], prompt="None", id="tx_tag_select")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Label (optional):")
                        yield Select([], prompt="None", id="tx_label_select")
                yield Rule()
                yield Label("ITEMS (optional):", classes="section_header")
                yield Button("Items (0)", variant="default", id="open_items_btn")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Ctrl+D] Date picker  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Ctrl+D=Date Picker  Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        # Set current Jalali date as default
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        self.query_one("#tx_date", Input).value = date_str

        self._category_options = []
        self._source_options = []
        self._items = []
        self._available_tags = []
        self._available_labels = []
        self.load_categories()
        self.load_sources()
        self._apply_dynamic_fields(False)
        self._load_tag_options()
        self._load_label_options()

    def _load_tag_options(self):
        resp = api_get("/metadata/tags", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err or not data:
            return
        options = [(t["name"], t["id"]) for t in data]
        self.query_one("#tx_tag_select", Select).set_options(options)

    def _load_label_options(self):
        resp = api_get("/metadata/labels", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err or not data:
            return
        options = [(l["name"], l["id"]) for l in data]
        self.query_one("#tx_label_select", Select).set_options(options)

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self._category_options = []
            self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)
            return
        if not data:
            self._category_options = []
        else:
            self._category_options = [(f"{c['name']} ({c['type']})", c["id"]) for c in data]
        self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)

    def load_sources(self):
        resp = api_get("/sources", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self._source_options = []
            return
        if not data:
            self._source_options = []
        else:
            self._source_options = [(s["name"], s["id"]) for s in data]
        self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "tx_is_transfer":
            self._apply_dynamic_fields(event.value)

    def _apply_dynamic_fields(self, is_transfer: bool) -> None:
        primary_label = self.query_one("#tx_primary_label", Label)
        secondary_label = self.query_one("#tx_secondary_label", Label)
        primary_select = self.query_one("#tx_primary_select", Select)
        secondary_select = self.query_one("#tx_secondary_select", Select)

        if is_transfer:
            primary_label.update("From Source:")
            secondary_label.update("To Source:")
            primary_select.set_options(self._source_options)
            secondary_select.set_options(self._source_options)
            primary_select.prompt = "Select source" if self._source_options else "No sources"
            secondary_select.prompt = "Select source" if self._source_options else "No sources"
        else:
            primary_label.update("Category:")
            secondary_label.update("Source:")
            primary_select.set_options(self._category_options)
            secondary_select.set_options(self._source_options)
            primary_select.prompt = "Select category" if self._category_options else "No categories"
            secondary_select.prompt = "Select source" if self._source_options else "No sources"

        primary_select.clear()
        secondary_select.clear()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "btn_date_picker":
            self.action_toggle_date_picker()
        elif event.button.id == "today_btn":
            try:
                picker = self.query_one("#tx_date_picker", JalaliDatePicker)
                self.query_one("#tx_date", Input).value = picker.get_jalali_date()
                picker.remove()
                self.query_one("#tx_amount", Input).focus()
            except Exception:
                pass
        elif event.button.id == "open_items_btn":
            self.action_open_items()
        elif event.button.id == "cancel":
            self.action_go_back()

    def action_open_items(self):
        def on_items_done(items):
            if items is not None:
                self._items = items
                self._update_items_button()

        self.app.push_screen(
            TransactionItemsModal(existing_items=self._items),
            on_items_done,
        )

    def _update_items_button(self):
        try:
            btn = self.query_one("#open_items_btn", Button)
            btn.label = f"Items ({len(self._items)})"
        except Exception:
            pass

    def save(self):
        date = self.query_one("#tx_date", Input).value.strip()
        amount_str = self.query_one("#tx_amount", Input).value.strip()
        is_transfer = self.query_one("#tx_is_transfer", Checkbox).value
        primary_value = self.query_one("#tx_primary_select", Select).value
        secondary_value = self.query_one("#tx_secondary_select", Select).value
        desc = self.query_one("#tx_desc", TextArea).text.strip()

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
        payload = {
            "date": date,
            "amount": amount,
            "description": desc,
        }

        if is_transfer:
            if primary_value is None or primary_value == Select.BLANK:
                self.app.push_screen(MessageBox("From source is required", "Validation"))
                return
            if secondary_value is None or secondary_value == Select.BLANK:
                self.app.push_screen(MessageBox("To source is required", "Validation"))
                return
            if primary_value == secondary_value:
                self.app.push_screen(MessageBox("From source and to source must be different", "Validation"))
                return

            payload["is_transfer"] = True
            payload["from_source_id"] = primary_value
            payload["to_source_id"] = secondary_value
        else:
            if primary_value is None or primary_value == Select.BLANK:
                self.app.push_screen(MessageBox("Category is required", "Validation"))
                return
            payload["category_id"] = primary_value
            if secondary_value is not None and secondary_value != Select.BLANK:
                payload["source_id"] = secondary_value
            # Include items if any
            if self._items:
                payload["items"] = [
                    {"name": i["name"], "quantity": i["quantity"], "unit": i.get("unit"),
                     "unit_price": i["unit_price"], "total_price": i["total_price"]}
                    for i in self._items
                ]

        resp = api_post("/transactions", payload, username=self.app.user.get("username"))
        resp_data, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            # Set tags and labels on the new transaction
            tx_id = resp_data.get("id") if resp_data else None
            if tx_id and not is_transfer:
                tag_value = self.query_one("#tx_tag_select", Select).value
                label_value = self.query_one("#tx_label_select", Select).value
                username = self.app.user.get("username")
                if tag_value not in (None, Select.BLANK):
                    api_put(f"/metadata/transactions/{tx_id}/tags", {"tag_ids": [tag_value]}, username=username)
                if label_value not in (None, Select.BLANK):
                    api_put(f"/metadata/transactions/{tx_id}/labels", {"label_ids": [label_value]}, username=username)

            message = "Transfer added successfully." if is_transfer else "Transaction added successfully."

            def on_success_dismiss(_):
                now = datetime.now()
                jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
                self.query_one("#tx_date", Input).value = jalali_now.strftime("%Y-%m-%d")
                self.query_one("#tx_amount", Input).value = ""
                self.query_one("#tx_desc", TextArea).load_text("")
                self.query_one("#tx_is_transfer", Checkbox).value = False
                self._items = []
                self._update_items_button()
                self.query_one("#tx_tag_select", Select).clear()
                self.query_one("#tx_label_select", Select).clear()
                self.query_one("#tx_date", Input).focus()

            self.app.push_screen(MessageBox(message, "Success"), on_success_dismiss)

    def action_toggle_date_picker(self):
        scroll = self.query_one(".form_scroll", VerticalScroll)
        existing = list(scroll.query("JalaliDatePicker"))
        if existing:
            for picker in existing:
                picker.remove()
            date_input = self.query_one("#tx_date", Input)
            date_input.focus()
        else:
            date_input = self.query_one("#tx_date", Input)
            picker = JalaliDatePicker(id="tx_date_picker")
            if date_input.value:
                try:
                    parts = date_input.value.strip().split("-")
                    if len(parts) == 3:
                        picker._set_date(int(parts[0]), int(parts[1]), int(parts[2]))
                except Exception:
                    pass
            scroll.mount(picker, before=scroll.children[0] if scroll.children else None)
            picker.focus()

    def on_key(self, event):
        if event.key == "enter":
            focused = self.app.focused
            if focused and focused.id in {"tx_date_picker", "picker_year", "picker_month", "picker_day"}:
                event.stop()
                picker = self.query_one("#tx_date_picker", JalaliDatePicker)
                self.query_one("#tx_date", Input).value = picker.get_jalali_date()
                picker.remove()
                self.query_one("#tx_amount", Input).focus()
            elif focused and focused.id == "save":
                event.stop()
                self.save()
            elif focused and focused.id == "cancel":
                event.stop()
                self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()


class TransactionEditScreen(Screen):
    """Edit transaction screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+d", "toggle_date_picker", "Date Picker"),
    ]

    def __init__(self, tx_id: int, record_type: str = "transaction", on_save=None, **kwargs):
        self.tx_id = tx_id
        self.record_type = record_type
        self.on_save = on_save
        self._original_is_transfer = False
        self._hydrating_form = False
        self._items = []
        self._available_tags = []
        self._available_labels = []
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("EDIT TRANSACTION", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Date (Jalali):")
                        with Horizontal(classes="date_field_row"):
                            yield Input(placeholder="1405-01-31", id="tx_date")
                            yield Button("📅", id="btn_date_picker", classes="date_picker_btn")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Amount:")
                        yield Input(placeholder="100000", id="tx_amount")
                yield Checkbox("Save as transfer", id="tx_is_transfer")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Category:", id="tx_primary_label")
                        yield Select([], prompt="Loading...", id="tx_primary_select")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Source:", id="tx_secondary_label")
                        yield Select([], prompt="Loading...", id="tx_secondary_select")
                yield Label("Note (optional):")
                yield TextArea(id="tx_desc")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Tag (optional):")
                        yield Select([], prompt="None", id="tx_tag_select")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Label (optional):")
                        yield Select([], prompt="None", id="tx_label_select")
                yield Rule()
                yield Label("ITEMS (optional):", classes="section_header")
                yield Button("Items (0)", variant="default", id="open_items_btn")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Ctrl+D] Date picker  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Ctrl+D=Date Picker  Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        # Set current Jalali date as default
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        self.query_one("#tx_date", Input).value = date_str

        self._category_options = []
        self._source_options = []
        self._items = []
        self.load_categories()
        self.load_sources()
        self._load_tag_options()
        self._load_label_options()

        resp = api_get(
            f"/transactions/{self.tx_id}",
            params={"record_type": self.record_type},
            username=self.app.user.get("username"),
        )
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        self._original_is_transfer = bool(data.get("is_transfer"))
        self._hydrating_form = True
        transfer_toggle = self.query_one("#tx_is_transfer", Checkbox)
        transfer_toggle.value = self._original_is_transfer
        transfer_toggle.disabled = self._original_is_transfer
        self._apply_dynamic_fields(self._original_is_transfer, clear_selection=False)
        self.query_one("#tx_date", Input).value = data.get("date", "")
        self.query_one("#tx_amount", Input).value = str(data.get("amount", ""))
        self.query_one("#tx_desc", TextArea).load_text(data.get("description") or "")

        primary_select = self.query_one("#tx_primary_select", Select)
        secondary_select = self.query_one("#tx_secondary_select", Select)
        if self._original_is_transfer:
            if data.get("from_source_id") is not None:
                primary_select.value = data.get("from_source_id")
            if data.get("to_source_id") is not None:
                secondary_select.value = data.get("to_source_id")
        else:
            if data.get("category_id") is not None:
                primary_select.value = data.get("category_id")
            if data.get("source_id") is not None:
                secondary_select.value = data.get("source_id")
        self._hydrating_form = False

        # Load existing items
        existing_items = data.get("items") or []
        for item in existing_items:
            self._items.append({
                "name": item["name"],
                "quantity": float(item.get("quantity", 1)),
                "unit": item.get("unit"),
                "unit_price": float(item.get("unit_price") or 0),
                "total_price": float(item.get("total_price", 0)),
            })
        if self._items:
            self._update_items_button()

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self._category_options = []
            self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)
            return
        if not data:
            self._category_options = []
        else:
            self._category_options = [(f"{c['name']} ({c['type']})", c["id"]) for c in data]
        self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)

    def load_sources(self):
        resp = api_get("/sources", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self._source_options = []
            self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)
            return
        if not data:
            self._source_options = []
        else:
            self._source_options = [(s["name"], s["id"]) for s in data]
        self._apply_dynamic_fields(self.query_one("#tx_is_transfer", Checkbox).value)

    def _load_tag_options(self):
        resp = api_get("/metadata/tags", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err or not data:
            return
        options = [(t["name"], t["id"]) for t in data]
        self.query_one("#tx_tag_select", Select).set_options(options)
        # Pre-select existing tag
        try:
            tags_resp = api_get(f"/metadata/transactions/{self.tx_id}/tags", username=self.app.user.get("username"))
            existing_tags, _ = handle_response(tags_resp)
            if existing_tags and existing_tags[0]:
                self.query_one("#tx_tag_select", Select).value = existing_tags[0]["id"]
        except Exception:
            pass

    def _load_label_options(self):
        resp = api_get("/metadata/labels", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err or not data:
            return
        options = [(l["name"], l["id"]) for l in data]
        self.query_one("#tx_label_select", Select).set_options(options)
        # Pre-select existing label
        try:
            labels_resp = api_get(f"/metadata/transactions/{self.tx_id}/labels", username=self.app.user.get("username"))
            existing_labels, _ = handle_response(labels_resp)
            if existing_labels and existing_labels[0]:
                self.query_one("#tx_label_select", Select).value = existing_labels[0]["id"]
        except Exception:
            pass

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "tx_is_transfer":
            self._apply_dynamic_fields(event.value, clear_selection=not self._hydrating_form)

    def _apply_dynamic_fields(self, is_transfer: bool, clear_selection: bool = True) -> None:
        primary_label = self.query_one("#tx_primary_label", Label)
        secondary_label = self.query_one("#tx_secondary_label", Label)
        primary_select = self.query_one("#tx_primary_select", Select)
        secondary_select = self.query_one("#tx_secondary_select", Select)

        if is_transfer:
            primary_label.update("From Source:")
            secondary_label.update("To Source:")
            primary_select.set_options(self._source_options)
            secondary_select.set_options(self._source_options)
            primary_select.prompt = "Select source" if self._source_options else "No sources"
            secondary_select.prompt = "Select source" if self._source_options else "No sources"
        else:
            primary_label.update("Category:")
            secondary_label.update("Source:")
            primary_select.set_options(self._category_options)
            secondary_select.set_options(self._source_options)
            primary_select.prompt = "Select category" if self._category_options else "No categories"
            secondary_select.prompt = "Select source" if self._source_options else "No sources"

        if clear_selection:
            primary_select.clear()
            secondary_select.clear()

    def action_open_items(self):
        def on_items_done(items):
            if items is not None:
                self._items = items
                self._update_items_button()

        self.app.push_screen(
            TransactionItemsModal(existing_items=self._items),
            on_items_done,
        )

    def _update_items_button(self):
        try:
            btn = self.query_one("#open_items_btn", Button)
            btn.label = f"Items ({len(self._items)})"
        except Exception:
            pass

    def action_toggle_date_picker(self):
        scroll = self.query_one(".form_scroll", VerticalScroll)
        existing = list(scroll.query("JalaliDatePicker"))
        if existing:
            for picker in existing:
                picker.remove()
            date_input = self.query_one("#tx_date", Input)
            date_input.focus()
        else:
            date_input = self.query_one("#tx_date", Input)
            picker = JalaliDatePicker(id="tx_date_picker")
            if date_input.value:
                try:
                    parts = date_input.value.strip().split("-")
                    if len(parts) == 3:
                        picker._set_date(int(parts[0]), int(parts[1]), int(parts[2]))
                except Exception:
                    pass
            scroll.mount(picker, before=scroll.children[0] if scroll.children else None)
            picker.focus()

    def on_key(self, event):
        if event.key == "enter":
            focused = self.app.focused
            if focused and focused.id in {"tx_date_picker", "picker_year", "picker_month", "picker_day"}:
                event.stop()
                picker = self.query_one("#tx_date_picker", JalaliDatePicker)
                self.query_one("#tx_date", Input).value = picker.get_jalali_date()
                picker.remove()
                self.query_one("#tx_amount", Input).focus()
            elif focused and focused.id == "save":
                event.stop()
                self.save()
            elif focused and focused.id == "cancel":
                event.stop()
                self.action_go_back()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "btn_date_picker":
            self.action_toggle_date_picker()
        elif event.button.id == "today_btn":
            try:
                picker = self.query_one("#tx_date_picker", JalaliDatePicker)
                self.query_one("#tx_date", Input).value = picker.get_jalali_date()
                picker.remove()
                self.query_one("#tx_amount", Input).focus()
            except Exception:
                pass
        elif event.button.id == "open_items_btn":
            self.action_open_items()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        date = self.query_one("#tx_date", Input).value.strip()
        amount_str = self.query_one("#tx_amount", Input).value.strip()
        is_transfer = self.query_one("#tx_is_transfer", Checkbox).value
        primary_value = self.query_one("#tx_primary_select", Select).value
        secondary_value = self.query_one("#tx_secondary_select", Select).value
        desc = self.query_one("#tx_desc", TextArea).text.strip()

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

        payload = {
            "date": date,
            "amount": amount,
            "description": desc,
            "is_transfer": is_transfer,
            "original_is_transfer": self._original_is_transfer,
        }

        if is_transfer:
            if primary_value is None or primary_value == Select.BLANK:
                self.app.push_screen(MessageBox("From source is required", "Validation"))
                return
            if secondary_value is None or secondary_value == Select.BLANK:
                self.app.push_screen(MessageBox("To source is required", "Validation"))
                return
            if primary_value == secondary_value:
                self.app.push_screen(MessageBox("From source and to source must be different", "Validation"))
                return
            payload["from_source_id"] = primary_value
            payload["to_source_id"] = secondary_value
        else:
            if primary_value is None or primary_value == Select.BLANK:
                self.app.push_screen(MessageBox("Category is required", "Validation"))
                return
            payload["category_id"] = primary_value
            if secondary_value is not None and secondary_value != Select.BLANK:
                payload["source_id"] = secondary_value
            # Include items if any
            if self._items:
                payload["items"] = [
                    {"name": i["name"], "quantity": i["quantity"], "unit": i.get("unit"),
                     "unit_price": i["unit_price"], "total_price": i["total_price"]}
                    for i in self._items
                ]

        resp = api_put(
            f"/transactions/{self.tx_id}?record_type={self.record_type}",
            payload,
            username=self.app.user.get("username"),
        )
        data, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            # Set tags and labels on the transaction
            if not is_transfer:
                tag_value = self.query_one("#tx_tag_select", Select).value
                label_value = self.query_one("#tx_label_select", Select).value
                username = self.app.user.get("username")
                if tag_value not in (None, Select.BLANK):
                    api_put(f"/metadata/transactions/{self.tx_id}/tags", {"tag_ids": [tag_value]}, username=username)
                if label_value not in (None, Select.BLANK):
                    api_put(f"/metadata/transactions/{self.tx_id}/labels", {"label_ids": [label_value]}, username=username)

            self._original_is_transfer = bool(data.get("is_transfer", is_transfer))
            if self.on_save:
                self.on_save()
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()
