"""Authentication screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
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
            if data.get("totp_enabled"):
                self.app.push_screen(TwoFAVerifyScreen(data))
            else:
                self.app.user = data
                from tui.sidebar_menu import SidebarMainMenuScreen
                self.app.push_screen(SidebarMainMenuScreen())

    def do_register(self):
        self.app.push_screen(RegisterScreen())

    def action_quit(self):
        self.app.action_quit()


class RegisterScreen(Screen):
    """Registration form for new users."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("NEW USER REGISTRATION", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                yield Label("Username:")
                yield Input(placeholder="Username (min 3 characters)", id="reg_user")
                yield Label("Password:")
                yield Input(placeholder="Password (min 6 characters)", password=True, id="reg_pass")
                yield Label("Confirm Password:")
                yield Input(placeholder="Confirm password", password=True, id="reg_pass_confirm")
                yield Label("Display Name:")
                yield Input(placeholder="Your full name", id="reg_display_name")
                yield Label("Email:")
                yield Input(placeholder="your@email.com", id="reg_email")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Submit", variant="primary", id="submit_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Submit  [Esc] Cancel", id="help")
            yield StatusBar("Fill all fields  Enter=Submit  Esc=Back", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_btn":
            self.do_submit()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.do_submit()

    def do_submit(self):
        username = self.query_one("#reg_user", Input).value.strip()
        password = self.query_one("#reg_pass", Input).value
        confirm = self.query_one("#reg_pass_confirm", Input).value
        display_name = self.query_one("#reg_display_name", Input).value.strip()
        email = self.query_one("#reg_email", Input).value.strip()

        if not username or not password:
            self.app.push_screen(MessageBox("Username and password are required.", "Validation"))
            return

        if password != confirm:
            self.app.push_screen(MessageBox("Passwords do not match.", "Validation"))
            return

        payload = {
            "username": username,
            "password": password,
        }
        if display_name:
            payload["display_name"] = display_name
        if email:
            payload["email"] = email

        resp = api_post("/auth/register", payload, username=username)
        data, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(
                MessageBox(
                    "Registration submitted successfully!\n\n"
                    "Your account is pending admin approval.\n"
                    "You will be able to log in once an admin approves your account.",
                    "Registration Pending",
                ),
                lambda _: self.app.pop_screen(),
            )

    def action_go_back(self):
        self.app.pop_screen()


class TwoFAVerifyScreen(Screen):
    """OTP verification screen shown during login when 2FA is enabled."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, user_data: dict, **kwargs):
        self.user_data = user_data
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("TWO-FACTOR AUTHENTICATION", classes="main_title")
            yield Rule()
            yield Label(f"User: {self.user_data.get('username', '')}", classes="menu_header")
            yield Rule()
            yield Label("Enter the 6-digit code from your authenticator app:")
            yield Input(placeholder="123456", id="otp_code", max_length=6, type="integer")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Verify", variant="primary", id="verify_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Verify  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Verify  Esc=Cancel", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "verify_btn":
            self.verify_code()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "otp_code":
            self.verify_code()

    def verify_code(self):
        code = self.query_one("#otp_code", Input).value.strip()
        if not code or len(code) != 6:
            self.app.push_screen(MessageBox("Please enter a 6-digit code.", "Validation"))
            return

        username = self.user_data.get("username", "")
        resp = api_post("/auth/verify-2fa", {"username": username, "code": code}, username=username)
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.user = self.user_data
            from tui.sidebar_menu import SidebarMainMenuScreen
            self.app.push_screen(SidebarMainMenuScreen())

    def action_go_back(self):
        self.app.pop_screen()


class TwoFASetupScreen(Screen):
    """Screen for setting up 2FA — shows QR code and verifies first OTP."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, username: str, secret: str, uri: str, on_complete=None, **kwargs):
        self.username = username
        self.secret = secret
        self.uri = uri
        self.on_complete = on_complete
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("SETUP TWO-FACTOR AUTHENTICATION", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                yield Label("Scan this QR code with your authenticator app:")
                from tui.widgets.custom import QRCodeWidget
                yield QRCodeWidget(self.uri, id="qr_code")
                yield Static(f"Manual key: {self.secret}", id="manual_key")
                yield Rule()
                yield Label("Enter the 6-digit code to verify:")
                yield Input(placeholder="123456", id="verify_code", max_length=6, type="integer")
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Enable 2FA", variant="primary", id="enable_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Enable  [Esc] Cancel", id="help")
            yield StatusBar("Scan QR → Enter code → Enable", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enable_btn":
            self.enable_2fa()
        elif event.button.id == "cancel_btn":
            self.action_go_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "verify_code":
            self.enable_2fa()

    def enable_2fa(self):
        code = self.query_one("#verify_code", Input).value.strip()
        if not code or len(code) != 6:
            self.app.push_screen(MessageBox("Please enter a 6-digit code.", "Validation"))
            return

        resp = api_post(
            "/auth/enable-2fa",
            {"username": self.username, "secret": self.secret, "code": code},
            username=self.username,
        )
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.notify("2FA enabled successfully!", severity="success")
            if self.on_complete:
                self.on_complete()
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()
