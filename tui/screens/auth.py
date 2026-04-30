"""Authentication screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Rule

from tui.api import api_post, handle_response
from tui.widgets import HelpTip, MessageBox, StatusBar


class LoginScreen(Screen):
    """Login and registration screen."""
    
    BINDINGS = [
        Binding("escape", "quit", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("TERMINAL ACCOUNTING SYSTEM", classes="main_title")
            yield Rule()
            yield Label("LOGIN", classes="menu_header")
            yield Rule()
            yield Label("Username:")
            yield Input(placeholder="Username", id="login_user")
            yield Label("Password:")
            yield Input(placeholder="Password", password=True, id="login_pass")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Login", variant="primary", id="login_btn")
                yield Button("Register", variant="default", id="register_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Login  [Esc] Exit", id="help")
            yield StatusBar("Enter=Login  Esc=Quit", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login_btn":
            self.do_login()
        elif event.button.id == "register_btn":
            self.do_register()

    def do_login(self):
        username = self.query_one("#login_user", Input).value.strip()
        password = self.query_one("#login_pass", Input).value
        
        if not username or not password:
            self.app.push_screen(MessageBox("Username and password are required.", "Validation"))
            return
        
        resp = api_post("/auth/login", {"username": username, "password": password}, username=username)
        data, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.user = data
            # Import here to avoid circular dependency
            from tui.screens.main_menu import MainMenuScreen
            self.app.push_screen(MainMenuScreen())

    def do_register(self):
        username = self.query_one("#login_user", Input).value.strip()
        password = self.query_one("#login_pass", Input).value
        
        if not username or not password:
            self.app.push_screen(MessageBox("Username and password are required.", "Validation"))
            return
        
        resp = api_post("/auth/register", {"username": username, "password": password}, username=username)
        data, err = handle_response(resp)
        
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Registration successful. Please log in.", "Success"))

    def action_quit(self):
        self.app.action_quit()
