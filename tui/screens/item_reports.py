"""Item-level analytics and inflation TUI screens."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Rule, Static

from tui.api import api_get, format_toman, handle_response
from tui.widgets import HelpTip, StatusBar


# ── Menu Screen ───────────────────────────────────────────────────────

class ItemReportsScreen(Screen):
    """Item analytics menu."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_top", "Top Items"),
        Binding("2", "do_velocity", "Velocity"),
        Binding("3", "do_inflation", "Inflation"),
        Binding("4", "do_prices", "Price Compare"),
        Binding("5", "do_spikes", "Spikes"),
        Binding("6", "do_basket", "Basket"),
        Binding("7", "do_best", "Best Stores"),
    ]

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("ITEM ANALYTICS", classes="menu_header")
            yield Rule()
            yield ListView(
                ListItem(Label("1. Top Purchased Items")),
                ListItem(Label("2. Spending Velocity")),
                ListItem(Label("3. Personal Inflation Tracker")),
                ListItem(Label("4. Price Comparison by Store")),
                ListItem(Label("5. Price Spike Alerts")),
                ListItem(Label("6. Monthly Item Basket")),
                ListItem(Label("7. Best Store per Item")),
                ListItem(Label("8. Back")),
                id="item_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-7] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        actions = [
            self.action_do_top,
            self.action_do_velocity,
            self.action_do_inflation,
            self.action_do_prices,
            self.action_do_spikes,
            self.action_do_basket,
            self.action_do_best,
            self.action_go_back,
        ]
        idx = event.list_view.index
        if 0 <= idx < len(actions):
            actions[idx]()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_top(self):
        self.app.push_screen(ItemReportViewScreen("top"))

    def action_do_velocity(self):
        self.app.push_screen(ItemReportViewScreen("velocity"))

    def action_do_inflation(self):
        self.app.push_screen(ItemReportViewScreen("inflation"))

    def action_do_prices(self):
        self.app.push_screen(ItemReportViewScreen("prices"))

    def action_do_spikes(self):
        self.app.push_screen(ItemReportViewScreen("spikes"))

    def action_do_basket(self):
        self.app.push_screen(ItemReportViewScreen("basket"))

    def action_do_best(self):
        self.app.push_screen(ItemReportViewScreen("best"))


# ── Detail View Screen ───────────────────────────────────────────────

_REPORT_VIEWS = ["top", "velocity", "inflation", "prices", "spikes", "basket", "best"]

_REPORT_LABELS = {
    "top": "TOP PURCHASED ITEMS",
    "velocity": "SPENDING VELOCITY",
    "inflation": "PERSONAL INFLATION",
    "prices": "PRICE COMPARISON",
    "spikes": "PRICE SPIKE ALERTS",
    "basket": "MONTHLY BASKET",
    "best": "BEST STORE PER ITEM",
}


class ItemReportViewScreen(Screen):
    """Item report detail view with multiple report types."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("tab", "next_view", "Next"),
        Binding("shift+tab", "prev_view", "Previous"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, report_type="top", **kwargs):
        self._report_type = report_type
        self._data = None
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        if not getattr(self, "_sidebar_embedded", False):
            yield Header()
        with Container(classes="wide_panel center_screen"):
            yield Label(_REPORT_LABELS.get(self._report_type, "ITEM REPORT"), classes="menu_header", id="report_title")
            yield Rule()
            with VerticalScroll(classes="report_scroll"):
                yield Static("Loading...", id="report_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Tab] Next report  [Shift+Tab] Previous  [R] Refresh  [Esc] Back", id="help")
            yield StatusBar(f"View: {self._report_type}  |  Tab=Switch  R=Refresh  Esc=Back", id="status")
        if not getattr(self, "_sidebar_embedded", False):
            yield Footer()

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self):
        content = self.query_one("#report_content", Static)
        content.update("Loading...")

        username = self.app.user.get("username")

        if self._report_type == "top":
            self._load_top(username)
        elif self._report_type == "velocity":
            self._load_velocity(username)
        elif self._report_type == "inflation":
            self._load_inflation(username)
        elif self._report_type == "prices":
            self._load_prices(username)
        elif self._report_type == "spikes":
            self._load_spikes(username)
        elif self._report_type == "basket":
            self._load_basket(username)
        elif self._report_type == "best":
            self._load_best(username)

    def _show_report(self, lines):
        content = self.query_one("#report_content", Static)
        content.update("\n".join(lines))

    # ── Top Purchased Items ───────────────────────────────────────

    def _load_top(self, username):
        resp = api_get("/reports/items/top", params={"limit": 15}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["No item data found. Add items to transactions first."])
            return

        w = 90
        lines = []
        lines.append("TOP PURCHASED ITEMS")
        lines.append("\u2500" * w)
        lines.append(
            f"{'Item':<20} {'Qty':>8} {'Spent':>15} {'Count':>7} {'Avg Price':>14} {'Last Price':>14}"
        )
        lines.append("\u2500" * w)
        for item in data:
            name = (item["item_name"] or "")[:20]
            lines.append(
                f"{name:<20} "
                f"{item['total_quantity']:>8.1f} "
                f"{format_toman(item['total_spent']):>15} "
                f"{item['purchase_count']:>7} "
                f"{format_toman(item['avg_price']):>14} "
                f"{format_toman(item['last_price']):>14}"
            )
        lines.append("\u2500" * w)
        lines.append(f"Total items tracked: {len(data)}")
        self._show_report(lines)

    # ── Spending Velocity ─────────────────────────────────────────

    def _load_velocity(self, username):
        resp = api_get("/reports/items/velocity", params={"min_purchases": 2}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["Not enough purchase history for velocity analysis."])
            return

        w = 90
        lines = []
        lines.append("SPENDING VELOCITY (Consumption Speed)")
        lines.append("\u2500" * w)
        lines.append(
            f"{'Item':<20} {'Count':>6} {'Avg Days':>9} {'Last Purchased':>16} {'Next Predicted':>16} {'Monthly Est':>14}"
        )
        lines.append("\u2500" * w)
        for item in data:
            name = (item["item_name"] or "")[:20]
            avg_days = f"{item['avg_days_between']:.1f}" if item["avg_days_between"] else "-"
            predicted = item.get("predicted_next_date") or "-"
            lines.append(
                f"{name:<20} "
                f"{item['purchase_count']:>6} "
                f"{avg_days:>9} "
                f"{item['last_purchase_date']:>16} "
                f"{predicted:>16} "
                f"{format_toman(item['monthly_estimated_cost']):>14}"
            )
        lines.append("\u2500" * w)
        total_monthly = sum(i["monthly_estimated_cost"] for i in data)
        lines.append(f"Estimated monthly recurring cost: {format_toman(total_monthly)}")
        self._show_report(lines)

    # ── Personal Inflation ────────────────────────────────────────

    def _load_inflation(self, username):
        resp = api_get("/reports/inflation/personal", params={"period_months": 3, "min_purchases": 1}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return

        items = data.get("items", [])
        if not items:
            self._show_report(["Not enough data for inflation tracking. Need purchases in multiple months."])
            return

        w = 78
        lines = []
        lines.append("PERSONAL INFLATION TRACKER")
        lines.append("\u2500" * w)
        lines.append(
            f"{'Item':<20} {'Avg Price (T0)':>16} {'Current (T1)':>16} {'Change':>10} {'Weight':>8}"
        )
        lines.append("\u2500" * w)

        for item in items:
            name = (item["item_name"] or "")[:20]
            rate = item["inflation_rate"]
            sign = "+" if rate >= 0 else ""
            color = "red" if rate > 0.1 else ("yellow" if rate > 0.05 else "green")
            lines.append(
                f"{name:<20} "
                f"{format_toman(item['avg_price_t0']):>16} "
                f"{format_toman(item['avg_price_t1']):>16} "
                f"[{color}]{sign}{rate * 100:>7.1f}%[/{color}] "
                f"{item['weight'] * 100:>7.1f}%"
            )

        lines.append("\u2500" * w)
        cpi = data.get("personal_cpi", 0)
        sign = "+" if cpi >= 0 else ""
        color = "red" if cpi > 0.1 else ("yellow" if cpi > 0.05 else "green")
        lines.append(f"[bold]Weighted Personal Inflation: [{color}]{sign}{cpi * 100:.1f}%[/{color}][/bold]")
        lines.append(f"Items tracked: {data.get('total_items_tracked', 0)}  |  Period: {data.get('period_months', 3)} months")

        # Check for spikes
        resp2 = api_get("/reports/inflation/spikes", params={"threshold": 0.2, "lookback_months": 3}, username=username)
        spikes, _ = handle_response(resp2)
        if spikes:
            lines.append("")
            lines.append("[bold red]PRICE SPIKE ALERTS (>20% above average):[/bold red]")
            lines.append("\u2500" * w)
            for s in spikes[:5]:
                name = (s["item_name"] or "")[:20]
                pct = s["change_pct"] * 100
                lines.append(
                    f"  [red]\u26a0[/red]  {name:<20} avg: {format_toman(s['avg_price']):>12}  "
                    f"now: {format_toman(s['latest_price']):>12}  [red]+{pct:.1f}%[/red]"
                )

        self._show_report(lines)

    # ── Price Comparison ──────────────────────────────────────────

    def _load_prices(self, username):
        resp = api_get("/reports/items/price-comparison", username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["No price comparison data available."])
            return

        w = 78
        lines = []
        lines.append("PRICE COMPARISON BY STORE")
        lines.append("\u2500" * w)
        lines.append(
            f"{'Item':<20} {'Store':<16} {'Avg':>12} {'Min':>12} {'Max':>12} {'Count':>6}"
        )
        lines.append("\u2500" * w)

        current_item = None
        for row in data:
            name = (row["item_name"] or "")[:20]
            wallet = (row["wallet_name"] or "")[:16]
            if current_item and current_item != name:
                lines.append("\u2500" * w)
            current_item = name
            lines.append(
                f"{name:<20} "
                f"{wallet:<16} "
                f"{format_toman(row['avg_price']):>12} "
                f"{format_toman(row['min_price']):>12} "
                f"{format_toman(row['max_price']):>12} "
                f"{row['purchase_count']:>6}"
            )

        self._show_report(lines)

    # ── Price Spikes ──────────────────────────────────────────────

    def _load_spikes(self, username):
        resp = api_get("/reports/inflation/spikes", params={"threshold": 0.15, "lookback_months": 3}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["No price spikes detected. All prices are within normal range."])
            return

        w = 78
        lines = []
        lines.append("PRICE SPIKE ALERTS (>15% above average)")
        lines.append("\u2500" * w)
        lines.append(
            f"{'Item':<20} {'Average':>14} {'Latest':>14} {'Date':>12} {'Change':>10}"
        )
        lines.append("\u2500" * w)
        for s in data:
            name = (s["item_name"] or "")[:20]
            pct = s["change_pct"] * 100
            lines.append(
                f"[red]\u26a0[/red] {name:<19} "
                f"{format_toman(s['avg_price']):>14} "
                f"{format_toman(s['latest_price']):>14} "
                f"{s['latest_date']:>12} "
                f"[red]+{pct:.1f}%[/red]"
            )
        lines.append("\u2500" * w)
        lines.append(f"Items with price spikes: {len(data)}")
        self._show_report(lines)

    # ── Monthly Basket ────────────────────────────────────────────

    def _load_basket(self, username):
        resp = api_get("/reports/items/monthly-basket", params={"months": 3}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["No basket data available."])
            return

        w = 78
        lines = []
        lines.append("MONTHLY ITEM BASKET (last 3 months)")
        lines.append("\u2500" * w)

        current_month = None
        month_total = 0
        for row in data:
            month = row["month"]
            if month != current_month:
                if current_month is not None:
                    lines.append(f"  {'Month Total:':<30} {format_toman(month_total):>14}")
                    lines.append("")
                current_month = month
                month_total = 0
                lines.append(f"[bold]{month}[/bold]")
                lines.append(f"  {'Item':<20} {'Qty':>8} {'Avg Price':>14} {'Cost':>14}")
                lines.append("  " + "\u2500" * 60)

            name = (row["item_name"] or "")[:20]
            lines.append(
                f"  {name:<20} "
                f"{row['total_quantity']:>8.1f} "
                f"{format_toman(row['avg_price']):>14} "
                f"{format_toman(row['monthly_cost']):>14}"
            )
            month_total += row["monthly_cost"]

        if current_month is not None:
            lines.append(f"  {'Month Total:':<30} {format_toman(month_total):>14}")

        self._show_report(lines)

    # ── Best Stores ───────────────────────────────────────────────

    def _load_best(self, username):
        resp = api_get("/reports/items/best-stores", params={"limit": 20}, username=username)
        data, err = handle_response(resp)
        if err:
            self._show_report([f"[red]Error: {err}[/red]"])
            return
        if not data:
            self._show_report(["No store comparison data available."])
            return

        w = 60
        lines = []
        lines.append("BEST STORE PER ITEM (lowest avg price)")
        lines.append("\u2500" * w)
        lines.append(f"{'Item':<20} {'Best Store':<16} {'Avg Price':>14} {'Visits':>8}")
        lines.append("\u2500" * w)
        for row in data:
            name = (row["item_name"] or "")[:20]
            wallet = (row["best_wallet"] or "")[:16]
            lines.append(
                f"{name:<20} "
                f"{wallet:<16} "
                f"{format_toman(row['avg_price']):>14} "
                f"{row['purchase_count']:>8}"
            )
        lines.append("\u2500" * w)
        self._show_report(lines)

    # ── Navigation ────────────────────────────────────────────────

    def action_next_view(self):
        idx = _REPORT_VIEWS.index(self._report_type)
        self._report_type = _REPORT_VIEWS[(idx + 1) % len(_REPORT_VIEWS)]
        self._update_title()
        self.load_data()

    def action_prev_view(self):
        idx = _REPORT_VIEWS.index(self._report_type)
        self._report_type = _REPORT_VIEWS[(idx - 1) % len(_REPORT_VIEWS)]
        self._update_title()
        self.load_data()

    def _update_title(self):
        try:
            title = self.query_one("#report_title", Label)
            title.update(_REPORT_LABELS.get(self._report_type, "ITEM REPORT"))
            status = self.query_one("#status", StatusBar)
            status.update(f"View: {self._report_type}  |  Tab=Switch  R=Refresh  Esc=Back")
        except Exception:
            pass

    def action_refresh(self):
        self.load_data()

    def action_go_back(self):
        self.app.pop_screen()
