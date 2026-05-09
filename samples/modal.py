#!/usr/bin/env python3
"""
modal_backdrop_example.py
Demonstrates how to create modal dialogs with backdrop effect in Textual.
"""

from textual.app import App, ComposeResult
from textual.containers import (
    Container, Horizontal, Vertical, Center, Middle
)
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    Label,
    Select,
    Checkbox,
    RadioButton,
    RadioSet,
    OptionList,
    Log,
)
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.css.query import NoMatches
from datetime import datetime
from typing import Optional


# ============================================================
# 1. Modal Form Screen with Backdrop
# ============================================================
class ModalFormScreen(ModalScreen):
    """
    A modal screen that appears on top of the main app
    with a backdrop (dimmed background) effect.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    #modal-backdrop {
        background: rgba(0, 0, 0, 0.7);
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #modal-form-container {
        background: $surface;
        border: heavy $primary;
        border-radius: 8;
        padding: 2 3;
        width: 70%;
        max-width: 80;
        height: auto;
        max-height: 90%;
        overflow-y: auto;
    }

    #form-title {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
        text-style: bold;
        color: $primary;
    }

    .form-field {
        width: 100%;
        margin: 1 0;
    }

    .form-label {
        width: 100%;
        margin-bottom: 0;
        text-style: bold;
    }

    .form-input {
        width: 100%;
    }

    #form-buttons {
        width: 100%;
        margin-top: 2;
        height: auto;
        align: center middle;
    }

    .btn {
        min-width: 20%;
        margin: 0 1;
    }

    #form-message {
        width: 100%;
        text-align: center;
        margin-top: 1;
        padding: 1;
    }

    .error {
        color: $error;
        background: $error 30%;
    }

    .success {
        color: $success;
        background: $success 30%;
    }

    .warning {
        color: $warning;
        background: $warning 30%;
    }
    """

    def __init__(self, title: str = "Form", **kwargs):
        # ============================================
        # MUST call super().__init__ FIRST!
        # ============================================
        super().__init__(**kwargs)
        self.modal_title = title
        self.form_data = {}

    def compose(self) -> ComposeResult:
        with Container(id="modal-backdrop"):
            with Vertical(id="modal-form-container"):
                yield Static(self.modal_title, id="form-title")

                # ---- Name ----
                with Container(classes="form-field"):
                    yield Label("Full Name:", classes="form-label")
                    yield Input(
                        placeholder="Enter your full name",
                        id="name-input",
                        classes="form-input",
                    )

                # ---- Email ----
                with Container(classes="form-field"):
                    yield Label("Email:", classes="form-label")
                    yield Input(
                        placeholder="Enter your email",
                        id="email-input",
                        classes="form-input",
                    )

                # ---- Account Type ----
                with Container(classes="form-field"):
                    yield Label("Account Type:", classes="form-label")
                    yield Select(
                        [
                            ("checking", "Checking Account"),
                            ("savings", "Savings Account"),
                            ("credit", "Credit Card"),
                            ("cash", "Cash"),
                            ("investment", "Investment Account"),
                        ],
                        id="account-type",
                        prompt="Select account type",
                        classes="form-input",
                    )

                # ---- Balance ----
                with Container(classes="form-field"):
                    yield Label("Initial Balance:", classes="form-label")
                    yield Input(
                        placeholder="0.00",
                        id="balance-input",
                        classes="form-input",
                    )

                # ---- Radio options ----
                with Container(classes="form-field"):
                    yield Label("Account Options:", classes="form-label")
                    yield RadioSet(
                        RadioButton(
                            "Primary Account", value=True, id="primary-radio"
                        ),
                        RadioButton("Secondary Account", id="secondary-radio"),
                        RadioButton("Joint Account", id="joint-radio"),
                    )

                # ---- Checkbox ----
                with Container(classes="form-field"):
                    yield Checkbox(
                        "Enable notifications", id="notifications-checkbox"
                    )

                yield Static("", id="form-message")

                with Horizontal(id="form-buttons"):
                    yield Button(
                        "Cancel", id="cancel-btn", variant="error", classes="btn"
                    )
                    yield Button(
                        "Submit", id="submit-btn", variant="primary", classes="btn"
                    )
                    yield Button(
                        "Reset", id="reset-btn", variant="default", classes="btn"
                    )

    def on_mount(self) -> None:
        try:
            self.query_one("#name-input", Input).focus()
        except NoMatches:
            pass

    def validate_form(self) -> bool:
        errors: list[str] = []

        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            errors.append("Name is required")

        email = self.query_one("#email-input", Input).value.strip()
        if not email:
            errors.append("Email is required")
        elif "@" not in email:
            errors.append("Invalid email format")

        account_type = self.query_one("#account-type", Select).value
        if not account_type:
            errors.append("Please select an account type")

        balance = self.query_one("#balance-input", Input).value.strip()
        if not balance:
            errors.append("Initial balance is required")
        else:
            try:
                float(balance)
            except ValueError:
                errors.append("Invalid balance format")

        if errors:
            self._show_message("; ".join(errors), "error")
            return False

        return True

    def collect_form_data(self) -> dict:
        return {
            "name": self.query_one("#name-input", Input).value.strip(),
            "email": self.query_one("#email-input", Input).value.strip(),
            "account_type": self.query_one("#account-type", Select).value,
            "balance": float(
                self.query_one("#balance-input", Input).value.strip()
            ),
            "is_primary": self.query_one(
                "#primary-radio", RadioButton
            ).value,
            "notifications": self.query_one(
                "#notifications-checkbox", Checkbox
            ).value,
        }

    def _show_message(self, message: str, msg_type: str = "info") -> None:
        msg = self.query_one("#form-message", Static)
        msg.update(message)
        msg.remove_class("error", "success", "warning", "info")
        msg.add_class(msg_type)

    def action_submit(self) -> None:
        if self.validate_form():
            self.form_data = self.collect_form_data()
            self._show_message("Form submitted successfully!", "success")
            self.set_timer(1.0, lambda: self.dismiss(self.form_data))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "reset-btn":
            self._reset_form()

    def _reset_form(self) -> None:
        self.query_one("#name-input", Input).value = ""
        self.query_one("#email-input", Input).value = ""
        self.query_one("#account-type", Select).value = None
        self.query_one("#balance-input", Input).value = ""
        self.query_one("#primary-radio", RadioButton).value = True
        self.query_one("#secondary-radio", RadioButton).value = False
        self.query_one("#joint-radio", RadioButton).value = False
        self.query_one("#notifications-checkbox", Checkbox).value = False
        self._show_message("", "info")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "name-input":
            self.query_one("#email-input", Input).focus()
        elif event.input.id == "email-input":
            self.query_one("#account-type", Select).focus()
        elif event.input.id == "balance-input":
            self.query_one("#primary-radio", RadioButton).focus()


# ============================================================
# 2. Confirmation Dialog with Backdrop
# ============================================================
class ConfirmDialogScreen(ModalScreen):
    """
    A simple confirmation dialog with backdrop.
    Returns True if confirmed, False if cancelled.
    """

    DEFAULT_CSS = """
    #confirm-backdrop {
        background: rgba(0, 0, 0, 0.6);
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #confirm-dialog {
        background: $surface;
        border: heavy $warning;
        border-radius: 6;
        padding: 2 3;
        width: 50%;
        max-width: 60;
        height: auto;
        align: center middle;
    }

    #confirm-title {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
        color: $warning;
    }

    #confirm-message {
        width: 100%;
        text-align: center;
        margin: 2 0;
    }

    #confirm-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    .confirm-btn {
        min-width: 30%;
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str, **kwargs):
        # ============================================
        # MUST call super().__init__ FIRST!
        # ============================================
        super().__init__(**kwargs)
        self.dlg_title = title
        self.dlg_message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-backdrop"):
            with Vertical(id="confirm-dialog"):
                yield Static(self.dlg_title, id="confirm-title")
                yield Static(self.dlg_message, id="confirm-message")
                yield Horizontal(
                    Button(
                        "Cancel",
                        id="cancel-confirm",
                        variant="error",
                        classes="confirm-btn",
                    ),
                    Button(
                        "Confirm",
                        id="accept-confirm",
                        variant="warning",
                        classes="confirm-btn",
                    ),
                    id="confirm-buttons",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-confirm":
            self.dismiss(False)
        elif event.button.id == "accept-confirm":
            self.dismiss(True)


# ============================================================
# 3. Animated Modal with Backdrop
# ============================================================
class AnimatedBackdropModal(ModalScreen):
    """
    Enhanced modal with a fade-in backdrop.
    """

    DEFAULT_CSS = """
    #animated-backdrop {
        background: rgba(0, 0, 0, 0);
        width: 100%;
        height: 100%;
        align: center middle;
        transition: background 300ms in_out_cubic;
    }

    #animated-backdrop.active {
        background: rgba(0, 0, 0, 0.7);
    }

    #animated-modal {
        background: $surface;
        border: heavy $primary;
        border-radius: 12;
        padding: 3;
        width: 60%;
        max-width: 70;
        height: auto;
    }

    #animated-title {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
        text-style: bold;
        color: $primary;
    }

    #animated-content {
        width: 100%;
        margin: 2 0;
    }

    #animated-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    .animated-btn {
        min-width: 30%;
        margin: 0 1;
    }
    """

    def __init__(self, title: str, content: str, **kwargs):
        # ============================================
        # MUST call super().__init__ FIRST!
        # ============================================
        super().__init__(**kwargs)
        self.modal_title = title
        self.modal_content = content

    def compose(self) -> ComposeResult:
        with Container(id="animated-backdrop"):
            with Vertical(id="animated-modal"):
                yield Static(self.modal_title, id="animated-title")
                yield Static(self.modal_content, id="animated-content")
                yield Horizontal(
                    Button(
                        "Cancel",
                        id="cancel-animated",
                        variant="error",
                        classes="animated-btn",
                    ),
                    Button(
                        "OK",
                        id="ok-animated",
                        variant="primary",
                        classes="animated-btn",
                    ),
                    id="animated-buttons",
                )

    def on_mount(self) -> None:
        self.set_timer(0.05, self._activate)

    def _activate(self) -> None:
        try:
            self.query_one("#animated-backdrop").add_class("active")
        except NoMatches:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-animated":
            self.dismiss(False)
        elif event.button.id == "ok-animated":
            self.dismiss(True)


# ============================================================
# 4. Main Dashboard
# ============================================================
class DashboardWithModals(App):
    """
    Main financial dashboard that uses modal forms with backdrop.
    """

    TITLE = "Financial Dashboard with Modal Forms"
    SUB_TITLE = "Click buttons to open modal dialogs"

    DEFAULT_CSS = """
    #app-container {
        height: 100%;
        width: 100%;
    }

    #sidebar {
        width: 25%;
        min-width: 24;
        height: 100%;
        background: $surface;
        border-right: solid $primary;
        padding: 1;
    }

    #main-content {
        width: 75%;
        height: 100%;
        background: $background;
        padding: 1;
    }

    .sidebar-title {
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }

    .action-btn {
        width: 100%;
        margin: 1 0;
    }

    #dashboard-title {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
        text-style: bold;
        color: $primary;
    }

    #activity-log {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    #sample-table {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = [
            {"name": "Checking", "balance": 5240.55, "type": "bank"},
            {"name": "Savings", "balance": 12500.00, "type": "bank"},
            {"name": "Cash", "balance": 320.00, "type": "cash"},
            {"name": "Credit Card", "balance": -1250.30, "type": "credit"},
        ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="app-container"):
            # ---- Sidebar ----
            with Vertical(id="sidebar"):
                yield Static("User Dashboard", classes="sidebar-title")
                yield Static("John Doe", id="user-name")

                yield Static("Actions", classes="sidebar-title")
                yield Button(
                    "Add Account",
                    id="add-account-btn",
                    variant="primary",
                    classes="action-btn",
                )
                yield Button(
                    "Transfer Funds",
                    id="transfer-btn",
                    variant="success",
                    classes="action-btn",
                )
                yield Button(
                    "Edit Profile",
                    id="edit-profile-btn",
                    variant="warning",
                    classes="action-btn",
                )
                yield Button(
                    "Delete Account",
                    id="delete-account-btn",
                    variant="error",
                    classes="action-btn",
                )
                yield Button(
                    "Animated Modal",
                    id="animated-btn",
                    variant="default",
                    classes="action-btn",
                )

                yield Static("Stats", classes="sidebar-title")
                yield Static(
                    f"Accounts: {len(self.accounts)}", id="stat-count"
                )
                balance = sum(a["balance"] for a in self.accounts)
                yield Static(f"Total: ${balance:,.2f}", id="stat-balance")

                yield Button(
                    "Exit", id="exit-btn", variant="error", classes="action-btn"
                )

            # ---- Main content ----
            with Vertical(id="main-content"):
                yield Static("Financial Overview", id="dashboard-title")
                yield DataTable(id="sample-table")

                yield Static("Activity Log", classes="sidebar-title")
                with Container(id="activity-log"):
                    yield Static("System started")

        yield Footer()

    # ---- lifecycle ----
    def on_mount(self) -> None:
        self._setup_sample_table()
        self._log("Dashboard loaded successfully")

    def _setup_sample_table(self) -> None:
        table = self.query_one("#sample-table", DataTable)
        table.add_columns("Account", "Type", "Balance", "Status")
        for account in self.accounts:
            balance = account["balance"]
            status = "OK" if balance >= 0 else "!!"
            table.add_row(
                account["name"],
                account["type"].capitalize(),
                f"${balance:,.2f}",
                status,
            )

    def _log(self, message: str) -> None:
        log_area = self.query_one("#activity-log")
        ts = datetime.now().strftime("%H:%M:%S")
        log_area.mount(Static(f"[{ts}] {message}"))

    def _update_stats(self) -> None:
        count_w = self.query_one("#stat-count", Static)
        balance_w = self.query_one("#stat-balance", Static)
        count_w.update(f"Accounts: {len(self.accounts)}")
        total = sum(a["balance"] for a in self.accounts)
        balance_w.update(f"Total: ${total:,.2f}")

    # ---- callbacks ----
    def _on_account_added(self, result: Optional[dict]) -> None:
        if result:
            account = {
                "name": result["name"],
                "type": result["account_type"],
                "balance": result["balance"],
            }
            self.accounts.append(account)

            table = self.query_one("#sample-table", DataTable)
            balance = result["balance"]
            status = "OK" if balance >= 0 else "!!"
            table.add_row(
                result["name"],
                result["account_type"].capitalize(),
                f"${balance:,.2f}",
                status,
            )
            self._update_stats()
            self._log(f"Added account: {result['name']} (${balance:,.2f})")
        else:
            self._log("Account creation cancelled")

    def _on_transfer_confirmed(self, result: bool) -> None:
        if result:
            self._log("Transfer initiated (demo)")
        else:
            self._log("Transfer cancelled")

    def _on_delete_confirmed(self, result: bool) -> None:
        if result:
            if self.accounts:
                deleted = self.accounts.pop(0)
                self._setup_sample_table()
                self._update_stats()
                self._log(f"Deleted account: {deleted['name']}")
        else:
            self._log("Delete cancelled")

    # ---- button handler ----
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id

        if btn == "add-account-btn":
            self.push_screen(
                ModalFormScreen(title="Add New Account"),
                callback=self._on_account_added,
            )

        elif btn == "transfer-btn":
            self.push_screen(
                ConfirmDialogScreen(
                    title="Transfer Funds",
                    message="Transfer $500 from Checking to Savings?",
                ),
                callback=self._on_transfer_confirmed,
            )

        elif btn == "edit-profile-btn":
            self.push_screen(
                ModalFormScreen(title="Edit Profile"),
                callback=lambda r: self._log(
                    "Profile updated" if r else "Profile edit cancelled"
                ),
            )

        elif btn == "delete-account-btn":
            if not self.accounts:
                self._log("No accounts to delete")
                return
            name = self.accounts[0]["name"]
            self.push_screen(
                ConfirmDialogScreen(
                    title="Delete Account",
                    message=f"Delete '{name}'? This cannot be undone.",
                ),
                callback=self._on_delete_confirmed,
            )

        elif btn == "animated-btn":
            self.push_screen(
                AnimatedBackdropModal(
                    title="Animated Modal",
                    content="This modal has a fade-in backdrop animation!",
                ),
                callback=lambda r: self._log(
                    f"Animated modal: {'OK' if r else 'Cancelled'}"
                ),
            )

        elif btn == "exit-btn":
            self.push_screen(
                ConfirmDialogScreen(
                    title="Exit Application",
                    message="Are you sure you want to exit?",
                ),
                callback=lambda r: self.exit() if r else None,
            )


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    app = DashboardWithModals()
    app.run()
