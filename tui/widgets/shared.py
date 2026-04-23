"""Shared reusable widgets used across multiple screens."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


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
            yield Button("OK", variant="error" if self.is_error else "primary", id="ok")

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
                yield Button("Yes", variant="primary", id="yes")
                yield Button("No", variant="default", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_dismiss_false(self):
        self.dismiss(False)
