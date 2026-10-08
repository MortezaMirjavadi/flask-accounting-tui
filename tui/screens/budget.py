"""Budget management screens."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Rule, Select, Static
)

from tui.api import api_get, api_post, api_put, api_delete, extract_items, handle_response, format_toman
from tui.config import PERSIAN_MONTHS, get_persian_month_name
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class BudgetScreen(Screen):
    """Budget management menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "go_tree", "Tree View"),
        Binding("2", "go_periods", "Periods"),
        Binding("3", "go_report", "Report"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
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
        if not getattr(self, "_sidebar_embedded", False):
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
    """Budget tree view with optimized single API call."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select_item", "Select"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="wide_panel center_screen"):
            yield Label("BUDGET TREE VIEW", classes="detail_header")
            yield Rule()
            with VerticalScroll(id="tree_scroll"):
                yield Static("", id="tree_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select Period/Item  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self):
        self.load_tree()

    def load_tree(self):
        status = self.query_one("#status", StatusBar)
        tree_content = self.query_one("#tree_content", Static)
        
        # Single API call for everything - no N+1 problem!
        resp = api_get("/budget/periods/with-items", username=self.app.user.get("username"))
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
            total = format_toman(period.get("total_planned", 0))
            item_count = period.get("item_count", 0)
            tree_lines.append(
                f"{period_prefix}📅 {period['year']}/{period['month']} ({month_name}) "
                f"[{item_count} items, {total}]"
            )
            
            items_data = period.get("items", [])
            
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
    """Budget period list management."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_period", "Add"),
        Binding("e", "edit_period", "Edit"),
        Binding("d", "delete_period", "Delete"),
        Binding("i", "manage_items", "Items"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="wide_panel center_screen"):
            yield Label("BUDGET PERIODS", classes="detail_header")
            yield Rule()
            yield DataTable(id="periods_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [A] Add  [E] Edit  [D] Delete  [I] Items  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self):
        table = self.query_one("#periods_table", DataTable)
        table.add_columns("ID", "Year", "Month", "Items")
        table.cursor_type = "row"
        table.zebra_stripes = True
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
        
        for period in extract_items(data):
            item_count = period.get("item_count", 0)
            month_name = get_persian_month_name(period["month"])
            table.add_row(
                str(period["id"]),
                str(period["year"]),
                f"{period['month']} - {month_name}",
                str(item_count),
                key=str(period["id"]),
            )
            # Store month mapping
            if not hasattr(table, '_month_map'):
                table._month_map = {}
            table._month_map[str(period["id"])] = period["month"]
        
        table.zebra_stripes = True
        status.update(f"Loaded {len(data)} period(s). [A] Add  [E] Edit  [D] Delete  [I] Items")

    def action_add_period(self):
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
    """Add new budget period."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("ADD BUDGET PERIOD", classes="detail_header")
            yield Rule()
            yield Label("Year (Jalali):")
            yield Input(placeholder="e.g., 1403", id="year_input")
            yield Label("Month:")
            yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save_btn")
                yield Button("✖ Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Fill in the fields and press Save", id="status")
        if not getattr(self, "_sidebar_embedded", False):
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
    """Edit budget period."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, period_id, **kwargs):
        super().__init__(**kwargs)
        self.period_id = period_id

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("EDIT BUDGET PERIOD", classes="detail_header")
            yield Rule()
            yield Label("Year (Jalali):")
            yield Input(placeholder="e.g., 1403", id="year_input")
            yield Label("Month:")
            yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save_btn")
                yield Button("✖ Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
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
    """Budget items for a specific period."""
    
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
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="wide_panel center_screen"):
            month_name = get_persian_month_name(self.month)
            yield Label(f"BUDGET ITEMS - {self.year}/{self.month} ({month_name})", classes="detail_header")
            yield Rule()
            yield DataTable(id="items_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [A] Add  [E] Edit  [D] Delete  [Esc] Back", id="help")
            yield StatusBar("Loading...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self):
        table = self.query_one("#items_table", DataTable)
        table.add_columns("ID", "Category", "Planned Amount", "Notes")
        table.cursor_type = "row"
        table.zebra_stripes = True
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
        for item in extract_items(data):
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
    """Add new budget item."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, period_id, **kwargs):
        super().__init__(**kwargs)
        self.period_id = period_id

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("ADD BUDGET ITEM", classes="detail_header")
            yield Rule()
            yield Label("Category:")
            yield Select([("Loading...", None)], id="category_select", allow_blank=False)
            yield Label("Planned Amount (Toman):")
            yield Input(placeholder="e.g., 1000000", id="amount_input")
            yield Label("Notes (optional):")
            yield Input(placeholder="Optional notes", id="notes_input")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save_btn")
                yield Button("✖ Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading categories...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
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
        options = [(cat["name"], cat["id"]) for cat in extract_items(data)]
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
    """Edit budget item."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, item_id, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("EDIT BUDGET ITEM", classes="detail_header")
            yield Rule()
            yield Label("Category:")
            yield Select([("Loading...", None)], id="category_select", allow_blank=False)
            yield Label("Planned Amount (Toman):")
            yield Input(placeholder="e.g., 1000000", id="amount_input")
            yield Label("Notes (optional):")
            yield Input(placeholder="Optional notes", id="notes_input")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save_btn")
                yield Button("✖ Cancel", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Loading...", id="status")
        if not getattr(self, "_sidebar_embedded", False):
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
        options = [(cat["name"], cat["id"]) for cat in extract_items(data)]
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
    """Budget vs actual spending report."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="wide_panel center_screen"):
            yield Label("BUDGET REPORT", classes="detail_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Label("Year:")
                yield Input(placeholder="1403", id="year_input", classes="filter_input")
                yield Label("Month:")
                yield Select(PERSIAN_MONTHS, id="month_select", allow_blank=False)
                yield Button("📊 Load Report", variant="primary", id="load_btn")
            yield DataTable(id="report_table")
            yield Static("", id="summary_text")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Navigate  [Enter] Load  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("Enter year and month, then press Load Report", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self):
        table = self.query_one("#report_table", DataTable)
        table.add_columns("Category", "Planned", "Spent", "Remaining", "Status")
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_cursor = True
        
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
        resp = api_get("/reports/budget", params=params, username=self.app.user.get("username"))
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
        summary_text = (
            f"\nTOTAL: Planned={format_toman(total_planned)}  "
            f"Spent={format_toman(total_spent)}  "
            f"Remaining={format_toman(total_remaining)}"
        )
        summary.update(summary_text)
        status.update(f"Report loaded for {year}/{month}")

    def action_refresh(self):
        self.action_load_report()

    def action_go_back(self):
        self.app.pop_screen()
