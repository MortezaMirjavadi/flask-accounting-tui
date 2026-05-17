"""Check management screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Select, Static, Rule, TextArea
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar
from app.utils.helpers import jalali_to_gregorian, gregorian_to_jalali


class ChecksScreen(Screen):
    """Checks menu."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("CHECKS", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. List Checks")),
                ListItem(Label("2. Add Check")),
                ListItem(Label("3. Back to Main Menu")),
                id="chk_menu_list",
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
        self.app.push_screen(CheckListScreen())

    def action_do_add(self):
        self.app.push_screen(CheckAddScreen())


class CheckListScreen(Screen):
    """Check list with filtering."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("c", "clear_selected", "Clear"),
        Binding("b", "bounce_selected", "Bounce"),
        Binding("x", "cancel_selected", "Cancel"),
        Binding("f", "apply_filter", "Filter"),
        Binding("r", "reset_filter", "Reset"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("CHECK LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Bank name", id="chk_filter_bank")
                yield Input(placeholder="Check number", id="chk_filter_number")
                yield Select(
                    [
                        ("All Status", ""),
                        ("Pending", "pending"),
                        ("Cleared", "cleared"),
                        ("Bounced", "bounced"),
                        ("Canceled", "canceled"),
                    ],
                    prompt="Status",
                    id="chk_filter_status",
                )
                yield Select(
                    [
                        ("All Types", ""),
                        ("Issued", "issued"),
                        ("Received", "received"),
                    ],
                    prompt="Type",
                    id="chk_filter_type",
                )
                yield Button("Filter", variant="primary", id="chk_filter_btn")
                yield Button("Reset", variant="default", id="chk_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="chk_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="chk_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip(
                "[↑/↓] Navigate  [E] Edit  [D] Delete  [C] Clear  [B] Bounce  [X] Cancel  [F] Filter  [R] Reset  [Esc] Back",
                id="help",
            )
            yield StatusBar("E=Edit  D=Delete  C=Clear  B=Bounce  X=Cancel  F=Filter  R=Reset  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#chk_table", DataTable)
        table.add_columns("ID", "Number", "Bank", "Amount", "Due Date", "Type", "Status")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#chk_table", DataTable)
        table.clear()
        resp = api_get("/checks", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "-", "No checks", "-", "-", "-", "-")
        else:
            for c in self._data:
                due_jalali = gregorian_to_jalali(c.get("due_date", "")) if c.get("due_date") else ""
                table.add_row(
                    str(c["id"]),
                    c.get("check_number") or "-",
                    c.get("bank_name") or "-",
                    format_toman(c.get("amount", 0)),
                    due_jalali,
                    c.get("type", ""),
                    c.get("status", ""),
                )
        self.update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chk_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "chk_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        bank = self.query_one("#chk_filter_bank", Input).value.strip()
        number = self.query_one("#chk_filter_number", Input).value.strip()
        status = self.query_one("#chk_filter_status", Select).value
        chk_type = self.query_one("#chk_filter_type", Select).value
        params = {}
        if bank:
            params["bank_name"] = bank
        if number:
            params["check_number"] = number
        # Skip invalid Select values: None, Select.BLANK, or string containing "null" or blank
        if status and status is not Select.BLANK:
            status_str = str(status).strip().lower()
            if status_str and status_str not in ("", "none", "null", "select.null", "select.blank"):
                params["status"] = str(self.query_one("#chk_filter_status", Select).value)
        if chk_type and chk_type is not Select.BLANK:
            type_str = str(chk_type).strip().lower()
            if type_str and type_str not in ("", "none", "null", "select.null", "select.blank"):
                params["type"] = str(self.query_one("#chk_filter_type", Select).value)
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#chk_filter_bank", Input).value = ""
        self.query_one("#chk_filter_number", Input).value = ""
        self.query_one("#chk_filter_status", Select).clear()
        self.query_one("#chk_filter_type", Select).clear()
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#chk_detail", Static)
        chk_id = self._get_selected_id()
        if chk_id is None:
            detail.update("Select a check to see details.")
            return
        chk = next((c for c in getattr(self, "_data", []) if c["id"] == chk_id), None)
        if chk is None:
            detail.update("Select a check to see details.")
            return
        issue_jalali = gregorian_to_jalali(chk.get("issue_date", "")) if chk.get("issue_date") else ""
        due_jalali = gregorian_to_jalali(chk.get("due_date", "")) if chk.get("due_date") else ""
        detail.update(
            f"[b]ID:[/b]           {chk['id']}\n"
            f"[b]Number:[/b]       {chk.get('check_number') or '-'}\n"
            f"[b]Bank:[/b]         {chk.get('bank_name') or '-'}\n"
            f"[b]Amount:[/b]       {format_toman(chk.get('amount', 0))}\n"
            f"[b]Issue Date:[/b]   {issue_jalali}\n"
            f"[b]Due Date:[/b]     {due_jalali}\n"
            f"[b]Type:[/b]         {chk.get('type', '')}\n"
            f"[b]Status:[/b]       {chk.get('status', '')}\n"
            f"[b]Description:[/b]  {chk.get('description') or '-'}\n"
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
        elif key == "c":
            event.stop()
            self.action_clear_selected()
        elif key == "b":
            event.stop()
            self.action_bounce_selected()
        elif key == "x":
            event.stop()
            self.action_cancel_selected()

    def _get_selected_id(self):
        table = self.query_one("#chk_table", DataTable)
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
        chk_id = self._get_selected_id()
        if chk_id is None:
            self.app.push_screen(MessageBox("No check selected.", "Info"))
            return

        def on_save():
            self.load_data()

        self.app.push_screen(CheckEditScreen(chk_id, on_save=on_save))

    def action_delete_selected(self):
        chk_id = self._get_selected_id()
        if chk_id is None:
            self.app.push_screen(MessageBox("No check selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/checks/{chk_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected check?", "Confirm"), on_confirm)

    def action_clear_selected(self):
        chk_id = self._get_selected_id()
        if chk_id is None:
            self.app.push_screen(MessageBox("No check selected.", "Info"))
            return
        chk = next((c for c in getattr(self, "_data", []) if c["id"] == chk_id), None)
        if chk is None:
            return
        if chk.get("status") != "pending":
            self.app.push_screen(MessageBox("Only pending checks can be cleared.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_post(f"/checks/{chk_id}/clear", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Mark this check as cleared?", "Confirm"), on_confirm)

    def action_bounce_selected(self):
        chk_id = self._get_selected_id()
        if chk_id is None:
            self.app.push_screen(MessageBox("No check selected.", "Info"))
            return
        chk = next((c for c in getattr(self, "_data", []) if c["id"] == chk_id), None)
        if chk is None:
            return
        if chk.get("status") != "pending":
            self.app.push_screen(MessageBox("Only pending checks can be bounced.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_post(f"/checks/{chk_id}/bounce", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Mark this check as bounced?", "Confirm"), on_confirm)

    def action_cancel_selected(self):
        chk_id = self._get_selected_id()
        if chk_id is None:
            self.app.push_screen(MessageBox("No check selected.", "Info"))
            return
        chk = next((c for c in getattr(self, "_data", []) if c["id"] == chk_id), None)
        if chk is None:
            return
        if chk.get("status") != "pending":
            self.app.push_screen(MessageBox("Only pending checks can be canceled.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_post(f"/checks/{chk_id}/cancel", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Cancel this check?", "Confirm"), on_confirm)


class CheckAddScreen(Screen):
    """Add new check screen."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("ADD CHECK", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                yield Label("Check Number:")
                yield Input(placeholder="Optional check number", id="chk_number")
                yield Label("Bank Name:")
                yield Input(placeholder="Optional bank name", id="chk_bank")
                yield Label("Amount:")
                yield Input(placeholder="Amount in toman", id="chk_amount")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Issue Date (Jalali):")
                        yield Input(placeholder="1405-01-01", id="chk_issue_date")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Due Date (Jalali):")
                        yield Input(placeholder="1405-03-01", id="chk_due_date")
                yield Label("Type:")
                yield Select(
                    [("Issued", "issued"), ("Received", "received")],
                    prompt="Select type",
                    id="chk_type",
                )
                yield Label("Category:")
                yield Select([], prompt="Loading...", id="chk_category")
                yield Label("Wallet (optional):")
                yield Select([], prompt="Loading...", id="chk_wallet")
                yield Label("Description (optional):")
                yield TextArea(id="chk_desc")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        self._load_categories()
        self._load_wallets()

    def _load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        select = self.query_one("#chk_category", Select)
        if err or not data:
            select.set_options([])
            select.prompt = "No categories"
        else:
            options = [(f"{c['name']} ({c['type']})", c["id"]) for c in data]
            select.set_options(options)
            select.prompt = "Select category"

    def _load_wallets(self):
        resp = api_get("/wallets", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        select = self.query_one("#chk_wallet", Select)
        if err or not data:
            select.set_options([])
            select.prompt = "No wallets"
        else:
            options = [(s["name"], s["id"]) for s in data]
            select.set_options(options)
            select.prompt = "Select wallet"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        number = self.query_one("#chk_number", Input).value.strip() or None
        bank = self.query_one("#chk_bank", Input).value.strip() or None
        amount_str = self.query_one("#chk_amount", Input).value.strip()
        issue_date = self.query_one("#chk_issue_date", Input).value.strip()
        due_date = self.query_one("#chk_due_date", Input).value.strip()
        chk_type = self.query_one("#chk_type", Select).value
        category_id = self.query_one("#chk_category", Select).value
        wallet_id = self.query_one("#chk_wallet", Select).value
        desc = self.query_one("#chk_desc", TextArea).text.strip() or None

        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return

        if not issue_date:
            self.app.push_screen(MessageBox("Issue date is required", "Validation"))
            return
        if not due_date:
            self.app.push_screen(MessageBox("Due date is required", "Validation"))
            return
        if chk_type is None or chk_type == Select.BLANK:
            self.app.push_screen(MessageBox("Type is required", "Validation"))
            return
        if category_id is None or category_id == Select.BLANK:
            self.app.push_screen(MessageBox("Category is required", "Validation"))
            return

        try:
            issue_gregorian = jalali_to_gregorian(issue_date)
            due_gregorian = jalali_to_gregorian(due_date)
        except ValueError as exc:
            self.app.push_screen(MessageBox(str(exc), "Validation"))
            return

        payload = {
            "check_number": number,
            "bank_name": bank,
            "amount": amount,
            "issue_date": issue_gregorian,
            "due_date": due_gregorian,
            "type": str(chk_type),
            "category_id": category_id,
            "wallet_id": wallet_id if wallet_id is not None and wallet_id != Select.BLANK else None,
            "description": desc,
        }
        resp = api_post("/checks", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Check added successfully.", "Success"))
            self.query_one("#chk_number", Input).value = ""
            self.query_one("#chk_bank", Input).value = ""
            self.query_one("#chk_amount", Input).value = ""
            self.query_one("#chk_issue_date", Input).value = ""
            self.query_one("#chk_due_date", Input).value = ""
            self.query_one("#chk_type", Select).clear()
            self.query_one("#chk_category", Select).clear()
            self.query_one("#chk_wallet", Select).clear()
            self.query_one("#chk_desc", TextArea).load_text("")


class CheckEditScreen(Screen):
    """Edit check screen (due date and description only; other fields are fixed after creation)."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, chk_id: int, on_save=None, **kwargs):
        self.chk_id = chk_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("EDIT CHECK", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                yield Label("Check Number:")
                yield Input(id="chk_number", disabled=True)
                yield Label("Bank Name:")
                yield Input(id="chk_bank", disabled=True)
                yield Label("Amount:")
                yield Input(id="chk_amount", disabled=True)
                yield Label("Issue Date (Jalali):")
                yield Input(id="chk_issue_date", disabled=True)
                yield Label("Due Date (Jalali):")
                yield Input(placeholder="1405-03-01", id="chk_due_date")
                yield Label("Type:")
                yield Input(id="chk_type", disabled=True)
                yield Label("Category:")
                yield Input(id="chk_category", disabled=True)
                yield Label("Wallet:")
                yield Input(id="chk_wallet", disabled=True)
                yield Label("Status:")
                yield Input(id="chk_status", disabled=True)
                yield Label("Description (optional):")
                yield TextArea(id="chk_desc")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/checks/{self.chk_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data
        issue_jalali = gregorian_to_jalali(data.get("issue_date", "")) if data.get("issue_date") else ""
        due_jalali = gregorian_to_jalali(data.get("due_date", "")) if data.get("due_date") else ""
        self.query_one("#chk_number", Input).value = data.get("check_number") or ""
        self.query_one("#chk_bank", Input).value = data.get("bank_name") or ""
        self.query_one("#chk_amount", Input).value = str(data.get("amount", ""))
        self.query_one("#chk_issue_date", Input).value = issue_jalali
        self.query_one("#chk_due_date", Input).value = due_jalali
        self.query_one("#chk_type", Input).value = data.get("type", "")
        self.query_one("#chk_category", Input).value = str(data.get("category_id", ""))
        self.query_one("#chk_wallet", Input).value = str(data.get("wallet_id") or "")
        self.query_one("#chk_status", Input).value = data.get("status", "")
        self.query_one("#chk_desc", TextArea).load_text(data.get("description") or "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        due_date = self.query_one("#chk_due_date", Input).value.strip()
        desc = self.query_one("#chk_desc", TextArea).text.strip() or None

        if not due_date:
            self.app.push_screen(MessageBox("Due date is required", "Validation"))
            return

        try:
            due_gregorian = jalali_to_gregorian(due_date)
        except ValueError as exc:
            self.app.push_screen(MessageBox(str(exc), "Validation"))
            return

        payload = {"due_date": due_gregorian}
        if desc is not None:
            payload["description"] = desc

        resp = api_put(f"/checks/{self.chk_id}/due-date", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()
