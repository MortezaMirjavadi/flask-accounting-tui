"""Shared reusable widgets used across multiple screens."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from tui.api import format_toman


class StatusBar(Static):
    """Status bar showing user info and current time."""
    
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
        """Update status with current user and time."""
        user = getattr(self.app, "user", None)
        username = user.get("username", "Guest") if user else "Guest"
        
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        shamsi_str = jalali_now.strftime("%Y-%m-%d %H:%M:%S")
        
        self.status_text = f"User: {username}  |  {shamsi_str}"


class HelpTip(Static):
    """Help text bar at bottom of screen."""
    
    def __init__(self, text="", **kwargs):
        super().__init__(text, **kwargs)


class MessageBox(ModalScreen):
    """Modal message dialog."""
    
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
            yield Label(
                self.title_text,
                classes="dialog_title error_title" if self.is_error else "dialog_title"
            )
            yield Static(
                self.message_text,
                classes="dialog_message error_message" if self.is_error else "dialog_message"
            )
            yield Button("✓ OK", variant="error" if self.is_error else "primary", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_dismiss(self):
        self.dismiss()


class ConfirmBox(ModalScreen[bool]):
    """Modal confirmation dialog."""
    
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
                yield Button("✓ Yes", variant="primary", id="yes")
                yield Button("✖ No", variant="default", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_dismiss_false(self):
        self.dismiss(False)


class TransactionItemsModal(ModalScreen):
    """Modal dialog for managing transaction line items."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+a", "add_item", "Add Item"),
        Binding("ctrl+x", "remove_item", "Remove Item"),
    ]

    def __init__(self, existing_items=None, **kwargs):
        self._items = [dict(i) for i in (existing_items or [])]
        self._displayed_items = list(self._items)
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Container(classes="items_dialog"):
            yield Label("TRANSACTION ITEMS", classes="dialog_title")
            with Horizontal(classes="items_input_row"):
                yield Input(placeholder="Name", id="item_name")
                yield Input(placeholder="Qty", id="item_qty")
                yield Input(placeholder="Unit", id="item_unit")
                yield Input(placeholder="Price", id="item_price")
                yield Button("➕ Add Item", variant="success", id="add_item_btn")
            yield Input(placeholder="Search by name...", id="item_search")
            yield DataTable(id="items_table")
            with Horizontal(classes="items_action_row"):
                yield Button("🗑 Remove", variant="error", id="remove_item_btn")
                yield Static("No items.", id="items_total")
            with Horizontal(classes="dialog_buttons"):
                yield Button("✓ Done", variant="primary", id="done")
                yield Button("✖ Cancel", variant="default", id="cancel_btn")

    def on_mount(self) -> None:
        table = self.query_one("#items_table", DataTable)
        table.add_columns("Name", "Qty", "Unit", "Unit Price", "Total")
        table.cursor_type = "row"
        table.zebra_stripes = True
        if self._items:
            self._update_display()
        self.query_one("#item_name", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "item_search":
            self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_item_btn":
            self.action_add_item()
        elif event.button.id == "remove_item_btn":
            self.action_remove_item()
        elif event.button.id == "done":
            self.dismiss(self._items)
        elif event.button.id == "cancel_btn":
            self.dismiss(None)

    def action_add_item(self):
        name = self.query_one("#item_name", Input).value.strip()
        qty_str = self.query_one("#item_qty", Input).value.strip()
        unit = self.query_one("#item_unit", Input).value.strip()
        price_str = self.query_one("#item_price", Input).value.strip()

        if not name:
            return
        if not price_str:
            return

        try:
            qty = float(qty_str) if qty_str else 1
            if qty <= 0:
                return
        except ValueError:
            return

        try:
            total_price = float(price_str)
            if total_price < 0:
                return
        except ValueError:
            return

        unit_price = round(total_price / qty, 2) if qty > 0 else total_price

        self._items.append({
            "name": name,
            "quantity": qty,
            "unit": unit or None,
            "unit_price": unit_price,
            "total_price": total_price,
        })
        self._update_display()

        self.query_one("#item_name", Input).value = ""
        self.query_one("#item_qty", Input).value = ""
        self.query_one("#item_unit", Input).value = ""
        self.query_one("#item_price", Input).value = ""
        self.query_one("#item_name", Input).focus()

    def action_remove_item(self):
        if not self._displayed_items:
            return
        table = self.query_one("#items_table", DataTable)
        if not table.rows:
            return
        try:
            cursor = table.cursor_row
            if cursor is None or cursor < 0 or cursor >= len(self._displayed_items):
                return
            item_to_remove = self._displayed_items[cursor]
            # Use identity to find the exact item in _items
            for i, item in enumerate(self._items):
                if item is item_to_remove:
                    self._items.pop(i)
                    break
            self._update_display()
        except Exception:
            pass

    def _update_display(self):
        table = self.query_one("#items_table", DataTable)
        search = self.query_one("#item_search", Input).value.strip().lower()

        if search:
            self._displayed_items = [i for i in self._items if search in i["name"].lower()]
        else:
            self._displayed_items = list(self._items)

        table.clear()
        for item in self._displayed_items:
            table.add_row(
                item["name"],
                str(item["quantity"]),
                item.get("unit") or "-",
                format_toman(item["unit_price"]),
                format_toman(item["total_price"]),
            )
        total = sum(i["total_price"] for i in self._items)
        total_display = self.query_one("#items_total", Static)
        if self._items:
            shown = len(self._displayed_items)
            total_label = f"Items total: {format_toman(total)}  |  {len(self._items)} item(s)"
            if search and shown != len(self._items):
                total_label += f"  |  showing {shown}"
            total_display.update(total_label)
        else:
            total_display.update("No items.")

    def action_cancel(self):
        self.dismiss(None)
