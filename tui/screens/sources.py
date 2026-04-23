"""Source management screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Static, Rule
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class SourcesScreen(Screen):
    """Sources menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("SOURCES", classes="menu_header")
            yield Rule()
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
    """Source list with filtering."""
    
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
        table.zebra_stripes = True
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
            table.add_row("-", "No sources found", "-")
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
    """Add new source screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("ADD SOURCE", classes="menu_header")
            yield Rule()
            yield Label("Name:")
            yield Input(placeholder="Source name (e.g. Bank, Cash)", id="src_name")
            yield Label("Amount:")
            yield Input(placeholder="Source amount", id="src_amount")
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
        
        payload = {"name": name, "amount": amount}
        resp = api_post("/sources", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Source added successfully.", "Success"))
            self.query_one("#src_name", Input).value = ""
            self.query_one("#src_amount", Input).value = ""


class SourceEditScreen(Screen):
    """Edit source screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, src_id: int, on_save=None, **kwargs):
        self.src_id = src_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("EDIT SOURCE", classes="menu_header")
            yield Rule()
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
        
        payload = {"name": name, "amount": amount}
        resp = api_put(f"/sources/{self.src_id}", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()
