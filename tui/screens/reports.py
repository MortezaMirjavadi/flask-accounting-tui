"""Report screens."""

import math
from collections import defaultdict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, ListItem, ListView, Static

from tui.api import api_get, handle_response, format_toman
from tui.widgets import HelpTip, MessageBox, StatusBar


class ReportsScreen(Screen):
    """Reports menu."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "do_summary", "Summary"),
        Binding("2", "do_category", "Category"),
        Binding("3", "do_monthly", "Monthly"),
        Binding("4", "do_bar_chart", "Bar Chart"),
        Binding("5", "do_pie_chart", "Pie Chart"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("REPORTS", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield ListView(
                ListItem(Label("1. Summary")),
                ListItem(Label("2. Category Report")),
                ListItem(Label("3. Monthly Report")),
                ListItem(Label("4. Bar Chart (Categories)")),
                ListItem(Label("5. Pie Chart (Categories)")),
                ListItem(Label("6. Back to Main Menu")),
                id="rep_menu_list",
            )
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[↑/↓] Navigate  [Enter] Select  [1-6] Quick select  [Esc] Back", id="help")
            yield StatusBar("Enter=Select  Esc=Back", id="status")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx == 0:
            self.action_do_summary()
        elif idx == 1:
            self.action_do_category()
        elif idx == 2:
            self.action_do_monthly()
        elif idx == 3:
            self.action_do_bar_chart()
        elif idx == 4:
            self.action_do_pie_chart()
        elif idx == 5:
            self.action_go_back()

    def action_go_back(self):
        self.app.pop_screen()

    def action_do_summary(self):
        self.app.push_screen(SummaryScreen())

    def action_do_category(self):
        self.app.push_screen(CategoryReportScreen())

    def action_do_monthly(self):
        self.app.push_screen(MonthlyReportScreen())

    def action_do_bar_chart(self):
        self.app.push_screen(BarChartScreen())

    def action_do_pie_chart(self):
        self.app.push_screen(PieChartScreen())


class SummaryScreen(Screen):
    """Financial summary report."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("FINANCIAL SUMMARY", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="sum_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#sum_table", DataTable)
        table.add_columns("Item", "Value")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self):
        table = self.query_one("#sum_table", DataTable)
        table.clear()
        resp = api_get("/reports/transactions/summary", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        table.add_row("Total Income", format_toman(data.get("total_income", 0)))
        table.add_row("Total Cost", format_toman(data.get("total_cost", 0)))
        table.add_row("Balance", format_toman(data.get("balance", 0)))

    def action_go_back(self):
        self.app.pop_screen()


class CategoryReportScreen(Screen):
    """Category breakdown report."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("CATEGORY REPORT", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="rep_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#rep_table", DataTable)
        table.add_columns("Category", "Type", "Total")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self):
        table = self.query_one("#rep_table", DataTable)
        table.clear()
        resp = api_get("/reports/transactions/category", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        if not data:
            table.add_row("-", "-", "No data")
        else:
            for r in data:
                table.add_row(
                    r.get("category_name", ""),
                    r.get("category_type", ""),
                    format_toman(r.get("total", 0)),
                )

    def action_go_back(self):
        self.app.pop_screen()


class MonthlyReportScreen(Screen):
    """Monthly breakdown report."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="main_panel"):
            yield Label("MONTHLY REPORT", classes="menu_header")
            yield Static("-" * 50, classes="separator")
            yield DataTable(id="mon_table")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#mon_table", DataTable)
        table.add_columns("Month", "Income", "Cost", "Balance")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.load_data()

    def load_data(self):
        table = self.query_one("#mon_table", DataTable)
        table.clear()
        resp = api_get("/reports/transactions/monthly", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        if err:
            self.app.push_screen(MessageBox(err, "Error"))
            return
        if not data:
            table.add_row("-", "-", "-", "No data")
        else:
            for r in data:
                income = r.get("total_income", 0)
                cost = r.get("total_cost", 0)
                table.add_row(
                    r.get("month", ""),
                    format_toman(income),
                    format_toman(cost),
                    format_toman(income - cost),
                )
        table.zebra_stripes = True

    def action_go_back(self):
        self.app.pop_screen()


class BarChartScreen(Screen):
    """ASCII bar chart for categories."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("CATEGORY BAR CHART", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            yield Static(id="chart_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_chart()

    def _ascii_bar(self, data):
        if not data:
            return "No data"
        labels = [r["category_name"] for r in data]
        values = [r["total"] for r in data]
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1
        max_label = max(len(l) for l in labels) if labels else 1
        
        lines = []
        lines.append(f"{'Category':<{max_label}} | {'Amount':>20} | Chart")
        lines.append("-" * (max_label + 38))
        
        for label, val, row in zip(labels, values, data):
            bar_len = int((val / max_val) * 30)
            color = "green" if row["category_type"] == "income" else "red"
            bar = "█" * bar_len
            lines.append(f"{label:<{max_label}} | {format_toman(val):>20} | [{color}]{bar}[/{color}]")
        
        lines.append("-" * (max_label + 38))
        return "\n".join(lines)

    def load_chart(self):
        resp = api_get("/reports/transactions/category-chart", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        content = self.query_one("#chart_content", Static)
        if err:
            content.update(f"Error: {err}")
            return
        if not data:
            content.update("No data available for chart.")
            return
        chart_str = self._ascii_bar(data)
        content.update(chart_str)

    def action_go_back(self):
        self.app.pop_screen()


class PieChartScreen(Screen):
    """ASCII pie chart for categories."""
    
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="wide_panel"):
            yield Label("CATEGORY PIE CHART", classes="menu_header")
            yield Static("-" * 70, classes="separator")
            yield Static(id="chart_content")
        with Vertical(classes="bottom_bar"):
            yield HelpTip("[Esc] Back to Reports menu", id="help")
            yield StatusBar("Esc=Back", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.load_chart()

    def _ascii_pie(self, labels, values):
        total = sum(values)
        if total == 0:
            return "No data"
        
        items = list(zip(labels, values))
        blocks = ["\u2588", "\u2593", "\u2592", "\u2591", "\u25A0", "\u25A1", "\u25AA", "\u25AB"]
        
        # Build a 2D grid for the circle
        size = 21
        radius = size // 2
        cx, cy = radius, radius
        grid = [[" " for _ in range(size)] for _ in range(size)]
        
        # Fill circle with slices based on angle
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                dist = (dx * dx + dy * dy) ** 0.5
                if dist <= radius:
                    angle = math.atan2(dy, dx)
                    if angle < 0:
                        angle += 2 * math.pi
                    
                    cumulative = 0.0
                    for idx, (_, val) in enumerate(items):
                        slice_angle = (val / total) * 2 * math.pi
                        if cumulative <= angle < cumulative + slice_angle:
                            grid[y][x] = blocks[idx % len(blocks)]
                            break
                        cumulative += slice_angle
        
        # Build legend lines
        lines = []
        lines.append(" " * 8 + "CATEGORY PIE CHART")
        lines.append("")
        
        for i, (label, val) in enumerate(items):
            pct = (val / total) * 100
            block = blocks[i % len(blocks)]
            lines.append(f"  {block} {label:<18} {val:>10,.0f}  ({pct:5.1f}%)")
        
        lines.append("")
        
        # Combine: put circle on the right side
        circle_lines = ["".join(row) for row in grid]
        legend_width = max(len(l) for l in lines) if lines else 0
        
        combined = []
        max_left = len(lines)
        max_right = len(circle_lines)
        
        for i in range(max(max_left, max_right)):
            left = lines[i] if i < max_left else ""
            right = circle_lines[i] if i < max_right else ""
            combined.append(left.ljust(legend_width + 2) + right)
        
        return "\n".join(combined)

    def load_chart(self):
        resp = api_get("/reports/transactions/category-chart", username=self.app.user.get("username"))
        data, err = handle_response(resp)
        content = self.query_one("#chart_content", Static)
        if err:
            content.update(f"Error: {err}")
            return
        if not data:
            content.update("No data available for chart.")
            return

        labels = [r["category_name"] for r in data]
        values = [r["total"] for r in data]
        chart_str = self._ascii_pie(labels, values)
        content.update(chart_str)

    def action_go_back(self):
        self.app.pop_screen()

