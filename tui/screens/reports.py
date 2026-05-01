"""Advanced report screens."""

from datetime import datetime, timedelta

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from tui.api import api_get, format_toman, handle_response
from tui.widgets import HelpTip, MessageBox, StatusBar


class ReportsScreen(Screen):
    """Reports menu."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_advanced", "Dashboard"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel center_screen"):
            yield Label("REPORTS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Daily / Weekly / Monthly Dashboard")),
                ListItem(Label("2. Back to Main Menu")),
                id="rep_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1] Dashboard  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index == 0:
            self.action_do_advanced()
        else:
            self.action_go_back()

    def action_do_advanced(self):
        self.app.push_screen(AdvancedReportScreen())

    def action_go_back(self):
        self.app.pop_screen()


class AdvancedReportScreen(Screen):
    """Daily / Weekly / Monthly reporting dashboard."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("tab", "next_view", "Next View"),
        Binding("shift+tab", "prev_view", "Prev View"),
        Binding("left", "prev_period", "Prev Period"),
        Binding("right", "next_period", "Next Period"),
        Binding("enter", "open_category_details", "Details"),
        Binding("f", "filter_category", "Filter"),
        Binding("s", "sort_rows", "Sort"),
        Binding("b", "jump_budget", "Budget"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        current = jdatetime.date.fromgregorian(date=datetime.now().date())
        self._view = "monthly"
        self._daily_date = current
        self._weekly_start = current - timedelta(days=6)
        self._monthly_year = current.year
        self._monthly_month = current.month
        self._filter_text = ""
        self._sort_mode = "actual_desc"
        self._report_data = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="wide_panel center_screen"):
            yield Label("ADVANCED REPORTS", classes="menu_header")
            yield Static(id="report_title")
            yield Static(id="report_body")
        with Vertical(classes="bottom_bar"):
            yield HelpTip(
                "[←/→] Period  [Tab] View  [Enter] Details  [F] Filter  [S] Sort  [B] Budget  [Esc] Back",
                id="help",
            )
            yield StatusBar("Advanced financial reporting dashboard", id="status")
        yield Footer()

    def on_mount(self):
        self.load_report()

    def load_report(self):
        if self._view == "daily":
            params = {"date": self._daily_date.strftime("%Y-%m-%d")}
            resp = api_get("/reports/daily", params=params, username=self.app.user.get("username"))
        elif self._view == "weekly":
            params = {"start_date": self._weekly_start.strftime("%Y-%m-%d")}
            resp = api_get("/reports/weekly", params=params, username=self.app.user.get("username"))
        else:
            params = {"year": self._monthly_year, "month": self._monthly_month}
            resp = api_get("/reports/monthly", params=params, username=self.app.user.get("username"))

        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return

        self._report_data = data
        self.render_report()

    def render_report(self):
        title = self.query_one("#report_title", Static)
        body = self.query_one("#report_body", Static)

        if self._view == "daily":
            title.update(f"Daily Report — {self._report_data.get('date', '')}")
            body.update(self._render_daily())
        elif self._view == "weekly":
            title.update(
                f"Weekly Report — {self._report_data.get('start_date', '')} → {self._report_data.get('end_date', '')}"
            )
            body.update(self._render_weekly())
        else:
            title.update(f"Monthly Report — {self._report_data.get('month_label', '')}")
            body.update(self._render_monthly())

    @staticmethod
    def _make_row(content: str, total_width: int) -> str:
        inner_width = total_width - 2
        if len(content) > inner_width:
            content = content[:inner_width - 3] + "..."
        padded_content = content.ljust(inner_width)
        return f"│{padded_content}│"

    def _render_daily(self) -> str:
        data = self._report_data or {}
        rows = data.get("category_breakdown", [])
        if self._filter_text:
            rows = [row for row in rows if self._filter_text.lower() in row.get("category_name", "").lower()]
        
        top = data.get("top_spending_category") or {}
        recent = data.get("last_5_transactions", [])
        compare = data.get("comparison_vs_previous_7_days_avg", {})
        budget = data.get("current_month_budget_usage_status", {})

        width = 46

        lines = [
            "┌────────────────────────────────────────────┐",
            self._make_row(f" Income:        {format_toman(data.get('total_income', 0))}", width),
            self._make_row(f" Expenses:      {format_toman(data.get('total_expenses', 0))}", width),
            self._make_row(f" Net:           {format_toman(data.get('net', 0))}", width),
            "├────────────────────────────────────────────┤",
            self._make_row(f" Top Spending:  {top.get('category_name', '-')}", width),
            self._make_row(f" Prev 7d Avg:   {format_toman(compare.get('previous_7_day_avg_expense', 0))}", width),
            self._make_row(f" Budget Used:   {budget.get('percent_consumed', 0):.1f}%", width),
            "├────────────────────────────────────────────┤",
            self._make_row(" Category Breakdown", width),
            self._make_row("-" * 44, width),
        ]
        
        for row in rows[:6]:
            cat_name = row.get('category_name', '-')
            amount = format_toman(row.get('amount', 0))
            lines.append(self._make_row(f" {cat_name:<14} {amount}", width))
            
        lines.append("├────────────────────────────────────────────┤")
        lines.append(self._make_row(" Last 5 Transactions", width))
        lines.append(self._make_row("-" * 44, width))
        
        for tx in recent[:5]:
            date_str = tx.get('date', '')
            cat_name = str(tx.get('category_name', '-'))[:10]
            amount = format_toman(tx.get('amount', 0))
            lines.append(self._make_row(f" {date_str:<10} {cat_name:<10} {amount}", width))
            
        lines.append("└────────────────────────────────────────────┘")
        
        return "\n".join(lines)

    def _render_weekly(self) -> str:
        data = self._report_data or {}
        rows = data.get("top_5_categories_by_spending", [])
        if self._filter_text:
            rows = [row for row in rows if self._filter_text.lower() in row.get("category_name", "").lower()]
        compare = data.get("comparison_vs_last_week", {})

        width = 62

        lines = [
            "┌────────────────────────────────────────────────────────────┐",
            self._make_row(f" Income:        {format_toman(data.get('total_income', 0))}", width),
            self._make_row(f" Expenses:      {format_toman(data.get('total_expenses', 0))}", width),
            self._make_row(f" Net:           {format_toman(data.get('net', 0))}", width),
            self._make_row(f" Avg Daily Exp: {format_toman(data.get('average_daily_expense', 0))}", width),
            "├────────────────────────────────────────────────────────────┤",
            self._make_row(f" Last Week %:   {round(compare.get('percent_change', 0) or 0, 1)}%", width),
            "├────────────────────────────────────────────────────────────┤",
            self._make_row(" Top 5 Categories", width),
            self._make_row("-" * (width - 2), width),
        ]
        
        for row in rows:
            cat_name = row.get('category_name', '-')
            amount = format_toman(row.get('amount', 0))
            lines.append(self._make_row(f" {cat_name:<14} {amount}", width))
            
        lines.append("├────────────────────────────────────────────────────────────┤")
        lines.append(self._make_row(" ASCII Bar Chart", width))
        lines.append(self._make_row("-" * (width - 2), width))
        
        for chart_line in (data.get("ascii_bar_chart", "") or "No data").splitlines()[:6]:
            lines.append(self._make_row(f" {chart_line}", width))
            
        lines.append("└────────────────────────────────────────────────────────────┘")
        return "\n".join(lines)

    def _render_monthly(self) -> str:
        data = self._report_data or {}
        summary = data.get("summary", {})
        categories = data.get("category_breakdown", [])
        budget_health = data.get("budget_health", {})
        trend = data.get("trend_analysis", {})
        velocity = data.get("spending_velocity", {})
        sources = data.get("source_health", [])
        insights = data.get("smart_insights", [])

        if self._filter_text:
            categories = [
                row for row in categories if self._filter_text.lower() in row.get("category_name", "").lower()
            ]

        if self._sort_mode == "percent_desc":
            categories = sorted(categories, key=lambda item: item.get("percent_used", 0), reverse=True)
        elif self._sort_mode == "planned_desc":
            categories = sorted(categories, key=lambda item: item.get("planned_amount", 0), reverse=True)
        else:
            categories = sorted(categories, key=lambda item: item.get("actual_amount", 0), reverse=True)

        width = 62

        lines = [
            "┌────────────────────────────────────────────────────────────┐",
            self._make_row(f" Income:        {format_toman(summary.get('total_income', 0))}", width),
            self._make_row(f" Expenses:      {format_toman(summary.get('total_expenses', 0))}", width),
            self._make_row(f" Net:           {format_toman(summary.get('net', 0))}", width),
            self._make_row(f" Savings Rate:  {summary.get('savings_rate', 0) * 100:.1f}%", width),
            "├────────────────────────────────────────────────────────────┤",
            self._make_row(" Budget Status", width),
            self._make_row("-" * (width - 2), width),
        ]

        for row in categories[:8]:
            bar = self._progress_bar(row.get("percent_used", 0), 10)
            planned = format_toman(row.get("planned_amount", 0))
            actual = format_toman(row.get("actual_amount", 0))
            percent = f"{row.get('percent_used', 0):>5.0f}%"
            status = row.get("status_indicator", "OK")
            
            row_content = f" {row.get('category_name', '-')[:10]:<10} {planned[:10]:>10} | {actual[:10]:<10} {percent:>5} {bar:<10} {status:<5}"
            lines.append(self._make_row(row_content, width))

        lines.extend(
            [
                "├────────────────────────────────────────────────────────────┤",
                self._make_row(f" Over Budget:   {budget_health.get('categories_over_budget', 0)}", width),
                self._make_row(f" Close Limit:   {budget_health.get('categories_close_to_limit', 0)}", width),
                self._make_row(f" Forecast:      {format_toman(velocity.get('forecast', 0))}", width),
                self._make_row(f" Overrun Risk:  {format_toman(velocity.get('predicted_budget_overrun_amount', 0))}", width),
                "├────────────────────────────────────────────────────────────┤",
                self._make_row(" Source Health", width),
                self._make_row("-" * (width - 2), width),
            ]
        )
        
        for row in sources[:5]:
            source_str = f" {row.get('source_name', '-')[:12]:<12} Δ {format_toman(row.get('balance_change', 0))}"
            lines.append(self._make_row(source_str, width))
            
        lines.append("├────────────────────────────────────────────────────────────┤")
        lines.append(self._make_row(" Smart Insights", width))
        lines.append(self._make_row("-" * (width - 2), width))
        
        for insight in insights[:4]:
            lines.append(self._make_row(f" {insight}", width))
            
        lines.append("└────────────────────────────────────────────────────────────┘")
        lines.append("")
        lines.append(
            f"Trend: Spending {self._fmt_pct(trend.get('spending_change_percent'))} | Income {self._fmt_pct(trend.get('income_change_percent'))}"
        )
        if trend.get("highest_changed_category"):
            lines.append(
                f"Highest Change: {trend.get('highest_changed_category')} ({self._fmt_pct(trend.get('highest_changed_category_percent'))})"
            )
            
        return "\n".join(lines)

    def _progress_bar(self, percent: float, width: int) -> str:
        filled = min(width, int(max(0, percent) / 100 * width))
        return "█" * filled + "▌" * (1 if 0 < percent < 100 and filled < width else 0)

    def _fmt_pct(self, value):
        if value is None:
            return "n/a"
        return f"{value:+.1f}%"

    def action_next_view(self):
        views = ["daily", "weekly", "monthly"]
        idx = views.index(self._view)
        self._view = views[(idx + 1) % len(views)]
        self.load_report()

    def action_prev_view(self):
        views = ["daily", "weekly", "monthly"]
        idx = views.index(self._view)
        self._view = views[(idx - 1) % len(views)]
        self.load_report()

    def action_prev_period(self):
        if self._view == "daily":
            self._daily_date -= timedelta(days=1)
        elif self._view == "weekly":
            self._weekly_start -= timedelta(days=7)
        else:
            if self._monthly_month == 1:
                self._monthly_year -= 1
                self._monthly_month = 12
            else:
                self._monthly_month -= 1
        self.load_report()

    def action_next_period(self):
        if self._view == "daily":
            self._daily_date += timedelta(days=1)
        elif self._view == "weekly":
            self._weekly_start += timedelta(days=7)
        else:
            if self._monthly_month == 12:
                self._monthly_year += 1
                self._monthly_month = 1
            else:
                self._monthly_month += 1
        self.load_report()

    def action_filter_category(self):
        if self._view != "monthly":
            self.app.push_screen(MessageBox("Category filter is available on monthly view.", "Info"))
            return
        filters = ["", "Food", "Transport", "Fun"]
        try:
            next_idx = (filters.index(self._filter_text) + 1) % len(filters)
        except ValueError:
            next_idx = 0
        self._filter_text = filters[next_idx]
        self.render_report()

    def action_sort_rows(self):
        if self._view != "monthly":
            self.app.push_screen(MessageBox("Sorting is available on monthly view.", "Info"))
            return
        modes = ["actual_desc", "percent_desc", "planned_desc"]
        self._sort_mode = modes[(modes.index(self._sort_mode) + 1) % len(modes)]
        self.render_report()

    def action_open_category_details(self):
        if self._view != "monthly":
            self.app.push_screen(MessageBox("Category details are available on monthly view.", "Info"))
            return
        rows = self._report_data.get("category_breakdown", []) if self._report_data else []
        if not rows:
            self.app.push_screen(MessageBox("No category data available.", "Info"))
            return
        top = rows[0]
        message = (
            f"{top.get('category_name')}\n"
            f"Planned: {format_toman(top.get('planned_amount', 0))}\n"
            f"Actual: {format_toman(top.get('actual_amount', 0))}\n"
            f"Remaining: {format_toman(top.get('remaining', 0))}\n"
            f"Status: {top.get('status_indicator', 'OK')}"
        )
        self.app.push_screen(MessageBox(message, "Category Details"))

    def action_jump_budget(self):
        from tui.screens.budget import BudgetReportScreen

        self.app.push_screen(BudgetReportScreen())

    def action_refresh(self):
        self.load_report()

    def action_go_back(self):
        self.app.pop_screen()


SummaryScreen = AdvancedReportScreen
CategoryReportScreen = AdvancedReportScreen
MonthlyReportScreen = AdvancedReportScreen
BarChartScreen = AdvancedReportScreen
PieChartScreen = AdvancedReportScreen
