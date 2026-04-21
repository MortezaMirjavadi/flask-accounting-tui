import math
import sys
from datetime import datetime

import jdatetime
import requests
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    Rule,
    ListView,
    Select,
    Static,
)

BASE_URL = "http://127.0.0.1:5000"


# Persian month names mapping
PERSIAN_MONTHS = [
    ("1 - Farvardin", 1),
    ("2 - Ordibehesht", 2),
    ("3 - Khordad", 3),
    ("4 - Tir", 4),
    ("5 - Mordad", 5),
    ("6 - Shahrivar", 6),
    ("7 - Mehr", 7),
    ("8 - Aban", 8),
    ("9 - Azar", 9),
    ("10 - Dey", 10),
    ("11 - Bahman", 11),
    ("12 - Esfand", 12),
]


def get_persian_month_name(month_num):
    """Get Persian month name from month number."""
    month_names = {
        1: "Farvardin", 2: "Ordibehesht", 3: "Khordad",
        4: "Tir", 5: "Mordad", 6: "Shahrivar",
        7: "Mehr", 8: "Aban", 9: "Azar",
        10: "Dey", 11: "Bahman", 12: "Esfand"
    }
    return month_names.get(month_num, str(month_num))


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path, params=None, username=None):
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.get(f"{BASE_URL}{path}", params=params, headers=headers, timeout=10)
    except requests.RequestException:
        return None


def api_post(path, payload, username=None):
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        return None


def api_put(path, payload, username=None):
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.put(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        return None


def api_delete(path, username=None):
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.delete(f"{BASE_URL}{path}", headers=headers, timeout=10)
    except requests.RequestException:
        return None


def format_toman(amount):
    """Format a number as Toman (Persian currency)."""
    try:
        return f"{float(amount):,.0f} Toman"
    except (TypeError, ValueError):
        return "0 Toman"


def handle_response(resp):
    if resp is None:
        return None, "Network error"
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    if not resp.ok:
        err_text = str(data)
        if err_text.strip().startswith("<"):
            err_text = f"Server error {resp.status_code}"
        return None, err_text
    return data, None


# ---------------------------------------------------------------------------
# Shared widgets
# ---------------------------------------------------------------------------

class StatusBar(Static):
    status_text = reactive("Ready")

    def __init__(self, text="Ready", **kwargs):
        super().__init__(text, **kwargs)
        self.status_text = text

    def on_mount(self):
        self.set_interval(1, self.update_status)
        self.update_status()

    def watch_status_text(self, text: str):
        self.update(text)

    def update_status(self):
        user = getattr(self.app, "user", None)
        username = user.get("username", "Guest") if user else "Guest"
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        shamsi_str = jalali_now.strftime("%Y-%m-%d %H:%M:%S")
        self.status_text = f"User: {username}  |  {shamsi_str}"


class HelpTip(Static):
    def __init__(self, text="", **kwargs):
        super().__init__(text, **kwargs)


class MessageBox(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    def __init__(self, message, title="Message", is_error=False, **kwargs):
        self.message_text = message
        self.title_text = title
        self.is_error = is_error
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Container(classes="dialog"):
            yield Label(self.title_text, classes="dialog_title error_title" if self.is_error else "dialog_title")
            yield Static(self.message_text, classes="dialog_message error_message" if self.is_error else "dialog_message")
            yield Button("OK", variant="error" if self.is_error else "primary", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_dismiss(self):
        self.dismiss()


class ConfirmBox(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "dismiss_false", "No")]

    def __init__(self, message, title="Confirm", **kwargs):
        self.message_text = message
        self.title_text = title
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Container(classes="dialog"):
            yield Label(self.title_text, classes="dialog_title")
            yield Static(self.message_text, classes="dialog_message")
            with Horizontal(classes="dialog_buttons"):
                yield Button("Yes", variant="primary", id="yes")
                yield Button("No", variant="default", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_dismiss_false(self):
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginScreen(Screen):
    BINDINGS = [
        Binding("escape", "quit", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("TERMINAL ACCOUNTING SYSTEM", classes="main_title")
            yield Static("=" * 50, classes="separator")
            yield Label("LOGIN", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Label("Username:")
            yield Input(placeholder="Username", id="login_user")
            yield Label("Password:")
            yield Input(placeholder="Password", password=True, id="login_pass")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Login", variant="primary", id="login_btn")
                yield Button("Register", variant="default", id="register_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Login  [Esc] Exit", id="help")
            yield StatusBar("Enter=Login  Esc=Quit", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login_btn":
            self.do_login()
        elif event.button.id == "register_btn":
            self.do_register()

    def do_login(self):
        username = self.query_one("#login_user", Input).value.strip()
        password = self.query_one("#login_pass", Input).value
        if not username or not password:
            self.app.push_screen(MessageBox("Username and password are required.", "Validation"))
            return
        resp = api_post("/auth/login", {"username": username, "password": password}, username=username)
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.user = data
            self.app.push_screen(MainMenuScreen())

    def do_register(self):
        username = self.query_one("#login_user", Input).value.strip()
        password = self.query_one("#login_pass", Input).value
        if not username or not password:
            self.app.push_screen(MessageBox("Username and password are required.", "Validation"))
            return
        resp = api_post("/auth/register", {"username": username, "password": password}, username=username)
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Registration successful. Please log in.", "Success"))

    def action_quit(self):
        self.app.action_quit()


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Exit"),
        Binding("1", "go_categories", "Categories"),
        Binding("2", "go_sources", "Sources"),
        Binding("3", "go_transactions", "Transactions"),
        Binding("4", "go_reports", "Reports"),
        Binding("5", "go_budget", "Budget"),
        Binding("6", "go_settings", "Settings"),
        Binding("l", "logout", "Logout"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("TERMINAL ACCOUNTING SYSTEM", classes="main_title")
            yield Static("=" * 50, classes="separator")
            user = getattr(self.app, "user", None)
            if user:
                yield Label(f"Welcome, {user.get('username', '')}!", classes="menu_header")
            else:
                yield Label("Main Menu", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Categories")),
                ListItem(Label("2. Sources")),
                ListItem(Label("3. Transactions")),
                ListItem(Label("4. Reports")),
                ListItem(Label("5. Budget")),
                ListItem(Label("6. Settings")),
                ListItem(Label("7. Logout")),
                ListItem(Label("8. Exit")),
                id="main_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            now = datetime.now()
            jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
            shamsi_str = jalali_now.strftime("%Y-%m-%d")
            yield HelpTip(f"Date: [{shamsi_str}]  [↑/↓] Navigate  [Enter] Select  [1-6] Quick select  [L] Logout  [Q] Exit", id="help")
            yield StatusBar("Enter=Select  Esc=Back  L=Logout  Q=Quit", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.app.push_screen(CategoriesScreen())
        elif idx == 1:
            self.app.push_screen(SourcesScreen())
        elif idx == 2:
            self.app.push_screen(TransactionsScreen())
        elif idx == 3:
            self.app.push_screen(ReportsScreen())
        elif idx == 4:
            self.app.push_screen(BudgetScreen())
        elif idx == 5:
            self.app.push_screen(SettingsScreen())
        elif idx == 6:
            self.action_logout()
        elif idx == 7:
            self.app.action_quit()

    def action_go_categories(self):
        self.app.push_screen(CategoriesScreen())

    def action_go_sources(self):
        self.app.push_screen(SourcesScreen())

    def action_go_transactions(self):
        self.app.push_screen(TransactionsScreen())

    def action_go_reports(self):
        self.app.push_screen(ReportsScreen())

    def action_go_budget(self):
        self.app.push_screen(BudgetScreen())

    def action_go_settings(self):
        self.app.push_screen(SettingsScreen())

    def action_logout(self):
        self.app.user = None
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        self.app.push_screen(LoginScreen())


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoriesScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("CATEGORIES", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. List Categories")),
                ListItem(Label("2. Add Category")),
                ListItem(Label("3. Back to Main Menu")),
                id="cat_menu_list",
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
            self.action_do_add()
        elif idx == 2:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_list(self):
        self.app.push_screen(CategoryListScreen())

    def action_do_add(self):
        self.app.push_screen(CategoryAddScreen())


class CategoryListScreen(Screen):
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
            yield Label("CATEGORY LIST", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Filter by name", id="cat_filter_name")
                yield Select(
                    [("All Types", ""), ("Income", "income"), ("Cost", "cost")],
                    prompt="Filter by type",
                    id="cat_filter_type",
                )
                yield Button("Filter", variant="primary", id="cat_filter_btn")
                yield Button("Reset", variant="default", id="cat_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="cat_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Static("-" * 25, classes="separator")
                    yield Static(id="cat_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  F=Filter  R=Reset  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#cat_table", DataTable)
        table.add_columns("ID", "Name", "Type")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#cat_table", DataTable)
        table.clear()
        resp = api_get("/categories", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No categories found", "-")
        else:
            for c in self._data:
                table.add_row(str(c["id"]), c["name"], c["type"])
        self.update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cat_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "cat_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        name = self.query_one("#cat_filter_name", Input).value.strip()
        cat_type = self.query_one("#cat_filter_type", Select).value
        params = {}
        if name:
            params["name"] = name
        if cat_type and cat_type is not Select.BLANK:
            params["type"] = str(cat_type)
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#cat_filter_name", Input).value = ""
        self.query_one("#cat_filter_type", Select).clear()
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#cat_detail", Static)
        cat_id = self._get_selected_id()
        if cat_id is None:
            detail.update("Select a category to see details.")
            return
        cat = next((c for c in getattr(self, "_data", []) if c["id"] == cat_id), None)
        if cat is None:
            detail.update("Select a category to see details.")
            return
        detail.update(
            f"[b]ID:[/b]        {cat['id']}\n"
            f"[b]Name:[/b]      {cat['name']}\n"
            f"[b]Type:[/b]      {cat['type']}\n"
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
        table = self.query_one("#cat_table", DataTable)
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
        cat_id = self._get_selected_id()
        if cat_id is None:
            self.app.push_screen(MessageBox("No category selected.", "Info"))
            return
        def on_save():
            self.load_data()
        self.app.push_screen(CategoryEditScreen(cat_id, on_save=on_save))

    def action_delete_selected(self):
        cat_id = self._get_selected_id()
        if cat_id is None:
            self.app.push_screen(MessageBox("No category selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/categories/{cat_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected category?", "Confirm"), on_confirm)


class CategoryAddScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("ADD CATEGORY", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Label("Name:")
            yield Input(placeholder="Category name", id="cat_name")
            yield Label("Type:")
            yield Select(
                [("Income", "income"), ("Cost", "cost")],
                prompt="Select type",
                id="cat_type",
            )
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        name = self.query_one("#cat_name", Input).value.strip()
        cat_type = self.query_one("#cat_type", Select).value
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if cat_type is None or cat_type == Select.BLANK:
            self.app.push_screen(MessageBox("Type is required", "Validation"))
            return
        resp = api_post("/categories", {"name": name, "type": str(cat_type)}, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Category added successfully.", "Success"))
            self.query_one("#cat_name", Input).value = ""


class CategoryEditScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, cat_id: int, on_save=None, **kwargs):
        self.cat_id = cat_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("EDIT CATEGORY", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Label("Name:")
            yield Input(placeholder="Category name", id="cat_name")
            yield Label("Type:")
            yield Select(
                [("Income", "income"), ("Cost", "cost")],
                prompt="Select type",
                id="cat_type",
            )
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/categories/{self.cat_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self.query_one("#cat_name", Input).value = data.get("name", "")
        self.query_one("#cat_type", Select).value = data.get("type", "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        name = self.query_one("#cat_name", Input).value.strip()
        cat_type = self.query_one("#cat_type", Select).value
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if cat_type is None or cat_type == Select.BLANK:
            self.app.push_screen(MessageBox("Type is required", "Validation"))
            return
        resp = api_put(f"/categories/{self.cat_id}", {"name": name, "type": str(cat_type)}, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class SourcesScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("SOURCES", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. List Sources")),
                ListItem(Label("2. Add Source")),
                ListItem(Label("3. Back to Main Menu")),
                id="src_menu_list",
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
            self.action_do_add()
        elif idx == 2:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_list(self):
        self.app.push_screen(SourceListScreen())

    def action_do_add(self):
        self.app.push_screen(SourceAddScreen())


class SourceListScreen(Screen):
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
            yield Label("SOURCE LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Filter by name", id="src_filter_name")
                yield Input(placeholder="Min amount", id="src_filter_min")
                yield Input(placeholder="Max amount", id="src_filter_max")
                yield Button("Filter", variant="primary", id="src_filter_btn")
                yield Button("Reset", variant="default", id="src_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="src_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="src_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  F=Filter  R=Reset  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#src_table", DataTable)
        table.add_columns("ID", "Name", "Amount")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#src_table", DataTable)
        table.clear()
        resp = api_get("/sources", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No sources found")
        else:
            for s in self._data:
                table.add_row(str(s["id"]), s["name"], format_toman(s["amount"]))
        self.update_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "src_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "src_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        name = self.query_one("#src_filter_name", Input).value.strip()
        min_amt = self.query_one("#src_filter_min", Input).value.strip()
        max_amt = self.query_one("#src_filter_max", Input).value.strip()
        params = {}
        if name:
            params["name"] = name
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
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#src_filter_name", Input).value = ""
        self.query_one("#src_filter_min", Input).value = ""
        self.query_one("#src_filter_max", Input).value = ""
        self.load_data()

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#src_detail", Static)
        src_id = self._get_selected_id()
        if src_id is None:
            detail.update("Select a source to see details.")
            return
        src = next((s for s in getattr(self, "_data", []) if s["id"] == src_id), None)
        if src is None:
            detail.update("Select a source to see details.")
            return
        # Fetch balance
        bal_resp = api_get(f"/sources/{src_id}/balance", username=self.app.user.get("username"))
        bal_data, bal_err = handle_response(bal_resp)
        if bal_err or bal_data is None:
            bal_info = "Balance: N/A"
        else:
            bal = bal_data.get("balance", 0)
            bal_info = f"Balance: {format_toman(bal)}"
        detail.update(
            f"[b]ID:[/b]        {src['id']}\n"
            f"[b]Name:[/b]      {src['name']}\n"
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
            self.app.push_screen(MessageBox("No source selected.", "Info"))
            return
        def on_save():
            self.load_data()
        self.app.push_screen(SourceEditScreen(src_id, on_save=on_save))

    def action_delete_selected(self):
        src_id = self._get_selected_id()
        if src_id is None:
            self.app.push_screen(MessageBox("No source selected.", "Info"))
            return

        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            resp = api_delete(f"/sources/{src_id}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()

        self.app.push_screen(ConfirmBox("Delete selected source?", "Confirm"), on_confirm)


class SourceAddScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("ADD SOURCE", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Label("Name:")
            yield Input(placeholder="Source name (e.g. Bank, Cash)", id="src_name")
            yield Label("Amount:")
            yield Input(placeholder="Source amount)", id="src_amount")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
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
        amount_str = self.query_one("#src_amount", Input).value.strip()
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        payload = {
            "name": name,
            "amount": amount,
        }
        resp = api_post("/sources", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Source added successfully.", "Success"))
            self.query_one("#src_name", Input).value = ""
            self.query_one("#src_amount", Input).value = ""


class SourceEditScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, src_id: int, on_save=None, **kwargs):
        self.src_id = src_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("EDIT SOURCE", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Label("Name:")
            yield Input(placeholder="Source name", id="src_name")
            yield Label("Amount:")
            yield Input(placeholder="10000", id="src_amount")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/sources/{self.src_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self.query_one("#src_name", Input).value = data.get("name", "")
        self.query_one("#src_amount", Input).value = str(data.get("amount", 0))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def save(self):
        name = self.query_one("#src_name", Input).value.strip()
        amount_str = self.query_one("#src_amount", Input).value.strip()
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        payload = {
            "name": name,
            "amount": amount,
        }
        resp = api_put(f"/sources/{self.src_id}", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TransactionsScreen(Screen):
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
            yield Static("-" * 50, classes="separator")
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
                    yield Static("-" * 25, classes="separator")
                    yield Static(id="tx_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  F=Filter  R=Reset  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tx_table", DataTable)
        table.add_columns("ID", "Date", "Amount", "Category", "Source", "Description")
        table.cursor_type = "row"
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
        self._mode = "category"  # "category" or "transaction"
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
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("ADD TRANSACTION", classes="menu_header")
            yield Static("-" * 50, classes="separator")
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
        from datetime import datetime
        import jdatetime
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        date_input = self.query_one("#tx_date", Input)
        date_input.value = date_str
        
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
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, tx_id: int, on_save=None, **kwargs):
        self.tx_id = tx_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("EDIT TRANSACTION", classes="menu_header")
            yield Static("-" * 50, classes="separator")
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
        from datetime import datetime
        import jdatetime
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        date_str = jalali_now.strftime("%Y-%m-%d")
        date_input = self.query_one("#tx_date", Input)
        date_input.value = date_str
        
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


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class ReportsScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_summary", "Summary"),
        Binding("2", "do_category", "Category"),
        Binding("3", "do_monthly", "Monthly"),
        Binding("4", "do_bar_chart", "Bar Chart"),
        Binding("5", "do_pie_chart", "Pie Chart"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("REPORTS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Summary")),
                ListItem(Label("2. Category Report")),
                ListItem(Label("3. Monthly Report")),
                ListItem(Label("4. Bar Chart (Categories)")),
                ListItem(Label("5. Pie Chart (Categories)")),
                ListItem(Label("6. Back to Main Menu")),
                id="rep_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-6] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_do_summary()
        elif idx == 1:
            self.action_do_category()
        elif idx == 2:
            self.action_do_monthly()
        elif idx == 3:
            self.action_do_bar_chart()
        elif idx == 4:
            self.action_do_pie_chart()
        elif idx == 5:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_summary(self):
        self.app.push_screen(SummaryScreen())

    def action_do_category(self):
        self.app.push_screen(CategoryReportScreen())

    def action_do_monthly(self):
        self.app.push_screen(MonthlyReportScreen())

    def action_do_bar_chart(self):
        self.app.push_screen(BarChartScreen())

    def action_do_pie_chart(self):
        self.app.push_screen(PieChartScreen())


class SummaryScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("FINANCIAL SUMMARY", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="sum_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#sum_table", DataTable)
        table.add_columns("Item", "Value")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#sum_table", DataTable)
        table.clear()
        resp = api_get("/transactions/summary", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        table.add_row("Total Income", format_toman(data.get("total_income", 0)))
        table.add_row("Total Cost", format_toman(data.get("total_cost", 0)))
        table.add_row("Balance", format_toman(data.get("balance", 0)))

    def action_go_back(self):
        self.app.pop_screen()


class CategoryReportScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("CATEGORY REPORT", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="rep_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#rep_table", DataTable)
        table.add_columns("Category", "Type", "Total")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#rep_table", DataTable)
        table.clear()
        resp = api_get("/transactions/report/category", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        if not data:
            table.add_row("-", "-", "No data")
        else:
            for r in data:
                table.add_row(
                    r.get("category_name", ""),
                    r.get("category_type", ""),
                    format_toman(r.get("total", 0)),
                )

    def action_go_back(self):
        self.app.pop_screen()


class MonthlyReportScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("MONTHLY REPORT", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="mon_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#mon_table", DataTable)
        table.add_columns("Month", "Income", "Cost", "Balance")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#mon_table", DataTable)
        table.clear()
        resp = api_get("/transactions/report/monthly", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        if not data:
            table.add_row("-", "-", "-", "No data")
        else:
            for r in data:
                income = r.get("total_income", 0)
                cost = r.get("total_cost", 0)
                table.add_row(
                    r.get("month", ""),
                    format_toman(income),
                    format_toman(cost),
                    format_toman(income - cost),
                )

    def action_go_back(self):
        self.app.pop_screen()


class BarChartScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("CATEGORY BAR CHART", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            yield Static(id="chart_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_chart()

    def _ascii_bar(self, data):
        if not data:
            return "No data"
        labels = [r["category_name"] for r in data]
        values = [r["total"] for r in data]
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1
        max_label = max(len(l) for l in labels) if labels else 1
        lines = []
        lines.append(f"{'Category':<{max_label}} | {'Amount':>20} | Chart")
        lines.append("-" * (max_label + 38))
        for label, val, row in zip(labels, values, data):
            bar_len = int((val / max_val) * 30)
            color = "green" if row["category_type"] == "income" else "red"
            bar = "█" * bar_len
            lines.append(f"{label:<{max_label}} | {format_toman(val):>20} | [{color}]{bar}[/{color}]")
        lines.append("-" * (max_label + 38))
        return "\n".join(lines)

    def load_chart(self):
        resp = api_get("/transactions/report/category-chart", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        content = self.query_one("#chart_content", Static)
        if err:
            content.update(f"Error: {err}")
            return
        if not data:
            content.update("No data available for chart.")
            return
        chart_str = self._ascii_bar(data)
        content.update(chart_str)

    def action_go_back(self):
        self.app.pop_screen()


class PieChartScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("CATEGORY PIE CHART", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            yield Static(id="chart_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_chart()

    def _ascii_pie(self, labels, values):
        total = sum(values)
        if total == 0:
            return "No data"
        items = list(zip(labels, values))
        # Palette of block characters for slices
        blocks = ["\u2588", "\u2593", "\u2592", "\u2591", "\u25A0", "\u25A1", "\u25AA", "\u25AB"]
        # Build a 2D grid for the circle
        size = 21
        radius = size // 2
        cx, cy = radius, radius
        grid = [[" " for _ in range(size)] for _ in range(size)]
        # Fill circle with slices based on angle
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                dist = (dx * dx + dy * dy) ** 0.5
                if dist <= radius:
                    angle = math.atan2(dy, dx)
                    if angle < 0:
                        angle += 2 * math.pi
                    # Determine which slice this angle belongs to
                    cumulative = 0.0
                    for idx, (_, val) in enumerate(items):
                        slice_angle = (val / total) * 2 * math.pi
                        if cumulative <= angle < cumulative + slice_angle:
                            grid[y][x] = blocks[idx % len(blocks)]
                            break
                        cumulative += slice_angle
        # Build legend lines
        lines = []
        lines.append(" " * 8 + "CATEGORY PIE CHART")
        lines.append("")
        for i, (label, val) in enumerate(items):
            pct = (val / total) * 100
            block = blocks[i % len(blocks)]
            lines.append(f"  {block} {label:<18} {val:>10,.0f}  ({pct:5.1f}%)")
        lines.append("")
        # Add the circle grid to the right of the legend
        legend_width = max(len(l) for l in lines) if lines else 0
        # Combine: put circle on the right side
        circle_lines = ["".join(row) for row in grid]
        combined = []
        max_left = len(lines)
        max_right = len(circle_lines)
        for i in range(max(max_left, max_right)):
            left = lines[i] if i < max_left else ""
            right = circle_lines[i] if i < max_right else ""
            combined.append(left.ljust(legend_width + 2) + right)
        return "\n".join(combined)

    def load_chart(self):
        import math
        resp = api_get("/transactions/report/category-chart", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        content = self.query_one("#chart_content", Static)
        if err:
            content.update(f"Error: {err}")
            return
        if not data:
            content.update("No data available for chart.")
            return

        labels = [r["category_name"] for r in data]
        values = [r["total"] for r in data]
        chart_str = self._ascii_pie(labels, values)
        content.update(chart_str)

    def action_go_back(self):
        self.app.pop_screen()


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class BudgetScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "go_tree", "Tree View"),
        Binding("2", "go_periods", "Periods"),
        Binding("3", "go_report", "Report"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("BUDGET MANAGEMENT", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. Budget Tree View")),
                ListItem(Label("2. Budget Periods")),
                ListItem(Label("3. Budget Report")),
                ListItem(Label("4. Back")),
                id="budget_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-3] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.app.push_screen(BudgetTreeScreen())
        elif idx == 1:
            self.app.push_screen(BudgetPeriodListScreen())
        elif idx == 2:
            self.app.push_screen(BudgetReportScreen())
        elif idx == 3:
            self.action_go_back()

    def action_go_tree(self):
        self.app.push_screen(BudgetTreeScreen())

    def action_go_periods(self):
        self.app.push_screen(BudgetPeriodListScreen())

    def action_go_report(self):
        self.app.push_screen(BudgetReportScreen())

    def action_go_back(self):
        self.app.pop_screen()




class BudgetTreeScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select_item", "Select"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="wide_panel"):
            yield Label("BUDGET TREE VIEW", classes="detail_header")
            yield Rule()
            with VerticalScroll(id="tree_scroll"):
                yield Static("", id="tree_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select Period/Item  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        yield Footer()

    def on_mount(self):
        self.load_tree()

    def load_tree(self):
        status = self.query_one("#status", StatusBar)
        tree_content = self.query_one("#tree_content", Static)
        
        # Fetch all budget periods
        resp = api_get("/budget/periods", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        
        if err:
            status.update(f"Error: {err}")
            tree_content.update(f"Error loading budget data: {err}")
            return
        
        if not data:
            status.update("No budget periods found")
            tree_content.update("No budget periods found. Create a period first.")
            return
        
        # Build tree structure
        tree_lines = []
        tree_lines.append("BUDGET PERIODS AND ITEMS")
        tree_lines.append("=" * 60)
        tree_lines.append("")
        
        for i, period in enumerate(data):
            is_last_period = (i == len(data) - 1)
            period_prefix = "└── " if is_last_period else "├── "
            
            month_name = get_persian_month_name(period["month"])
            tree_lines.append(f"{period_prefix}📅 {period['year']}/{period['month']} ({month_name})")
            
            # Fetch items for this period
            items_resp = api_get(f"/budget/periods/{period['id']}/items", username=self.app.user.get("username"))
            items_data, _ = handle_response(items_resp)
            
            if items_data:
                for j, item in enumerate(items_data):
                    is_last_item = (j == len(items_data) - 1)
                    
                    if is_last_period:
                        item_prefix = "    └── " if is_last_item else "    ├── "
                    else:
                        item_prefix = "│   └── " if is_last_item else "│   ├── "
                    
                    planned = format_toman(item["planned_amount"])
                    tree_lines.append(f"{item_prefix}💰 {item['category_name']}: {planned}")
                    
                    # Add notes if present
                    if item.get("notes"):
                        if is_last_period:
                            note_prefix = "        " if is_last_item else "    │   "
                        else:
                            note_prefix = "│       " if is_last_item else "│   │   "
                        tree_lines.append(f"{note_prefix}📝 {item['notes']}")
            else:
                if is_last_period:
                    tree_lines.append("    └── (No items)")
                else:
                    tree_lines.append("│   └── (No items)")
            
            tree_lines.append("")
        
        tree_content.update("\n".join(tree_lines))
        status.update(f"Loaded {len(data)} period(s). Press [R] to refresh")

    def action_refresh(self):
        self.load_tree()

    def action_select_item(self):
        # For now, just refresh. Could be enhanced to navigate to specific period/item
        self.action_refresh()

    def action_go_back(self):
        self.app.pop_screen()


class BudgetPeriodListScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_period", "Add"),
        Binding("e", "edit_period", "Edit"),
        Binding("d", "delete_period", "Delete"),
        Binding("i", "manage_items", "Items"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="wide_panel"):
            yield Label("BUDGET PERIODS", classes="detail_header")
            yield Rule()
            yield DataTable(id="periods_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [A] Add  [E] Edit  [D] Delete  [I] Items  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#periods_table", DataTable)
        table.add_columns("ID", "Year", "Month", "Items")
        table.cursor_type = "row"
        self.load_periods()

    def load_periods(self):
        table = self.query_one("#periods_table", DataTable)
        table.clear()
        resp = api_get("/budget/periods", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        if not data:
            status.update("No budget periods found. Press [A] to add one.")
            return
        for period in data:
            # Count items for this period
            items_resp = api_get(f"/budget/periods/{period['id']}/items", username=self.app.user.get("username"))
            items_data, _ = handle_response(items_resp)
            item_count = len(items_data) if items_data else 0
            month_name = get_persian_month_name(period["month"])
            table.add_row(
                str(period["id"]),
                str(period["year"]),
                f"{period['month']} - {month_name}",
                str(item_count),
                key=str(period["id"]),
            )
            # Store the actual month number in the row for later retrieval
            if not hasattr(table, '_month_map'):
                table._month_map = {}
            table._month_map[str(period["id"])] = period["month"]
        status.update(f"Loaded {len(data)} period(s). [A] Add  [E] Edit  [D] Delete  [I] Items")

    def action_add_period(self):
        # self.app.push_screen(BudgetPeriodAddScreen(), lambda _: self.load_periods())
        # self.app.push_screen(BudgetPeriodAddScreen(), callback=lambda result: self.load_periods())
        self.app.push_screen(BudgetPeriodAddScreen(), self.after_add)

    def after_add(self, result):
        self.load_periods()


    def action_edit_period(self):
        table = self.query_one("#periods_table", DataTable)
        if table.row_count == 0:
            self.app.push_screen(MessageBox("No periods to edit.", "Info"))
            return
        row_key = table.get_row_at(table.cursor_row)
        period_id = int(row_key[0])
        self.app.push_screen(BudgetPeriodEditScreen(period_id), lambda _: self.load_periods())

    def action_delete_period(self):
        table = self.query_one("#periods_table", DataTable)
        if table.row_count == 0:
            self.app.push_screen(MessageBox("No periods to delete.", "Info"))
            return
        row_key = table.get_row_at(table.cursor_row)
        period_id = int(row_key[0])

        def on_confirm(confirmed: bool):
            if confirmed:
                self._do_delete(period_id)

        self.app.push_screen(
            ConfirmBox("Delete this budget period and all its items?", "Confirm Delete"),
            on_confirm,
        )

    def _do_delete(self, period_id):
        resp = api_delete(f"/budget/periods/{period_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.load_periods()

    def action_manage_items(self):
        table = self.query_one("#periods_table", DataTable)
        if table.row_count == 0:
            self.app.push_screen(MessageBox("No periods available. Add a period first.", "Info"))
            return
        row_key = table.get_row_at(table.cursor_row)
        period_id = int(row_key[0])
        year = int(row_key[1])
        # Get month from the stored map or extract from display string
        if hasattr(table, '_month_map'):
            month = table._month_map.get(str(period_id))
        else:
            # Fallback: extract from display string "2 - Ordibehesht"
            month_str = row_key[2].split(' - ')[0]
            month = int(month_str)
        self.app.push_screen(BudgetItemListScreen(period_id, year, month))

    def action_go_back(self):
        self.app.pop_screen()


class BudgetPeriodAddScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("ADD BUDGET PERIOD", classes="detail_header")
            yield Rule()
            yield Label("Year (Jalali):")
            yield Input(placeholder="e.g., 1403", id="year_input")
            yield Label("Month:")
            yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Fill in the fields and press Save", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self.action_save()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def action_save(self):
        year_input = self.query_one("#year_input", Input)
        month_select = self.query_one("#month_select", Select)
        status = self.query_one("#status", StatusBar)

        year = year_input.value.strip()

        if not year:
            status.update("Error: Year is required")
            return

        if month_select.value == Select.BLANK:
            status.update("Error: Please select a month")
            return

        try:
            year_int = int(year)
            month_int = month_select.value
        except ValueError:
            status.update("Error: Year must be a valid number")
            return

        payload = {"year": year_int, "month": month_int}
        resp = api_post("/budget/periods", payload, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            status.update(f"Error: {err}")
        else:
            self.dismiss(True)

    def action_go_back(self):
        self.app.pop_screen()


class BudgetPeriodEditScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, period_id, **kwargs):
        super().__init__(**kwargs)
        self.period_id = period_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("EDIT BUDGET PERIOD", classes="detail_header")
            yield Rule()
            yield Label("Year (Jalali):")
            yield Input(placeholder="e.g., 1403", id="year_input")
            yield Label("Month:")
            yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading...", id="status")
        yield Footer()

    def on_mount(self):
        self.load_period()

    def load_period(self):
        resp = api_get(f"/budget/periods/{self.period_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        year_input = self.query_one("#year_input", Input)
        month_select = self.query_one("#month_select", Select)
        year_input.value = str(data["year"])
        month_select.value = data["month"]
        status.update("Edit the fields and press Save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self.action_save()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def action_save(self):
        year_input = self.query_one("#year_input", Input)
        month_select = self.query_one("#month_select", Select)
        status = self.query_one("#status", StatusBar)

        year = year_input.value.strip()

        if not year:
            status.update("Error: Year is required")
            return

        if month_select.value == Select.BLANK:
            status.update("Error: Please select a month")
            return

        try:
            year_int = int(year)
            month_int = month_select.value
        except ValueError:
            status.update("Error: Year must be a valid number")
            return

        payload = {"year": year_int, "month": month_int}
        resp = api_put(f"/budget/periods/{self.period_id}", payload, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            status.update(f"Error: {err}")
        else:
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


class BudgetItemListScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_item", "Add"),
        Binding("e", "edit_item", "Edit"),
        Binding("d", "delete_item", "Delete"),
    ]

    def __init__(self, period_id, year, month, **kwargs):
        super().__init__(**kwargs)
        self.period_id = period_id
        self.year = year
        self.month = month

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="wide_panel"):
            month_name = get_persian_month_name(self.month)
            yield Label(f"BUDGET ITEMS - {self.year}/{self.month} ({month_name})", classes="detail_header")
            yield Rule()
            yield DataTable(id="items_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [A] Add  [E] Edit  [D] Delete  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#items_table", DataTable)
        table.add_columns("ID", "Category", "Planned Amount", "Notes")
        table.cursor_type = "row"
        self.load_items()

    def load_items(self):
        table = self.query_one("#items_table", DataTable)
        table.clear()
        resp = api_get(f"/budget/periods/{self.period_id}/items", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        if not data:
            status.update("No budget items found. Press [A] to add one.")
            return
        for item in data:
            table.add_row(
                str(item["id"]),
                item["category_name"],
                format_toman(item["planned_amount"]),
                item.get("notes", "") or "",
                key=str(item["id"]),
            )
        status.update(f"Loaded {len(data)} item(s). [A] Add  [E] Edit  [D] Delete")

    def action_add_item(self):
        self.app.push_screen(BudgetItemAddScreen(self.period_id), lambda _: self.load_items())

    def action_edit_item(self):
        table = self.query_one("#items_table", DataTable)
        if table.row_count == 0:
            self.app.push_screen(MessageBox("No items to edit.", "Info"))
            return
        row_key = table.get_row_at(table.cursor_row)
        item_id = int(row_key[0])
        self.app.push_screen(BudgetItemEditScreen(item_id), lambda _: self.load_items())

    def action_delete_item(self):
        table = self.query_one("#items_table", DataTable)
        if table.row_count == 0:
            self.app.push_screen(MessageBox("No items to delete.", "Info"))
            return
        row_key = table.get_row_at(table.cursor_row)
        item_id = int(row_key[0])

        def on_confirm(confirmed: bool):
            if confirmed:
                self._do_delete(item_id)

        self.app.push_screen(
            ConfirmBox("Delete this budget item?", "Confirm Delete"),
            on_confirm,
        )

    def _do_delete(self, item_id):
        resp = api_delete(f"/budget/items/{item_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.load_items()

    def action_go_back(self):
        self.app.pop_screen()


class BudgetItemAddScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, period_id, **kwargs):
        super().__init__(**kwargs)
        self.period_id = period_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("ADD BUDGET ITEM", classes="detail_header")
            yield Rule()
            yield Label("Category:")
            yield Select([("Loading...", None)], id="category_select", allow_blank=False)
            yield Label("Planned Amount (Toman):")
            yield Input(placeholder="e.g., 1000000", id="amount_input")
            yield Label("Notes (optional):")
            yield Input(placeholder="Optional notes", id="notes_input")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading categories...", id="status")
        yield Footer()

    def on_mount(self):
        self.load_categories()

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        if not data:
            status.update("No categories found. Please add categories first.")
            return
        cat_select = self.query_one("#category_select", Select)
        options = [(cat["name"], cat["id"]) for cat in data]
        cat_select.set_options(options)
        status.update("Fill in the fields and press Save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self.action_save()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def action_save(self):
        cat_select = self.query_one("#category_select", Select)
        amount_input = self.query_one("#amount_input", Input)
        notes_input = self.query_one("#notes_input", Input)
        status = self.query_one("#status", StatusBar)

        if cat_select.value == Select.BLANK:
            status.update("Error: Please select a category")
            return

        amount = amount_input.value.strip()
        if not amount:
            status.update("Error: Amount is required")
            return

        try:
            amount_float = float(amount)
        except ValueError:
            status.update("Error: Amount must be a valid number")
            return

        payload = {
            "budget_period_id": self.period_id,
            "category_id": cat_select.value,
            "planned_amount": amount_float,
            "notes": notes_input.value.strip() or None,
        }
        resp = api_post("/budget/items", payload, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            status.update(f"Error: {err}")
        else:
            self.dismiss(True)

    def action_go_back(self):
        self.app.pop_screen()


class BudgetItemEditScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, item_id, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("EDIT BUDGET ITEM", classes="detail_header")
            yield Rule()
            yield Label("Category:")
            yield Select([("Loading...", None)], id="category_select", allow_blank=False)
            yield Label("Planned Amount (Toman):")
            yield Input(placeholder="e.g., 1000000", id="amount_input")
            yield Label("Notes (optional):")
            yield Input(placeholder="Optional notes", id="notes_input")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading...", id="status")
        yield Footer()

    def on_mount(self):
        self.load_categories()

    def load_categories(self):
        resp = api_get("/categories", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        if not data:
            status.update("No categories found.")
            return
        cat_select = self.query_one("#category_select", Select)
        options = [(cat["name"], cat["id"]) for cat in data]
        cat_select.set_options(options)
        self.load_item()

    def load_item(self):
        resp = api_get(f"/budget/items/{self.item_id}", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        status = self.query_one("#status", StatusBar)
        if err:
            status.update(f"Error: {err}")
            return
        cat_select = self.query_one("#category_select", Select)
        amount_input = self.query_one("#amount_input", Input)
        notes_input = self.query_one("#notes_input", Input)
        cat_select.value = data["category_id"]
        amount_input.value = str(data["planned_amount"])
        notes_input.value = data.get("notes", "") or ""
        status.update("Edit the fields and press Save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self.action_save()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def action_save(self):
        cat_select = self.query_one("#category_select", Select)
        amount_input = self.query_one("#amount_input", Input)
        notes_input = self.query_one("#notes_input", Input)
        status = self.query_one("#status", StatusBar)

        if cat_select.value == Select.BLANK:
            status.update("Error: Please select a category")
            return

        amount = amount_input.value.strip()
        if not amount:
            status.update("Error: Amount is required")
            return

        try:
            amount_float = float(amount)
        except ValueError:
            status.update("Error: Amount must be a valid number")
            return

        payload = {
            "category_id": cat_select.value,
            "planned_amount": amount_float,
            "notes": notes_input.value.strip() or None,
        }
        resp = api_put(f"/budget/items/{self.item_id}", payload, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            status.update(f"Error: {err}")
        else:
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


class BudgetReportScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="wide_panel"):
            yield Label("BUDGET REPORT", classes="detail_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Label("Year:")
                yield Input(placeholder="1403", id="year_input", classes="filter_input")
                yield Label("Month:")
                yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
                yield Button("Load Report", variant="primary", id="load_btn")
            yield DataTable(id="report_table")
            yield Static("", id="summary_text")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Navigate  [Enter] Load  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("Enter year and month, then press Load Report", id="status")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#report_table", DataTable)
        table.add_columns("Category", "Planned", "Spent", "Remaining", "Status")
        table.cursor_type = "row"
        # Pre-fill with current Jalali date
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        year_input = self.query_one("#year_input", Input)
        month_select = self.query_one("#month_select", Select)
        year_input.value = str(jalali_now.year)
        month_select.value = jalali_now.month

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load_btn":
            self.action_load_report()

    def action_load_report(self):
        year_input = self.query_one("#year_input", Input)
        month_select = self.query_one("#month_select", Select)
        status = self.query_one("#status", StatusBar)

        year = year_input.value.strip()
        month = month_select.value

        if not year:
            status.update("Error: Year is required")
            return

        if month_select.value == Select.BLANK:
            status.update("Error: Please select a month")
            return

        try:
            year_int = int(year)
            month_int = month_select.value
        except ValueError:
            status.update("Error: Year must be a valid number")
            return

        params = {"year": year_int, "month": month_int}
        resp = api_get("/budget/report", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            status.update(f"Error: {err}")
            return

        table = self.query_one("#report_table", DataTable)
        table.clear()

        categories = data.get("categories", [])
        if not categories:
            status.update("No budget data found for this period.")
            return

        for cat in categories:
            remaining = cat["remaining_amount"]
            if remaining >= 0:
                status_text = "✓ OK"
            else:
                status_text = "✗ Over"
            table.add_row(
                cat["category_name"],
                format_toman(cat["planned_amount"]),
                format_toman(cat["total_spent"]),
                format_toman(remaining),
                status_text,
            )

        summary = self.query_one("#summary_text", Static)
        total_planned = data.get("total_planned", 0)
        total_spent = data.get("total_spent", 0)
        total_remaining = data.get("total_remaining", 0)
        summary_text = f"\nTOTAL: Planned={format_toman(total_planned)}  Spent={format_toman(total_spent)}  Remaining={format_toman(total_remaining)}"
        summary.update(summary_text)
        status.update(f"Report loaded for {year}/{month}")

    def action_refresh(self):
        self.action_load_report()

    def action_go_back(self):
        self.app.pop_screen()



# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("SETTINGS", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. Reset All Data")),
                ListItem(Label("2. Back")),
                id="settings_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_reset_data()
        elif idx == 1:
            self.action_go_back()

    def action_reset_data(self):
        def on_confirm(confirmed: bool):
            if confirmed:
                self._do_reset()
        self.app.push_screen(
            ConfirmBox(
                "This will permanently delete ALL your categories, sources, and transactions.\nThis action cannot be undone.",
                "Reset All Data?",
            ),
            on_confirm,
        )

    def _do_reset(self):
        resp = api_post("/settings/reset", {}, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("All data has been reset successfully.", "Success"))

    def action_go_back(self):
        self.app.pop_screen()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class AccountingApp(App):
    CSS = """
    Screen {
        align: center middle;
        background: $surface-darken-1;
    }

    .main_panel {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }

    .wide_panel {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    #tree_scroll {
        height: 1fr;
        border: solid $primary;
    }

    #tree_content {
        width: 100%;
        padding: 1;
    }

    .main_title {
        text-align: center;
        color: $primary-lighten-2;
        text-style: bold;
    }

    .menu_header {
        text-align: center;
        color: $primary;
        text-style: bold;
    }

    .detail_header {
        text-align: center;
        color: $primary-lighten-1;
        text-style: bold;
    }

    .separator {
        text-align: center;
        color: $primary-darken-2;
    }

    .split_row {
        width: 100%;
        height: auto;
    }

    .left_pane {
        width: 65%;
        height: auto;
    }

    .right_pane {
        width: 35%;
        height: auto;
        border: solid $primary-darken-2;
        padding: 1;
        background: $surface-darken-1;
    }

    ListView {
        width: 100%;
        height: auto;
        border: none;
        background: transparent;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:focus {
        background: $primary;
        color: $text;
    }

    DataTable {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-1;
    }

    Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    .button_row {
        width: 100%;
        height: auto;
        align: left middle;
    }

    .filter_row {
        width: 100%;
        height: auto;
        align: left middle;
        margin: 0 0 1 0;
    }

    .filter_row Input {
        width: 15;
        margin: 0 1 0 0;
    }

    .filter_row Select {
        width: 25;
        margin: 0 1 0 0;
    }

    .filter_row Button {
        margin: 0 1 0 0;
    }

    Button {
        margin: 0 1 0 0;
    }

    .bottom_bar {
        dock: bottom;
        height: 2;
        width: 100%;
    }

    HelpTip {
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        content-align: center middle;
    }

    StatusBar {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        content-align: center middle;
    }

    .dialog {
        width: 40;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    .dialog_title {
        text-align: center;
        color: $primary-lighten-2;
        text-style: bold;
    }

    .dialog_message {
        text-align: center;
        margin: 1 0;
    }

    .error_title {
        color: $error;
    }

    .error_message {
        color: $error;
        text-style: bold;
    }

    .dialog_buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    """

    def on_mount(self):
        self.push_screen(LoginScreen())

    def action_quit(self):
        def on_confirm(confirmed: bool):
            if confirmed:
                self.exit()
        self.push_screen(ConfirmBox("Are you sure you want to exit?", "Exit Confirmation"), on_confirm)


def main():
    app = AccountingApp()
    app.run()


if __name__ == "__main__":
    main()
