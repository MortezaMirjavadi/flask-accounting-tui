"""Settings screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from tui.api import api_post, handle_response
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class SettingsScreen(Screen):
    """Application settings."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel"):
            yield Label("SETTINGS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
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
                "This will permanently delete ALL your categories, sources, and transactions.\n"
                "This action cannot be undone.",
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
