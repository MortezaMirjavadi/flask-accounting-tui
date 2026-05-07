"""Settings screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from tui.api import api_get, api_post, handle_response
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


class SettingsScreen(Screen):
    """Application settings."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("SETTINGS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Security")),
                ListItem(Label("2. Reset All Data")),
                ListItem(Label("3. Back")),
                id="settings_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_security()
        elif idx == 1:
            self.action_reset_data()
        elif idx == 2:
            self.action_go_back()

    def action_security(self):
        """Navigate to security settings."""
        self.app.push_screen(SecurityScreen())

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


class SecurityScreen(Screen):
    """Security settings — 2FA management."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
            yield Label("SECURITY SETTINGS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield Static("", id="twofa_status")
            yield Static("")
            yield ListView(
                ListItem(Label("1. Enable 2FA")),
                ListItem(Label("2. Disable 2FA")),
                ListItem(Label("3. Back")),
                id="security_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        self._refresh_status()

    def _refresh_status(self):
        username = self.app.user.get("username", "")
        resp = api_get("/auth/me", params={"username": username})
        data, err = handle_response(resp)
        status = self.query_one("#twofa_status", Static)
        if not err and data:
            if data.get("totp_enabled"):
                status.update("[green]Two-Factor Authentication: Enabled[/green]")
            else:
                status.update("[dim]Two-Factor Authentication: Disabled[/dim]")
        else:
            status.update("[dim]Two-Factor Authentication: Disabled[/dim]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_enable_2fa()
        elif idx == 1:
            self.action_disable_2fa()
        elif idx == 2:
            self.action_go_back()

    def action_enable_2fa(self):
        """Start 2FA setup flow."""
        username = self.app.user.get("username", "")
        self.app.notify("Requesting 2FA setup...", severity="information")
        resp = api_post("/auth/setup-2fa", {"username": username}, username=username)
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        from tui.screens.auth import TwoFASetupScreen

        def on_complete():
            self._refresh_status()
            self.app.notify("2FA enabled successfully!", severity="success")

        self.app.push_screen(
            TwoFASetupScreen(
                username=username,
                secret=data["secret"],
                uri=data["uri"],
                on_complete=on_complete,
            )
        )

    def action_disable_2fa(self):
        """Disable 2FA after confirmation."""
        def on_confirm(confirmed: bool):
            if not confirmed:
                return
            username = self.app.user.get("username", "")
            resp = api_post("/auth/disable-2fa", {"username": username}, username=username)
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self._refresh_status()
                self.app.notify("2FA has been disabled.", severity="warning")

        self.app.push_screen(
            ConfirmBox(
                "Are you sure you want to disable Two-Factor Authentication?\n"
                "Your account will be less secure.",
                "Disable 2FA?",
            ),
            on_confirm,
        )

    def action_go_back(self):
        self.app.pop_screen()
