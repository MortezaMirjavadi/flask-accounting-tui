"""Main menu screen."""

from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from tui.widgets import HelpTip, StatusBar


class MainMenuScreen(Screen):
    """Main application menu."""

    BINDINGS = [
        Binding("q", "quit", "Exit"),
        Binding("1", "go_categories", "Categories"),
        Binding("2", "go_sources", "Sources"),
        Binding("3", "go_transactions", "Transactions"),
        Binding("4", "go_reports", "Reports"),
        Binding("5", "go_budget", "Budget"),
        Binding("6", "go_calendar", "Calendar"),
        Binding("7", "go_settings", "Settings"),
        Binding("l", "logout", "Logout"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="main_panel center_screen"):
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
                ListItem(Label("6. Calendar")),
                ListItem(Label("7. Settings")),
                ListItem(Label("8. Logout")),
                ListItem(Label("9. Exit")),
                id="main_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            now = datetime.now()
            jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
            shamsi_str = jalali_now.strftime("%Y-%m-%d")
            yield HelpTip(
                f"Date: [{shamsi_str}]  [↑/↓] Navigate  [Enter] Select  "
                f"[1-7] Quick select  [L] Logout  [Q] Exit",
                id="help"
            )
            yield StatusBar("Enter=Select  Esc=Back  L=Logout  Q=Quit", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu selection."""
        idx = event.list_view.index
        if idx == 7:  # Logout
            self.action_logout()
        elif idx == 8:  # Exit
            self.app.action_quit()
        elif idx == 5:  # Calendar
            self.action_go_calendar()
        elif 0 <= idx < 7:
            screen_class = self._get_screen_class(idx)
            self.app.push_screen(screen_class())

    def _get_screen_class(self, idx: int):
        """Dynamically import screen class to avoid circular imports."""
        screen_map = {
            0: ("tui.screens.categories", "CategoriesScreen"),
            1: ("tui.screens.sources", "SourcesScreen"),
            2: ("tui.screens.transactions", "TransactionsScreen"),
            3: ("tui.screens.reports", "ReportsScreen"),
            4: ("tui.screens.budget", "BudgetScreen"),
            5: ("tui.calendar_view", "CalendarScreen"),
            6: ("tui.screens.settings", "SettingsScreen"),
        }
        import importlib
        module_name, class_name = screen_map[idx]
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    def action_go_categories(self):
        from tui.screens.categories import CategoriesScreen
        self.app.push_screen(CategoriesScreen())

    def action_go_sources(self):
        from tui.screens.sources import SourcesScreen
        self.app.push_screen(SourcesScreen())

    def action_go_transactions(self):
        from tui.screens.transactions import TransactionsScreen
        self.app.push_screen(TransactionsScreen())

    def action_go_reports(self):
        from tui.screens.reports import ReportsScreen
        self.app.push_screen(ReportsScreen())

    def action_go_budget(self):
        from tui.screens.budget import BudgetScreen
        self.app.push_screen(BudgetScreen())

    def action_go_calendar(self):
        """Navigate to calendar screen."""
        from tui.calendar_view import CalendarScreen
        user = getattr(self.app, "user", None)
        user_id = user.get("id") if user else None
        if user_id is None:
            from tui.widgets import MessageBox
            self.app.push_screen(MessageBox("No user logged in", "Error", is_error=True))
            return
        self.app.push_screen(CalendarScreen(user_id=user_id))

    def action_go_settings(self):
        from tui.screens.settings import SettingsScreen
        self.app.push_screen(SettingsScreen())

    def action_logout(self):
        self.app.user = None
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        from tui.screens.auth import LoginScreen
        self.app.push_screen(LoginScreen())
