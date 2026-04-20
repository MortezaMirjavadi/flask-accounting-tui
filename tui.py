import math
import sys

import requests
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
)

BASE_URL = "http://127.0.0.1:5000"

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path, params=None):
    try:
        return requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
    except requests.RequestException:
        return None


def api_post(path, payload):
    try:
        return requests.post(f"{BASE_URL}{path}", json=payload, timeout=10)
    except requests.RequestException:
        return None


def api_put(path, payload):
    try:
        return requests.put(f"{BASE_URL}{path}", json=payload, timeout=10)
    except requests.RequestException:
        return None


def api_delete(path):
    try:
        return requests.delete(f"{BASE_URL}{path}", timeout=10)
    except requests.RequestException:
        return None


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
    def __init__(self, text="Ready", **kwargs):
        super().__init__(text, **kwargs)


class HelpTip(Static):
    def __init__(self, text="", **kwargs):
        super().__init__(text, **kwargs)


class MessageBox(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    def __init__(self, message, title="Message", **kwargs):
        self.message_text = message
        self.title_text = title
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Container(classes="dialog"):
            yield Label(self.title_text, classes="dialog_title")
            yield Static(self.message_text, classes="dialog_message")
            yield Button("OK", variant="primary", id="ok")

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
# Main menu
# ---------------------------------------------------------------------------

class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Exit"),
        Binding("1", "go_categories", "Categories"),
        Binding("2", "go_sources", "Sources"),
        Binding("3", "go_transactions", "Transactions"),
        Binding("4", "go_reports", "Reports"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("TERMINAL ACCOUNTING SYSTEM", classes="main_title")
            yield Static("=" * 50, classes="separator")
            yield Label("Main Menu", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Categories")),
                ListItem(Label("2. Sources")),
                ListItem(Label("3. Transactions")),
                ListItem(Label("4. Reports")),
                ListItem(Label("5. Exit")),
                id="main_menu_list",
            )
        yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-4] Quick select  [Q] Exit", id="help")
        yield StatusBar("Enter=Select  Esc=Back  Q=Quit", id="status")
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
            self.app.exit()

    def action_go_categories(self):
        self.app.push_screen(CategoriesScreen())

    def action_go_sources(self):
        self.app.push_screen(SourcesScreen())

    def action_go_transactions(self):
        self.app.push_screen(TransactionsScreen())

    def action_go_reports(self):
        self.app.push_screen(ReportsScreen())


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
        yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-2] Quick select  [Esc] Back", id="help")
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
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("CATEGORY LIST", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="cat_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Static("-" * 25, classes="separator")
                    yield Static(id="cat_detail")
        yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [Esc] Back", id="help")
        yield StatusBar("E=Edit  D=Delete  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#cat_table", DataTable)
        table.add_columns("ID", "Name", "Type")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#cat_table", DataTable)
        table.clear()
        resp = api_get("/categories")
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
            resp = api_delete(f"/categories/{cat_id}")
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
        resp = api_post("/categories", {"name": name, "type": str(cat_type)})
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
        yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
        yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/categories/{self.cat_id}")
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
        resp = api_put(f"/categories/{self.cat_id}", {"name": name, "type": str(cat_type)})
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
        yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-2] Quick select  [Esc] Back", id="help")
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
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("SOURCE LIST", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="src_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Static("-" * 25, classes="separator")
                    yield Static(id="src_detail")
        yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [Esc] Back", id="help")
        yield StatusBar("E=Edit  D=Delete  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#src_table", DataTable)
        table.add_columns("ID", "Name", "Amount")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#src_table", DataTable)
        table.clear()
        resp = api_get("/sources")
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No sources found")
        else:
            for s in self._data:
                table.add_row(str(s["id"]), s["name"], f"{s['amount']:,.2f}")
        self.update_detail()

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
        bal_resp = api_get(f"/sources/{src_id}/balance")
        bal_data, bal_err = handle_response(bal_resp)
        if bal_err or bal_data is None:
            bal_info = "Balance: N/A"
        else:
            bal = bal_data.get("balance", 0)
            bal_info = f"Balance: {bal:,.2f}"
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
            resp = api_delete(f"/sources/{src_id}")
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
        resp = api_post("/sources", payload)
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
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
        yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        resp = api_get(f"/sources/{self.src_id}")
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
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        resp = api_put(f"/sources/{self.src_id}", {"name": name})
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
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("TRANSACTION LIST", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="tx_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Static("-" * 25, classes="separator")
                    yield Static(id="tx_detail")
        yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [Esc] Back", id="help")
        yield StatusBar("E=Edit  D=Delete  Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tx_table", DataTable)
        table.add_columns("ID", "Date", "Amount", "Category", "Source", "Description")
        table.cursor_type = "row"
        self.load_data()

    def load_data(self):
        table = self.query_one("#tx_table", DataTable)
        table.clear()
        resp = api_get("/transactions")
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
                    str(t.get("amount", "")),
                    t.get("category_name", "N/A"),
                    t.get("source_name") or "-",
                    (t.get("description") or "")[:25],
                )
        self.update_detail()

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
            f"[b]Amount:[/b]      {tx.get('amount', 0):,.2f}\n"
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
            resp = api_delete(f"/transactions/{tx_id}")
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
            yield Static("-" * 70, classes="separator")
            yield Static(id="accordion_content")
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
        resp = api_get("/categories")
        cats, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._categories = cats or []

        resp = api_get("/transactions")
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

            lines.append(f"{marker} {arrow} [{color}]{cat_name}[/{color}] ({cat_type})  {len(cat_txs)} txs  Total: {total:,.2f}")

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
                            f"   {tx_marker}  {t.get('date','')}  {t.get('amount',0):>12,.2f}  "
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
            resp = api_delete(f"/transactions/{tx_id}")
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
        yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
        yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_categories()
        self.load_sources()

    def load_categories(self):
        resp = api_get("/categories")
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
        resp = api_get("/sources")
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
        resp = api_post("/transactions", payload)
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
        yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
        yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_categories()
        self.load_sources()
        resp = api_get(f"/transactions/{self.tx_id}")
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
        resp = api_get("/categories")
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
        resp = api_get("/sources")
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
        resp = api_put(f"/transactions/{self.tx_id}", payload)
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
        yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-5] Quick select  [Esc] Back", id="help")
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
        resp = api_get("/transactions/summary")
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        table.add_row("Total Income", f"{data.get('total_income', 0):,.2f}")
        table.add_row("Total Cost", f"{data.get('total_cost', 0):,.2f}")
        table.add_row("Balance", f"{data.get('balance', 0):,.2f}")

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
        resp = api_get("/transactions/report/category")
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
                    f"{r.get('total', 0):,.2f}",
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
        resp = api_get("/transactions/report/monthly")
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
                    f"{income:,.2f}",
                    f"{cost:,.2f}",
                    f"{income - cost:,.2f}",
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
        lines.append(f"{'Category':<{max_label}} | {'Amount':>12} | Chart")
        lines.append("-" * (max_label + 30))
        for label, val, row in zip(labels, values, data):
            bar_len = int((val / max_val) * 30)
            color = "green" if row["category_type"] == "income" else "red"
            bar = "█" * bar_len
            lines.append(f"{label:<{max_label}} | {val:>12,.0f} | [{color}]{bar}[/{color}]")
        lines.append("-" * (max_label + 30))
        return "\n".join(lines)

    def load_chart(self):
        resp = api_get("/transactions/report/category-chart")
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
        resp = api_get("/transactions/report/category-chart")
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
        width: 90;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
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
        height: auto;
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

    Button {
        margin: 0 1 0 0;
    }

    HelpTip {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        content-align: center middle;
    }

    StatusBar {
        dock: bottom;
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

    .dialog_buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    """

    def on_mount(self):
        self.push_screen(MainMenuScreen())


def main():
    app = AccountingApp()
    app.run()


if __name__ == "__main__":
    main()
