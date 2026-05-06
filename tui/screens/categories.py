"""Category management screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, 
    ListItem, ListView, Select, Static, Rule
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class CategoriesScreen(Screen):
    """Categories menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_list", "List"),
        Binding("2", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("CATEGORIES", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. List Categories")),
                ListItem(Label("2. Add Category")),
                ListItem(Label("3. Back to Main Menu")),
                id="cat_menu_list",
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
        self.app.push_screen(CategoryListScreen())

    def action_do_add(self):
        self.app.push_screen(CategoryAddScreen())


class CategoryListScreen(Screen):
    """Category list with filtering."""
    
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
            yield Label("CATEGORY LIST", classes="menu_header")
            yield Rule()
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
                    yield Rule()
                    yield Static(id="cat_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [E] Edit  [D] Delete  [F] Filter  [R] Reset  [Esc] Back", id="help")
            yield StatusBar("E=Edit  D=Delete  F=Filter  R=Reset  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#cat_table", DataTable)
        table.add_columns("ID", "Name", "Type")
        table.cursor_type = "row"
        table.zebra_stripes = True
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
            rows = [(str(c["id"]), c["name"], c["type"]) for c in self._data]
            table.add_rows(rows)
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
    """Add new category screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("ADD CATEGORY", classes="menu_header")
            yield Rule()
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
            self.dismiss(True)
            self.notify("Category created successfully")
            self.query_one("#cat_name", Input).value = ""


class CategoryEditScreen(Screen):
    """Edit category screen."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, cat_id: int, on_save=None, **kwargs):
        self.cat_id = cat_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("EDIT CATEGORY", classes="menu_header")
            yield Rule()
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
        if not getattr(self, "_sidebar_embedded", False):
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
        
        resp = api_put(
            f"/categories/{self.cat_id}",
            {"name": name, "type": str(cat_type)},
            username=self.app.user.get("username")
        )
        _, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.app.pop_screen()
