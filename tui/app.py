"""Main TUI application."""

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from tui.screens.auth import LoginScreen
from tui.sidebar_menu import SidebarMainMenuScreen
from tui.widgets import ConfirmBox


class AccountingApp(App):
    """Main accounting TUI application."""
    
    CSS = """
    Screen {
        align: center middle;
        content-align: center middle;
        background: $surface-darken-1;
    }

    .center_screen {
        content-align: center middle;
    }

    MainMenuScreen {
        align: center middle;
    }

    ModalScreen {
        align: center middle;
        content-align: center middle;
    }

    .center_screen.form_panel {
        width: 72;
        height: 2fr;
        max-height: 100%;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }

    .center_screen.wide_panel {
        width: 90%;
        height: 90%;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    .main_panel {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }

    .form_panel {
        width: 72;
        height: 1fr;
        max-height: 85%;
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

    TextArea {
        width: 100%;
        height: 5;
        margin: 0 0 1 0;
    }

    Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    Checkbox {
        width: 100%;
        margin: 0 0 1 0;
    }

    .hidden {
        display: none;
    }

    .button_row {
        width: 100%;
        height: auto;
        align: left middle;
    }

    .form_scroll {
        width: 100%;
        height: 1fr;
        min-height: 0;
        padding: 0 1 0 0;
    }

    .form_row {
        width: 100%;
        height: auto;
    }

    .form_col {
        width: 1fr;
        height: auto;
    }

    .form_col_spacer {
        width: 2;
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
        width: 16;
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

    JalaliDatePicker {
        width: 100%;
        height: auto;
        border: solid $primary-darken-2;
        background: $surface-darken-1;
        padding: 1;
        margin: 0 0 1 0;
    }
    JalaliDatePicker .picker_header {
        text-align: center;
        color: $primary-lighten-2;
        text-style: bold;
        height: 1;
        margin: 0 0 1 0;
    }
    JalaliDatePicker .picker_columns {
        width: 100%;
        height: auto;
    }
    JalaliDatePicker .picker_col {
        width: 1fr;
        height: auto;
        border: solid $primary-darken-2;
        background: $surface;
        padding: 0;
    }
    JalaliDatePicker .picker_col_header {
        text-align: center;
        color: $primary;
        text-style: bold;
        background: $primary-darken-3;
        height: 1;
        padding: 0;
    }
    JalaliDatePicker .picker_item {
        text-align: center;
        height: 1;
        padding: 0;
    }
    JalaliDatePicker .picker_item_selected {
        text-align: center;
        background: $primary;
        color: $text;
        text-style: bold;
        height: 1;
        padding: 0;
    }
    JalaliDatePicker .picker_controls {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0 0 0;
    }
    JalaliDatePicker .picker_controls Button {
        width: 8;
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs):
        self.user = None
        self._sidebar_host_screen = None
        self._sidebar_embed_loading = False
        super().__init__(**kwargs)

    def on_mount(self):
        self.push_screen(LoginScreen())

    def push_screen(self, screen, callback=None, wait_for_dismiss=False, *, mode=None):
        from tui.widgets.shared import MessageBox, ConfirmBox
        from tui.sidebar_menu import ContentRenderer

        host_screen = getattr(self, "_sidebar_host_screen", None)
        if host_screen is not None:
            # MessageBox & ConfirmBox — show as real modal dialogs
            if isinstance(screen, (MessageBox, ConfirmBox)):
                return super().push_screen(
                    screen,
                    callback=callback,
                    wait_for_dismiss=wait_for_dismiss,
                    mode=mode,
                )

            # Regular screens — load inside the content area
            renderer = host_screen.query_one(ContentRenderer)
            renderer.show_instance(screen, self, callback=callback)
            future = asyncio.get_running_loop().create_future()
            future.set_result(None)
            return future

        return super().push_screen(
            screen,
            callback=callback,
            wait_for_dismiss=wait_for_dismiss,
            mode=mode,
        )

    def action_quit(self):
        def on_confirm(confirmed: bool):
            if confirmed:
                self.exit()
        
        self.push_screen(
            ConfirmBox("Are you sure you want to exit?", "Exit Confirmation"),
            on_confirm,
        )
