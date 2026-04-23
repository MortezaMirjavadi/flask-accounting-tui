"""Main TUI application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from tui.screens.auth import LoginScreen
from tui.widgets import ConfirmBox


class AccountingApp(App):
    """Main accounting TUI application."""
    
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
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    #tree_scroll {
        height: 1fr;
        border: solid $primary;
    }

    #tree_content {
        width: 100%;
        padding: 1;
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
        height: 1fr;
        border: solid $primary-darken-1;
    }

    DataTable > .datatable--header {
        background: $boost;
        text-style: bold;
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

    .filter_row {
        width: 100%;
        height: auto;
        align: left middle;
        margin: 0 0 1 0;
    }

    .filter_row Input {
        width: 15;
        margin: 0 1 0 0;
    }

    .filter_row Select {
        width: 25;
        margin: 0 1 0 0;
    }

    .filter_row Button {
        margin: 0 1 0 0;
    }

    .filter_row Label {
        margin: 0 1 0 0;
        content-align: center middle;
    }

    .filter_input {
        width: 10;
    }

    Button {
        margin: 0 1 0 0;
    }

    .bottom_bar {
        dock: bottom;
        height: 2;
        width: 100%;
    }

    HelpTip {
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        content-align: center middle;
    }

    StatusBar {
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

    .error_title {
        color: $error;
    }

    .error_message {
        color: $error;
        text-style: bold;
    }

    .dialog_buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    """

    def __init__(self, **kwargs):
        self.user = None
        super().__init__(**kwargs)

    def on_mount(self):
        self.push_screen(LoginScreen())

    def action_quit(self):
        def on_confirm(confirmed: bool):
            if confirmed:
                self.exit()
        
        self.push_screen(
            ConfirmBox("Are you sure you want to exit?", "Exit Confirmation"),
            on_confirm,
        )
