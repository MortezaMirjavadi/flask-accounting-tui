"""Contact, Tag, and Label management TUI screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Select, Static, Rule, TextArea,
)

from tui.api import api_get, api_post, api_put, api_delete, handle_response, format_toman
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


# ── Contact Management ──────────────────────────────────────────────

class ContactListScreen(Screen):
    """List and manage contacts."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_contact", "Add"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("CONTACTS", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Input(placeholder="Search contacts...", id="contact_search")
                yield Button("Search", variant="primary", id="contact_search_btn")
            yield DataTable(id="contact_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[A] Add  [E] Edit  [D] Delete  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("A=Add  E=Edit  D=Delete  R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#contact_table", DataTable)
        table.add_columns("ID", "Name", "Phone", "Email", "Address")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._data = []
        self.load_data()

    def load_data(self, search=None):
        table = self.query_one("#contact_table", DataTable)
        table.clear()
        params = {}
        if search:
            params["q"] = search
        resp = api_get("/metadata/contacts", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No contacts found", "-", "-", "-")
        else:
            for c in self._data:
                table.add_row(
                    str(c["id"]),
                    (c.get("name") or "")[:25],
                    (c.get("phone") or "-")[:15],
                    (c.get("email") or "-")[:25],
                    (c.get("address") or "-")[:30],
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "contact_search_btn":
            search = self.query_one("#contact_search", Input).value.strip()
            self.load_data(search=search or None)

    def _get_selected_id(self):
        table = self.query_one("#contact_table", DataTable)
        if not table.rows or not self._data:
            return None
        try:
            cursor = table.cursor_row
            if cursor is None or cursor < 0 or cursor >= len(self._data):
                return None
            row_key = table.coordinate_to_cell_key((cursor, 0)).row_key
            cells = table.get_row(row_key)
            return int(cells[0])
        except Exception:
            return None

    def action_add_contact(self):
        def on_save():
            self.load_data()
        self.app.push_screen(ContactFormScreen(on_save=on_save))

    def action_edit_selected(self):
        cid = self._get_selected_id()
        if cid is None:
            self.app.push_screen(MessageBox("No contact selected.", "Info"))
            return
        def on_save():
            self.load_data()
        self.app.push_screen(ContactFormScreen(contact_id=cid, on_save=on_save))

    def action_delete_selected(self):
        cid = self._get_selected_id()
        if cid is None:
            self.app.push_screen(MessageBox("No contact selected.", "Info"))
            return
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_delete(f"/metadata/contacts/{cid}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
        self.app.push_screen(ConfirmBox("Delete this contact?", "Confirm"), on_confirm)

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()


class ContactFormScreen(Screen):
    """Add or edit a contact."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, contact_id=None, on_save=None, **kwargs):
        self.contact_id = contact_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        title = "EDIT CONTACT" if self.contact_id else "ADD CONTACT"
        with Container(classes="form_panel center_screen"):
            yield Label(title, classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                yield Label("Name:")
                yield Input(placeholder="Full name", id="contact_name")
                yield Label("Phone:")
                yield Input(placeholder="Phone number", id="contact_phone")
                yield Label("Email:")
                yield Input(placeholder="Email address", id="contact_email")
                yield Label("Address:")
                yield TextArea(id="contact_address")
                yield Label("Notes:")
                yield TextArea(id="contact_notes")
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        if self.contact_id:
            resp = api_get(f"/metadata/contacts/{self.contact_id}", username=self.app.user.get("username"))
            data, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
                return
            self.query_one("#contact_name", Input).value = data.get("name", "")
            self.query_one("#contact_phone", Input).value = data.get("phone") or ""
            self.query_one("#contact_email", Input).value = data.get("email") or ""
            self.query_one("#contact_address", TextArea).load_text(data.get("address") or "")
            self.query_one("#contact_notes", TextArea).load_text(data.get("notes") or "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        name = self.query_one("#contact_name", Input).value.strip()
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        payload = {
            "name": name,
            "phone": self.query_one("#contact_phone", Input).value.strip() or None,
            "email": self.query_one("#contact_email", Input).value.strip() or None,
            "address": self.query_one("#contact_address", TextArea).text.strip() or None,
            "notes": self.query_one("#contact_notes", TextArea).text.strip() or None,
        }
        if self.contact_id:
            resp = api_put(f"/metadata/contacts/{self.contact_id}", payload, username=self.app.user.get("username"))
        else:
            resp = api_post("/metadata/contacts", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()


# ── Tag Management ──────────────────────────────────────────────────

class TagListScreen(Screen):
    """List and manage tags."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_tag", "Add"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("TAGS", classes="menu_header")
            yield Rule()
            yield DataTable(id="tag_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[A] Add  [E] Edit  [D] Delete  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("A=Add  E=Edit  D=Delete  R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tag_table", DataTable)
        table.add_columns("ID", "Name", "Color", "Used In")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._data = []
        self.load_data()

    def load_data(self):
        table = self.query_one("#tag_table", DataTable)
        table.clear()
        resp = api_get("/metadata/tags", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No tags found", "-", "-")
        else:
            for t in self._data:
                table.add_row(
                    str(t["id"]),
                    t.get("name", ""),
                    t.get("color") or "-",
                    f"{t.get('usage_count', 0)} transactions",
                )

    def _get_selected_id(self):
        table = self.query_one("#tag_table", DataTable)
        if not table.rows or not self._data:
            return None
        try:
            cursor = table.cursor_row
            if cursor is None or cursor < 0 or cursor >= len(self._data):
                return None
            row_key = table.coordinate_to_cell_key((cursor, 0)).row_key
            cells = table.get_row(row_key)
            return int(cells[0])
        except Exception:
            return None

    def action_add_tag(self):
        def on_save():
            self.load_data()
        self.app.push_screen(TagFormScreen(on_save=on_save))

    def action_edit_selected(self):
        tid = self._get_selected_id()
        if tid is None:
            self.app.push_screen(MessageBox("No tag selected.", "Info"))
            return
        def on_save():
            self.load_data()
        self.app.push_screen(TagFormScreen(tag_id=tid, on_save=on_save))

    def action_delete_selected(self):
        tid = self._get_selected_id()
        if tid is None:
            self.app.push_screen(MessageBox("No tag selected.", "Info"))
            return
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_delete(f"/metadata/tags/{tid}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
        self.app.push_screen(ConfirmBox("Delete this tag?", "Confirm"), on_confirm)

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()


class TagFormScreen(Screen):
    """Add or edit a tag."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, tag_id=None, on_save=None, **kwargs):
        self.tag_id = tag_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        title = "EDIT TAG" if self.tag_id else "ADD TAG"
        with Container(classes="main_panel center_screen"):
            yield Label(title, classes="menu_header")
            yield Rule()
            yield Label("Name:")
            yield Input(placeholder="Tag name", id="tag_name")
            yield Label("Color (optional):")
            yield Select(
                [("None", None), ("Red", "red"), ("Green", "green"),
                 ("Blue", "blue"), ("Yellow", "yellow"), ("Purple", "purple"),
                 ("Orange", "orange"), ("Cyan", "cyan")],
                value=None, id="tag_color", allow_blank=False,
            )
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        if self.tag_id:
            resp = api_get(f"/metadata/tags/{self.tag_id}", username=self.app.user.get("username"))
            data, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
                return
            self.query_one("#tag_name", Input).value = data.get("name", "")
            self.query_one("#tag_color", Select).value = data.get("color")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        name = self.query_one("#tag_name", Input).value.strip()
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        payload = {"name": name}
        color = self.query_one("#tag_color", Select).value
        if color:
            payload["color"] = color
        if self.tag_id:
            resp = api_put(f"/metadata/tags/{self.tag_id}", payload, username=self.app.user.get("username"))
        else:
            resp = api_post("/metadata/tags", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()


# ── Label Management ────────────────────────────────────────────────

class LabelListScreen(Screen):
    """List and manage labels."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "add_label", "Add"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("LABELS", classes="menu_header")
            yield Rule()
            yield DataTable(id="label_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[A] Add  [E] Edit  [D] Delete  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("A=Add  E=Edit  D=Delete  R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#label_table", DataTable)
        table.add_columns("ID", "Name", "Color", "Transactions", "Wallets")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._data = []
        self.load_data()

    def load_data(self):
        table = self.query_one("#label_table", DataTable)
        table.clear()
        resp = api_get("/metadata/labels", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = data or []
        if not self._data:
            table.add_row("-", "No labels found", "-", "-", "-")
        else:
            for lb in self._data:
                table.add_row(
                    str(lb["id"]),
                    lb.get("name", ""),
                    lb.get("color") or "-",
                    str(lb.get("transaction_count", 0)),
                    str(lb.get("wallet_count", 0)),
                )

    def _get_selected_id(self):
        table = self.query_one("#label_table", DataTable)
        if not table.rows or not self._data:
            return None
        try:
            cursor = table.cursor_row
            if cursor is None or cursor < 0 or cursor >= len(self._data):
                return None
            row_key = table.coordinate_to_cell_key((cursor, 0)).row_key
            cells = table.get_row(row_key)
            return int(cells[0])
        except Exception:
            return None

    def action_add_label(self):
        def on_save():
            self.load_data()
        self.app.push_screen(LabelFormScreen(on_save=on_save))

    def action_edit_selected(self):
        lid = self._get_selected_id()
        if lid is None:
            self.app.push_screen(MessageBox("No label selected.", "Info"))
            return
        def on_save():
            self.load_data()
        self.app.push_screen(LabelFormScreen(label_id=lid, on_save=on_save))

    def action_delete_selected(self):
        lid = self._get_selected_id()
        if lid is None:
            self.app.push_screen(MessageBox("No label selected.", "Info"))
            return
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_delete(f"/metadata/labels/{lid}", username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
        self.app.push_screen(ConfirmBox("Delete this label?", "Confirm"), on_confirm)

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()


class LabelFormScreen(Screen):
    """Add or edit a label."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, label_id=None, on_save=None, **kwargs):
        self.label_id = label_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        title = "EDIT LABEL" if self.label_id else "ADD LABEL"
        with Container(classes="main_panel center_screen"):
            yield Label(title, classes="menu_header")
            yield Rule()
            yield Label("Name:")
            yield Input(placeholder="Label name", id="label_name")
            yield Label("Color (optional):")
            yield Select(
                [("None", None), ("Red", "red"), ("Green", "green"),
                 ("Blue", "blue"), ("Yellow", "yellow"), ("Purple", "purple"),
                 ("Orange", "orange"), ("Cyan", "cyan")],
                value=None, id="label_color", allow_blank=False,
            )
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        if self.label_id:
            resp = api_get(f"/metadata/labels/{self.label_id}", username=self.app.user.get("username"))
            data, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
                return
            self.query_one("#label_name", Input).value = data.get("name", "")
            self.query_one("#label_color", Select).value = data.get("color")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        name = self.query_one("#label_name", Input).value.strip()
        if not name:
            self.app.push_screen(MessageBox("Name is required", "Validation"))
            return
        payload = {"name": name}
        color = self.query_one("#label_color", Select).value
        if color:
            payload["color"] = color
        if self.label_id:
            resp = api_put(f"/metadata/labels/{self.label_id}", payload, username=self.app.user.get("username"))
        else:
            resp = api_post("/metadata/labels", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            if self.on_save:
                self.on_save()
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()
