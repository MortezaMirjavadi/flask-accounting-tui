"""User management screens for admins."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, Rule, Select, Static,
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


# =============================================================================
# User Management List Screen
# =============================================================================

class UserManagementScreen(Screen):
    """Admin screen to manage all users."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("n", "add_user", "New"),
        Binding("e", "edit_user", "Edit"),
        Binding("x", "delete_user", "Delete"),
        Binding("a", "approve_user", "Approve"),
        Binding("r", "reject_user", "Reject"),
        Binding("t", "activate_user", "Activate"),
        Binding("d", "deactivate_user", "Deactivate"),
    ]

    def __init__(self, **kwargs):
        self._data = []
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("USER MANAGEMENT", classes="menu_header")
            yield Rule()
            yield Static("", id="description")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="user_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="detail_panel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip(
                "[N] New  [E] Edit  [X] Delete  [A] Approve  [R] Reject  "
                "[T] Activate  [D] Deactivate  [Esc] Back",
                id="help",
            )
            yield StatusBar(
                "N=New  E=Edit  X=Delete  A=Approve  R=Reject  T=Activate  D=Deactivate  Esc=Back",
                id="status",
            )
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#user_table", DataTable)
        table.add_column("ID", key="id")
        table.add_column("Username", key="username")
        table.add_column("Display Name", key="display_name")
        table.add_column("Email", key="email")
        table.add_column("Status", key="status")
        table.add_column("Role", key="role")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def _format_status(self, item: dict) -> str:
        if not item.get("is_approved"):
            return "Pending"
        if not item.get("is_active", True):
            return "Inactive"
        return "Active"

    def load_data(self):
        table = self.query_one("#user_table", DataTable)
        table.clear()
        self._data = []

        resp = api_get("/auth/users", username=self.app.user.get("username"))
        data, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        self._data = data or []
        for item in self._data:
            status = self._format_status(item)
            role = "Admin" if item.get("is_admin") else "User"
            table.add_row(
                str(item.get("id", "")),
                item.get("username", ""),
                item.get("display_name", "") or "-",
                item.get("email", "") or "-",
                status,
                role,
                key=str(item["id"]),
            )

        self.update_detail()
        desc = self.query_one("#description", Static)
        pending = sum(1 for u in self._data if not u.get("is_approved"))
        if pending:
            desc.update(f"{len(self._data)} user(s) total. {pending} pending approval.")
        else:
            desc.update(f"{len(self._data)} user(s) total.")

    def update_detail(self):
        detail = self.query_one("#detail_panel", Static)
        item = self._get_selected_item()

        if item is None:
            detail.update("Select a user to see details.")
            return

        status = self._format_status(item)
        role = "Admin" if item.get("is_admin") else "User"
        lines = [
            f"[b]Username:[/b] {item.get('username', '')}",
            f"[b]Display Name:[/b] {item.get('display_name', '') or '-'}",
            f"[b]Email:[/b] {item.get('email', '') or '-'}",
            f"[b]Status:[/b] {status}",
            f"[b]Role:[/b] {role}",
            f"[b]Registered:[/b] {item.get('created_at', '')}",
        ]
        detail.update("\n".join(lines))

    def _get_selected_item(self):
        table = self.query_one("#user_table", DataTable)
        if not table.rows or not self._data:
            return None

        cursor = table.cursor_row
        if cursor is None or cursor < 0 or cursor >= len(self._data):
            return None

        return self._data[cursor]

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    # --- Add / Edit / Delete ---

    def action_add_user(self):
        def on_save():
            self.load_data()

        self.app.push_screen(UserAddScreen(on_save=on_save))

    def action_edit_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return

        def on_save():
            self.load_data()

        self.app.push_screen(UserEditScreen(item["id"], on_save=on_save))

    def action_delete_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return
        if item.get("is_admin"):
            self.app.push_screen(MessageBox("Cannot delete an admin user.", "Info"))
            return

        def on_confirm(result):
            if not result:
                return
            resp = api_delete(
                f"/auth/users/{item['id']}",
                username=self.app.user.get("username"),
            )
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.app.notify(f"User '{item['username']}' deleted.", severity="warning")
                self.load_data()

        self.app.push_screen(
            ConfirmBox(
                f"Delete user '{item['username']}' permanently?\nThis cannot be undone.",
                "Confirm Delete",
            ),
            on_confirm,
        )

    # --- Approve / Reject ---

    def action_approve_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return
        if item.get("is_approved"):
            self.app.push_screen(MessageBox("User is already approved.", "Info"))
            return

        def do_approve(result):
            if not result:
                return
            resp = api_post(
                f"/auth/approve-user/{item['id']}", {},
                username=self.app.user.get("username"),
            )
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.app.notify(f"User '{item['username']}' approved!", severity="success")
                self.load_data()

        self.app.push_screen(
            ConfirmBox(f"Approve user '{item['username']}'?", "Confirm Approval"),
            do_approve,
        )

    def action_reject_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return
        if item.get("is_approved"):
            self.app.push_screen(MessageBox("Only pending users can be rejected.", "Info"))
            return

        def do_reject(result):
            if not result:
                return
            resp = api_post(
                f"/auth/reject-user/{item['id']}", {},
                username=self.app.user.get("username"),
            )
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.app.notify(f"User '{item['username']}' rejected.", severity="warning")
                self.load_data()

        self.app.push_screen(
            ConfirmBox(
                f"Reject and delete user '{item['username']}'?\nThis cannot be undone.",
                "Confirm Rejection",
            ),
            do_reject,
        )

    # --- Activate / Deactivate ---

    def action_activate_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return
        if not item.get("is_approved"):
            self.app.push_screen(MessageBox("User must be approved first.", "Info"))
            return
        if item.get("is_active", True):
            self.app.push_screen(MessageBox("User is already active.", "Info"))
            return

        def do_activate(result):
            if not result:
                return
            resp = api_post(
                f"/auth/activate-user/{item['id']}", {},
                username=self.app.user.get("username"),
            )
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.app.notify(f"User '{item['username']}' activated!", severity="success")
                self.load_data()

        self.app.push_screen(
            ConfirmBox(f"Activate user '{item['username']}'?", "Confirm Activation"),
            do_activate,
        )

    def action_deactivate_user(self):
        item = self._get_selected_item()
        if item is None:
            self.app.push_screen(MessageBox("No user selected.", "Info"))
            return
        if not item.get("is_approved"):
            self.app.push_screen(MessageBox("Only approved users can be deactivated.", "Info"))
            return
        if not item.get("is_active", True):
            self.app.push_screen(MessageBox("User is already inactive.", "Info"))
            return
        if item.get("is_admin"):
            self.app.push_screen(MessageBox("Admin users cannot be deactivated.", "Info"))
            return

        def do_deactivate(result):
            if not result:
                return
            resp = api_post(
                f"/auth/deactivate-user/{item['id']}", {},
                username=self.app.user.get("username"),
            )
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.app.notify(f"User '{item['username']}' deactivated.", severity="warning")
                self.load_data()

        self.app.push_screen(
            ConfirmBox(f"Deactivate user '{item['username']}'?", "Confirm Deactivation"),
            do_deactivate,
        )

    def on_key(self, event):
        key = event.key.lower()
        if key == "n":
            event.stop()
            self.action_add_user()
        elif key == "e":
            event.stop()
            self.action_edit_user()
        elif key == "x":
            event.stop()
            self.action_delete_user()
        elif key == "a":
            event.stop()
            self.action_approve_user()
        elif key == "r":
            event.stop()
            self.action_reject_user()
        elif key == "t":
            event.stop()
            self.action_activate_user()
        elif key == "d":
            event.stop()
            self.action_deactivate_user()

    def action_go_back(self):
        self.app.pop_screen()


# =============================================================================
# User Add Screen
# =============================================================================

class UserAddScreen(Screen):
    """Admin screen to create a new user directly."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, on_save=None, **kwargs):
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("ADD NEW USER", classes="menu_header")
            yield Rule()
            with Vertical(classes="form_scroll"):
                yield Label("Username:")
                yield Input(placeholder="Username (min 3 characters)", id="add_username")
                yield Label("Password:")
                yield Input(placeholder="Password (min 6 characters)", password=True, id="add_password")
                yield Label("Display Name:")
                yield Input(placeholder="Full name (optional)", id="add_display_name")
                yield Label("Email:")
                yield Input(placeholder="email@example.com (optional)", id="add_email")
                yield Label("Role:")
                yield Select(
                    [("User", "user"), ("Admin", "admin")],
                    value="user",
                    id="add_role",
                )
                yield Label("Active:")
                yield Select(
                    [("Yes", "yes"), ("No", "no")],
                    value="yes",
                    id="add_active",
                )
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Create", variant="primary", id="create_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Create  [Esc] Cancel", id="help")
            yield StatusBar("Fill fields  Enter=Create  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create_btn":
            self.save()
        else:
            self.action_go_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.save()

    def save(self):
        username = self.query_one("#add_username", Input).value.strip()
        password = self.query_one("#add_password", Input).value
        display_name = self.query_one("#add_display_name", Input).value.strip()
        email = self.query_one("#add_email", Input).value.strip()
        role = self.query_one("#add_role", Select).value
        active = self.query_one("#add_active", Select).value

        if not username:
            self.app.push_screen(MessageBox("Username is required.", "Validation"))
            return
        if not password:
            self.app.push_screen(MessageBox("Password is required.", "Validation"))
            return
        if len(username) < 3:
            self.app.push_screen(MessageBox("Username must be at least 3 characters.", "Validation"))
            return
        if len(password) < 6:
            self.app.push_screen(MessageBox("Password must be at least 6 characters.", "Validation"))
            return
        if email and "@" not in email:
            self.app.push_screen(MessageBox("Invalid email address.", "Validation"))
            return

        payload = {
            "username": username,
            "password": password,
            "is_admin": role == "admin",
            "is_active": active == "yes",
        }
        if display_name:
            payload["display_name"] = display_name
        if email:
            payload["email"] = email

        resp = api_post("/auth/users", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.notify(f"User '{username}' created!", severity="success")
            if self.on_save:
                self.on_save()
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


# =============================================================================
# User Edit Screen
# =============================================================================

class UserEditScreen(Screen):
    """Admin screen to edit an existing user."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, user_id: int, on_save=None, **kwargs):
        self.user_id = user_id
        self.on_save = on_save
        self._user = None
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("EDIT USER", classes="menu_header")
            yield Rule()
            with Vertical(classes="form_scroll"):
                yield Label("Username:")
                yield Static(id="edit_username")
                yield Label("Display Name:")
                yield Input(placeholder="Full name", id="edit_display_name")
                yield Label("Email:")
                yield Input(placeholder="email@example.com", id="edit_email")
                yield Label("New Password (leave blank to keep current):")
                yield Input(placeholder="New password", password=True, id="edit_password")
                yield Label("Role:")
                yield Select(
                    [("User", "user"), ("Admin", "admin")],
                    id="edit_role",
                )
                yield Label("Approved:")
                yield Select(
                    [("Yes", "yes"), ("No", "no")],
                    id="edit_approved",
                )
                yield Label("Active:")
                yield Select(
                    [("Yes", "yes"), ("No", "no")],
                    id="edit_active",
                )
            yield Static("")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Edit fields  Enter=Save  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        resp = api_get(
            f"/auth/users/{self.user_id}",
            username=self.app.user.get("username"),
        )
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        self._user = data
        self.query_one("#edit_username", Static).update(data.get("username", ""))
        self.query_one("#edit_display_name", Input).value = data.get("display_name") or ""
        self.query_one("#edit_email", Input).value = data.get("email") or ""
        self.query_one("#edit_role", Select).value = "admin" if data.get("is_admin") else "user"
        self.query_one("#edit_approved", Select).value = "yes" if data.get("is_approved") else "no"
        self.query_one("#edit_active", Select).value = "yes" if data.get("is_active", True) else "no"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self.save()
        else:
            self.action_go_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.save()

    def save(self):
        if self._user is None:
            return

        display_name = self.query_one("#edit_display_name", Input).value.strip()
        email = self.query_one("#edit_email", Input).value.strip()
        password = self.query_one("#edit_password", Input).value
        role = self.query_one("#edit_role", Select).value
        approved = self.query_one("#edit_approved", Select).value
        active = self.query_one("#edit_active", Select).value

        if email and "@" not in email:
            self.app.push_screen(MessageBox("Invalid email address.", "Validation"))
            return
        if password and len(password) < 6:
            self.app.push_screen(MessageBox("Password must be at least 6 characters.", "Validation"))
            return

        payload = {
            "display_name": display_name or None,
            "email": email or None,
            "is_admin": role == "admin",
            "is_approved": approved == "yes",
            "is_active": active == "yes",
        }
        if password:
            payload["password"] = password

        resp = api_put(
            f"/auth/users/{self.user_id}",
            payload,
            username=self.app.user.get("username"),
        )
        _, err = handle_response(resp)

        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.notify(f"User '{self._user.get('username', '')}' updated!", severity="success")
            if self.on_save:
                self.on_save()
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()
