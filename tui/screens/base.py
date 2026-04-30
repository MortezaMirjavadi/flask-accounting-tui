"""Base classes with common functionality for screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Rule, Select, Static

from tui.api import api_get, api_delete, handle_response
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
