"""Debt & Receivable TUI screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Checkbox, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Select, Static, Rule, TextArea,
)

from tui.api import api_get, api_post, api_put, api_delete, extract_items, handle_response, format_toman
from tui.jalali_date_picker import JalaliDatePicker
from tui.widgets import ConfirmBox, HelpTip, MessageBox, StatusBar


# ── Main Menu ───────────────────────────────────────────────────────

class DebtMenuScreen(Screen):
    """Debt management menu."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_dashboard", "Dashboard"),
        Binding("2", "do_list", "List"),
        Binding("3", "do_add", "Add"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("DEBTS & RECEIVABLES", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. Dashboard")),
                ListItem(Label("2. List Debts")),
                ListItem(Label("3. Add Debt")),
                ListItem(Label("4. Back to Main Menu")),
                id="debt_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-3] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_do_dashboard()
        elif idx == 1:
            self.action_do_list()
        elif idx == 2:
            self.action_do_add()
        else:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_dashboard(self):
        self.app.push_screen(DebtDashboardScreen())

    def action_do_list(self):
        self.app.push_screen(DebtListScreen())

    def action_do_add(self):
        self.app.push_screen(DebtAddScreen())


# ── Dashboard ───────────────────────────────────────────────────────

class DebtDashboardScreen(Screen):
    """Debt overview dashboard."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("DEBT DASHBOARD", classes="menu_header")
            yield Rule()
            yield Static("Loading...", id="dash_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[R] Refresh  [Esc] Back", id="help")
            yield StatusBar("R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self):
        username = self.app.user.get("username")
        resp = api_get("/debts/summary", username=username)
        data, err = handle_response(resp)
        if err:
            self._show([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show(["No debt data available."])
            return

        lines = []
        w = 70

        lines.append("OVERVIEW")
        lines.append("\u2500" * w)
        lines.append(
            f"  {'Total Receivables:':<30} [green]{format_toman(data.get('receivable_total', 0)):>15}[/green]"
        )
        lines.append(
            f"  {'Total Payables:':<30} [red]{format_toman(data.get('payable_total', 0)):>15}[/red]"
        )
        net = data.get("net_position", 0)
        color = "green" if net >= 0 else "red"
        lines.append(
            f"  {'Net Position:':<30} [{color}]{format_toman(net):>15}[/{color}]"
        )
        lines.append("")

        lines.append("ALERTS")
        lines.append("\u2500" * w)
        overdue_count = data.get("overdue_count", 0)
        overdue_amount = data.get("overdue_amount", 0)
        if overdue_count > 0:
            lines.append(
                f"  [red]\u26a0[/red]  {overdue_count} overdue debt(s) totaling {format_toman(overdue_amount)}"
            )
        else:
            lines.append("  [green]\u2713[/green]  No overdue debts")

        due_soon = data.get("due_soon", {})
        due_count = due_soon.get("count", 0)
        due_total = due_soon.get("total", 0)
        if due_count > 0:
            lines.append(
                f"  [yellow]\u26a0[/yellow]  {due_count} debt(s) due within 7 days: {format_toman(due_total)}"
            )
        lines.append("")

        # Recent payments
        recent = data.get("recent_payments", [])
        if recent:
            lines.append("RECENT PAYMENTS")
            lines.append("\u2500" * w)
            for p in recent:
                cp = (p.get("counterparty_name") or "")[:15]
                ptype = "IN" if p.get("type") == "receivable" else "OUT"
                color = "green" if ptype == "IN" else "red"
                lines.append(
                    f"  [{color}]{ptype}[/{color}]  {format_toman(p['amount']):>14}  "
                    f"{p.get('payment_date', ''):<12} {cp:<15} {(p.get('title') or '')[:20]}"
                )

        self._show(lines)

    def _show(self, lines):
        self.query_one("#dash_content", Static).update("\n".join(lines))

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()


# ── Debt List ───────────────────────────────────────────────────────

class DebtListScreen(Screen):
    """List debts with filtering."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("v", "view_selected", "View"),
        Binding("p", "pay_selected", "Pay"),
        Binding("f", "apply_filter", "Filter"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("DEBT LIST", classes="menu_header")
            yield Rule()
            with Horizontal(classes="filter_row"):
                yield Select(
                    [("All", "all"), ("Receivable", "receivable"), ("Payable", "payable")],
                    value="all", id="debt_filter_type", allow_blank=False,
                )
                yield Select(
                    [
                        ("All Status", "all"),
                        ("Active", "active"),
                        ("Partially Paid", "partially_paid"),
                        ("Overdue", "overdue"),
                        ("Settled", "settled"),
                        ("Cancelled", "cancelled"),
                        ("Written Off", "written_off"),
                    ],
                    value="all", id="debt_filter_status", allow_blank=False,
                )
                yield Input(placeholder="Counterparty", id="debt_filter_cp")
                yield Button("🔍 Filter", variant="primary", id="debt_filter_btn")
                yield Button("🔄 Reset", variant="default", id="debt_reset_btn")
            with Horizontal(classes="split_row"):
                with Vertical(classes="left_pane"):
                    yield DataTable(id="debt_table")
                with Vertical(classes="right_pane"):
                    yield Label("DETAILS", classes="detail_header")
                    yield Rule()
                    yield Static(id="debt_detail")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [V] View  [P] Pay  [F] Filter  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar("V=View  P=Pay  F=Filter  R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#debt_table", DataTable)
        table.add_columns("ID", "Type", "Counterparty", "Title", "Original", "Remaining", "Due", "Status")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._data = []
        self.load_data()

    def load_data(self, params=None):
        table = self.query_one("#debt_table", DataTable)
        table.clear()
        params = dict(params or {})
        resp = api_get("/debts", params=params, username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        self._data = extract_items(data)
        if not self._data:
            table.add_row("-", "-", "-", "No debts found", "-", "-", "-", "-")
        else:
            for d in self._data:
                dtype = "REC" if d["type"] == "receivable" else "PAY"
                table.add_row(
                    str(d["id"]),
                    dtype,
                    (d.get("counterparty_name") or "")[:18],
                    (d.get("title") or "")[:22],
                    format_toman(d.get("original_amount", 0)),
                    format_toman(d.get("remaining_amount", 0)),
                    d.get("due_date") or "-",
                    d.get("status", ""),
                )
        self.update_detail()

    def update_detail(self):
        detail = self.query_one("#debt_detail", Static)
        debt_id = self._get_selected_id()
        if debt_id is None:
            detail.update("Select a debt to see details.")
            return
        d = next((x for x in self._data if x["id"] == debt_id), None)
        if d is None:
            detail.update("Select a debt to see details.")
            return
        dtype = "Receivable" if d["type"] == "receivable" else "Payable"
        detail.update(
            f"[b]ID:[/b]            {d['id']}\n"
            f"[b]Type:[/b]          {dtype}\n"
            f"[b]Counterparty:[/b]  {d.get('counterparty_name', '')}\n"
            f"[b]CP Type:[/b]       {d.get('counterparty_type', '')}\n"
            f"[b]Title:[/b]         {d.get('title', '')}\n"
            f"[b]Original:[/b]      {format_toman(d.get('original_amount', 0))}\n"
            f"[b]Remaining:[/b]     {format_toman(d.get('remaining_amount', 0))}\n"
            f"[b]Issue Date:[/b]    {d.get('issue_date', '')}\n"
            f"[b]Due Date:[/b]      {d.get('due_date') or 'None'}\n"
            f"[b]Status:[/b]        {d.get('status', '')}\n"
            f"[b]Priority:[/b]      {d.get('priority', '')}\n"
            f"[b]Payments:[/b]      {d.get('payment_count', 0)}\n"
            f"[b]Total Paid:[/b]    {format_toman(d.get('total_paid', 0))}\n"
            f"[b]Notes:[/b]         {(d.get('description') or '-')[:40]}\n"
        )

    def on_data_table_row_highlighted(self, event):
        self.update_detail()

    def _get_selected_id(self):
        table = self.query_one("#debt_table", DataTable)
        if not table.rows:
            return None
        cursor = table.cursor_row
        if cursor is None or cursor < 0 or cursor >= len(self._data):
            return None
        try:
            row_key = table.coordinate_to_cell_key((cursor, 0)).row_key
            cells = table.get_row(row_key)
            return int(cells[0])
        except Exception:
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "debt_filter_btn":
            self.action_apply_filter()
        elif event.button.id == "debt_reset_btn":
            self.action_reset_filter()

    def action_apply_filter(self):
        params = {}
        dtype = self.query_one("#debt_filter_type", Select).value
        status = self.query_one("#debt_filter_status", Select).value
        cp = self.query_one("#debt_filter_cp", Input).value.strip()
        if dtype not in (None, "all"):
            params["type"] = dtype
        if status not in (None, "all"):
            params["status"] = status
        if cp:
            params["counterparty"] = cp
        self.load_data(params=params)

    def action_reset_filter(self):
        self.query_one("#debt_filter_type", Select).value = "all"
        self.query_one("#debt_filter_status", Select).value = "all"
        self.query_one("#debt_filter_cp", Input).value = ""
        self.load_data()

    def action_view_selected(self):
        debt_id = self._get_selected_id()
        if debt_id is None:
            self.app.push_screen(MessageBox("No debt selected.", "Info"))
            return

        def on_save():
            self.load_data()

        self.app.push_screen(DebtDetailScreen(debt_id, on_save=on_save))

    def action_pay_selected(self):
        debt_id = self._get_selected_id()
        if debt_id is None:
            self.app.push_screen(MessageBox("No debt selected.", "Info"))
            return
        d = next((x for x in self._data if x["id"] == debt_id), None)
        if d is None:
            return
        if d["status"] in ("settled", "cancelled", "written_off"):
            self.app.push_screen(MessageBox(f"Cannot pay a {d['status']} debt.", "Info"))
            return

        def on_save():
            self.load_data()

        self.app.push_screen(DebtPaymentScreen(debt_id, d.get("remaining_amount", 0), on_save=on_save))

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()


# ── Debt Detail ─────────────────────────────────────────────────────

class DebtDetailScreen(Screen):
    """View a single debt with payment history and actions."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("p", "add_payment", "Pay"),
        Binding("w", "write_off", "Write Off"),
        Binding("c", "cancel", "Cancel"),
        Binding("s", "settle", "Settle"),
    ]

    def __init__(self, debt_id, on_save=None, **kwargs):
        self.debt_id = debt_id
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label("DEBT DETAILS", classes="menu_header")
            yield Rule()
            yield Static("Loading...", id="detail_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[P] Pay  [W] Write Off  [C] Cancel  [S] Settle  [Esc] Back", id="help")
            yield StatusBar("P=Pay  W=Write Off  C=Cancel  S=Settle  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self):
        username = self.app.user.get("username")
        resp = api_get(f"/debts/{self.debt_id}", username=username)
        debt, err = handle_response(resp)
        if err:
            self._show([f"[red]Error: {err}[/red]"])
            return

        resp2 = api_get(f"/debts/{self.debt_id}/payments", username=username)
        payments, _ = handle_response(resp2)

        resp3 = api_get(f"/debts/{self.debt_id}/history", username=username)
        history, _ = handle_response(resp3)

        lines = []
        w = 70

        dtype = "Receivable (money owed TO you)" if debt["type"] == "receivable" else "Payable (money you owe)"
        status = debt.get("status", "")
        status_color = {
            "active": "green", "partially_paid": "yellow", "overdue": "red",
            "settled": "green", "cancelled": "dim", "written_off": "dim",
        }.get(status, "white")

        lines.append(f"[bold]{debt.get('title', '')}[/bold]")
        lines.append("\u2500" * w)
        lines.append(f"  Type:          {dtype}")
        lines.append(f"  Counterparty:  {debt.get('counterparty_name', '')} ({debt.get('counterparty_type', '')})")
        lines.append(f"  Status:        [{status_color}]{status.upper()}[/{status_color}]")
        lines.append(f"  Priority:      {debt.get('priority', 'normal')}")
        lines.append(f"  Issue Date:    {debt.get('issue_date', '')}")
        lines.append(f"  Due Date:      {debt.get('due_date') or 'No due date'}")
        lines.append("")
        lines.append(
            f"  Original:      {format_toman(debt.get('original_amount', 0))}"
        )
        lines.append(
            f"  Remaining:     {format_toman(debt.get('remaining_amount', 0))}"
        )
        lines.append(
            f"  Paid:          {format_toman(debt.get('total_paid', 0))}"
        )

        # Progress bar
        orig = float(debt.get("original_amount", 1))
        rem = float(debt.get("remaining_amount", 0))
        pct = ((orig - rem) / orig * 100) if orig > 0 else 0
        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
        lines.append(f"  Progress:      [{bar}] {pct:.0f}%")

        if debt.get("has_interest"):
            lines.append(f"  Interest:      {debt.get('interest_type', '')} @ {debt.get('interest_rate', 0)}%")
        if debt.get("description"):
            lines.append(f"  Notes:         {debt['description']}")
        lines.append("")

        # Payment history
        if payments:
            lines.append("PAYMENT HISTORY")
            lines.append("\u2500" * w)
            lines.append(f"  {'Date':<14} {'Amount':>14} {'Method':<10} {'Note'}")
            lines.append("  " + "\u2500" * 56)
            total_paid = 0
            for p in payments:
                lines.append(
                    f"  {p.get('payment_date', ''):<14} "
                    f"{format_toman(p['amount']):>14} "
                    f"{(p.get('payment_method') or 'cash'):<10} "
                    f"{(p.get('note') or '-')[:25]}"
                )
                total_paid += float(p["amount"])
            lines.append("  " + "\u2500" * 56)
            lines.append(f"  {'Total:':<14} {format_toman(total_paid):>14}")
        else:
            lines.append("No payments recorded yet.")

        # Status history
        if history:
            lines.append("")
            lines.append("STATUS HISTORY")
            lines.append("\u2500" * w)
            for h in history:
                old = h.get("old_status") or "created"
                new = h.get("new_status", "")
                lines.append(
                    f"  {h.get('changed_at', '')[:16]}  {old} -> {new}  {(h.get('note') or '')[:25]}"
                )

        self._show(lines)

    def _show(self, lines):
        self.query_one("#detail_content", Static).update("\n".join(lines))

    def action_add_payment(self):
        resp = api_get(f"/debts/{self.debt_id}", username=self.app.user.get("username"))
        debt, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        if debt["status"] in ("settled", "cancelled", "written_off"):
            self.app.push_screen(MessageBox(f"Cannot pay a {debt['status']} debt.", "Info"))
            return

        def on_pay():
            self.load_data()
            if self.on_save:
                self.on_save()

        self.app.push_screen(DebtPaymentScreen(self.debt_id, debt.get("remaining_amount", 0), on_save=on_pay))

    def action_write_off(self):
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_post(f"/debts/{self.debt_id}/write-off", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
                if self.on_save:
                    self.on_save()

        self.app.push_screen(ConfirmBox("Write off this debt as uncollectible?", "Write Off"), on_confirm)

    def action_cancel(self):
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_post(f"/debts/{self.debt_id}/cancel", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
                if self.on_save:
                    self.on_save()

        self.app.push_screen(ConfirmBox("Cancel this debt?", "Cancel"), on_confirm)

    def action_settle(self):
        def on_confirm(confirmed):
            if not confirmed:
                return
            resp = api_post(f"/debts/{self.debt_id}/settle", {}, username=self.app.user.get("username"))
            _, err = handle_response(resp)
            if err:
                self.app.push_screen(MessageBox(err, "Error"))
            else:
                self.load_data()
                if self.on_save:
                    self.on_save()

        self.app.push_screen(ConfirmBox("Manually mark this debt as settled?", "Settle"), on_confirm)

    def action_go_back(self):
        self.app.pop_screen()


# ── Add Debt Form ───────────────────────────────────────────────────

class DebtAddScreen(Screen):
    """Add a new debt or receivable."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("ADD DEBT", classes="menu_header")
            yield Rule()
            with VerticalScroll(classes="form_scroll"):
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Type:")
                        yield Select(
                            [("Receivable (owed to me)", "receivable"),
                             ("Payable (I owe)", "payable")],
                            id="debt_type", allow_blank=False,
                        )
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Priority:")
                        yield Select(
                            [("Normal", "normal"), ("Low", "low"),
                             ("High", "high"), ("Urgent", "urgent")],
                            value="normal", id="debt_priority", allow_blank=False,
                        )
                yield Label("Counterparty Name:")
                yield Input(placeholder="e.g. Ali, Bank Melli", id="debt_cp_name")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Counterparty Type:")
                        yield Select(
                            [("Person", "person"), ("Friend", "friend"),
                             ("Family", "family"), ("Company", "company"),
                             ("Bank", "bank"), ("Merchant", "merchant"),
                             ("Other", "other")],
                            value="person", id="debt_cp_type", allow_blank=False,
                        )
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Wallet Account (optional):")
                        yield Select([], prompt="None", id="debt_wallet")
                yield Label("Title:")
                yield Input(placeholder="Short description", id="debt_title")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Amount:")
                        yield Input(placeholder="1000000", id="debt_amount")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("Issue Date (Jalali):")
                        with Horizontal(classes="date_field_row"):
                            yield Input(placeholder="1405-01-01", id="debt_issue_date")
                            yield Button("\U0001f4c5", id="btn_issue_date_picker", classes="date_picker_btn")
                with Horizontal(classes="form_row"):
                    with Vertical(classes="form_col"):
                        yield Label("Due Date (Jalali, optional):")
                        with Horizontal(classes="date_field_row"):
                            yield Input(placeholder="1405-04-01", id="debt_due_date")
                            yield Button("\U0001f4c5", id="btn_due_date_picker", classes="date_picker_btn")
                    yield Static("", classes="form_col_spacer")
                    with Vertical(classes="form_col"):
                        yield Label("")
                        yield Checkbox("Has Interest", id="debt_has_interest")
                yield Label("Notes (optional):")
                yield TextArea(id="debt_desc")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save")
                yield Button("✖ Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next field  [Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        from datetime import datetime
        import jdatetime
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        self.query_one("#debt_issue_date", Input).value = jalali_now.strftime("%Y-%m-%d")
        self._wallet_options = []
        self.load_wallets()

    def load_wallets(self):
        resp = api_get("/wallets", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            return
        if data:
            self._wallet_options = [(s["name"], s["id"]) for s in extract_items(data)]
            self.query_one("#debt_wallet", Select).set_options(
                [("None", None)] + self._wallet_options
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        debt_type = self.query_one("#debt_type", Select).value
        cp_name = self.query_one("#debt_cp_name", Input).value.strip()
        cp_type = self.query_one("#debt_cp_type", Select).value
        wallet_id = self.query_one("#debt_wallet", Select).value
        title = self.query_one("#debt_title", Input).value.strip()
        amount_str = self.query_one("#debt_amount", Input).value.strip()
        issue_date = self.query_one("#debt_issue_date", Input).value.strip()
        due_date = self.query_one("#debt_due_date", Input).value.strip()
        priority = self.query_one("#debt_priority", Select).value
        has_interest = self.query_one("#debt_has_interest", Checkbox).value
        desc = self.query_one("#debt_desc", TextArea).text.strip()

        if not cp_name:
            self.app.push_screen(MessageBox("Counterparty name is required", "Validation"))
            return
        if not title:
            self.app.push_screen(MessageBox("Title is required", "Validation"))
            return
        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        if not issue_date:
            self.app.push_screen(MessageBox("Issue date is required", "Validation"))
            return

        payload = {
            "type": debt_type,
            "counterparty_name": cp_name,
            "counterparty_type": cp_type,
            "title": title,
            "description": desc or None,
            "original_amount": amount,
            "issue_date": issue_date,
            "priority": priority or "normal",
            "has_interest": has_interest,
        }
        if due_date:
            payload["due_date"] = due_date
        if wallet_id:
            payload["wallet_id"] = wallet_id

        resp = api_post("/debts", payload, username=self.app.user.get("username"))
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Debt created successfully.", "Success"))
            self.query_one("#debt_cp_name", Input).value = ""
            self.query_one("#debt_title", Input).value = ""
            self.query_one("#debt_amount", Input).value = ""
            self.query_one("#debt_due_date", Input).value = ""
            self.query_one("#debt_desc", TextArea).load_text("")

    def action_go_back(self):
        self.app.pop_screen()


# ── Payment Form ────────────────────────────────────────────────────

class DebtPaymentScreen(Screen):
    """Record a payment against a debt."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, debt_id, remaining_amount, on_save=None, **kwargs):
        self.debt_id = debt_id
        self.remaining_amount = float(remaining_amount)
        self.on_save = on_save
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="form_panel center_screen"):
            yield Label("RECORD PAYMENT", classes="menu_header")
            yield Rule()
            yield Static(
                f"Remaining: {format_toman(self.remaining_amount)}",
                id="pay_remaining",
            )
            with VerticalScroll(classes="form_scroll"):
                yield Label("Amount:")
                yield Input(placeholder=str(int(self.remaining_amount)), id="pay_amount")
                yield Label("Payment Date (Jalali):")
                with Horizontal(classes="date_field_row"):
                    yield Input(placeholder="1405-02-19", id="pay_date")
                    yield Button("\U0001f4c5", id="btn_pay_date_picker", classes="date_picker_btn")
                yield Label("Wallet Account (optional):")
                yield Select([], prompt="None", id="pay_wallet")
                yield Label("Note (optional):")
                yield Input(placeholder="e.g. partial payment", id="pay_note")
            with Horizontal(classes="button_row"):
                yield Button("💾 Save", variant="primary", id="save")
                yield Button("✖ Cancel", variant="default", id="cancel")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Enter] Save  [Esc] Cancel", id="help")
            yield StatusBar("Enter=Save  Esc=Cancel", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        from datetime import datetime
        import jdatetime
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        self.query_one("#pay_date", Input).value = jalali_now.strftime("%Y-%m-%d")
        self.load_wallets()

    def load_wallets(self):
        resp = api_get("/wallets", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            return
        if data:
            options = [(s["name"], s["id"]) for s in extract_items(data)]
            self.query_one("#pay_wallet", Select).set_options([("None", None)] + options)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save()
        elif event.button.id == "cancel":
            self.action_go_back()

    def save(self):
        amount_str = self.query_one("#pay_amount", Input).value.strip()
        pay_date = self.query_one("#pay_date", Input).value.strip()
        wallet_id = self.query_one("#pay_wallet", Select).value
        note = self.query_one("#pay_note", Input).value.strip()

        if not amount_str:
            self.app.push_screen(MessageBox("Amount is required", "Validation"))
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.app.push_screen(MessageBox("Invalid amount", "Validation"))
            return
        if not pay_date:
            self.app.push_screen(MessageBox("Payment date is required", "Validation"))
            return

        payload = {
            "amount": amount,
            "payment_date": pay_date,
            "payment_method": "cash",
        }
        if wallet_id:
            payload["wallet_id"] = wallet_id
        if note:
            payload["note"] = note

        resp = api_post(
            f"/debts/{self.debt_id}/payments",
            payload,
            username=self.app.user.get("username"),
        )
        _, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
        else:
            self.app.push_screen(MessageBox("Payment recorded successfully.", "Success"))
            if self.on_save:
                self.on_save()
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()
