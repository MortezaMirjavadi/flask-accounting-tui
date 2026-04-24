"""
Advanced DataTable and ListView Example
Features: Sorting, filtering, selection, custom renderers,
          master-detail pattern, and real-time updates
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    DataTable, ListView, ListItem, Static, 
    Input, Button, Header, Footer, Select, Checkbox,
    TabbedContent, TabPane
)
from textual.containers import (
    Horizontal, Vertical, Container
)
from textual.reactive import reactive
from textual.binding import Binding


# =============================================================================
# Sample Data Models
# =============================================================================

@dataclass
class Employee:
    id: int
    name: str
    department: str
    role: str
    salary: float
    start_date: datetime
    performance: float
    active: bool = True
    
    @property
    def tenure_years(self) -> float:
        return (datetime.now() - self.start_date).days / 365.25
    
    @property
    def performance_color(self) -> str:
        if self.performance >= 0.9:
            return "green"
        elif self.performance >= 0.7:
            return "yellow"
        elif self.performance >= 0.5:
            return "orange"
        return "red"


DEPARTMENTS = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]
ROLES = {
    "Engineering": ["Developer", "Senior Developer", "Tech Lead", "Architect", "CTO"],
    "Sales": ["Sales Rep", "Account Executive", "Sales Manager", "VP Sales"],
    "Marketing": ["Specialist", "Manager", "Director", "CMO"],
    "HR": ["Recruiter", "HR Manager", "People Director", "CHRO"],
    "Finance": ["Analyst", "Accountant", "Controller", "CFO"],
    "Operations": ["Coordinator", "Manager", "Director", "COO"],
}

NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", "Eva Davis",
    "Frank Miller", "Grace Wilson", "Henry Moore", "Ivy Taylor", "Jack Anderson",
    "Kate Thomas", "Lee Jackson", "Mia White", "Noah Harris", "Olivia Martin",
    "Paul Thompson", "Quinn Garcia", "Ryan Martinez", "Sara Robinson", "Tom Clark",
    "Uma Rodriguez", "Victor Lewis", "Wendy Lee", "Xander Walker", "Yara Hall",
    "Zack Allen", "Amy Young", "Ben King", "Cathy Wright", "Dan Lopez"
]


def generate_employees(count: int = 50) -> list[Employee]:
    """Generate sample employee data."""
    employees = []
    for i in range(count):
        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES[dept])
        start = datetime.now() - timedelta(days=random.randint(30, 3650))
        
        base_salary = {
            "Developer": 70000, "Senior Developer": 95000, "Tech Lead": 120000,
            "Architect": 140000, "CTO": 200000,
            "Sales Rep": 50000, "Account Executive": 75000,
            "Sales Manager": 100000, "VP Sales": 150000,
            "Specialist": 55000, "Manager": 85000, "Director": 120000, "CMO": 180000,
            "Recruiter": 50000, "HR Manager": 80000, "People Director": 110000, "CHRO": 160000,
            "Analyst": 60000, "Accountant": 65000, "Controller": 100000, "CFO": 175000,
            "Coordinator": 45000, "Manager": 80000, "Director": 115000, "COO": 190000,
        }.get(role, 60000)
        
        employees.append(Employee(
            id=i + 1000,
            name=random.choice(NAMES),
            department=dept,
            role=role,
            salary=base_salary * random.uniform(0.9, 1.3),
            start_date=start,
            performance=random.random(),
            active=random.random() > 0.15
        ))
    return employees


# =============================================================================
# Custom DataTable with Advanced Features
# =============================================================================

class SortableDataTable(DataTable):
    """Enhanced DataTable with sorting capabilities."""
    
    DEFAULT_CSS = """
    SortableDataTable {
        height: 1fr;
        border: solid $primary;
    }
    
    SortableDataTable > .datatable--header {
        text-style: bold;
        background: $primary-darken-2;
    }
    
    SortableDataTable > .datatable--header-cursor {
        background: $primary;
        color: $text;
    }
    
    SortableDataTable > .datatable--cursor {
        background: $primary-darken-1;
    }
    
    SortableDataTable > .datatable--hover {
        background: $surface-lighten-1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False
        self._column_types: dict[str, type] = {}
    
    def add_sortable_column(self, label: str, key: str, type_: type = str, **kwargs):
        """Add a column with type information for sorting."""
        self._column_types[key] = type_
        self.add_column(label, key=key, **kwargs)
    
    def sort_by(self, column_key: str) -> None:
        """Sort table by column, toggling direction if same column."""
        if self._sort_column == column_key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column_key
            self._sort_reverse = False
        
        self._refresh_sort_indicator()
        self._apply_sort()
    
    def _refresh_sort_indicator(self):
        """Update column headers to show sort direction."""
        for col_key in self._column_types:
            label = str(self.columns[col_key].label).replace(" ▲", "").replace(" ▼", "")
            if col_key == self._sort_column:
                arrow = " ▼" if self._sort_reverse else " ▲"
                self.columns[col_key].label = label + arrow
            else:
                self.columns[col_key].label = label
    
    def _apply_sort(self):
        """Apply current sort to data."""
        if not self._sort_column:
            return
        
        col_idx = list(self._column_types.keys()).index(self._sort_column)
        type_ = self._column_types[self._sort_column]
        
        def sort_key(row):
            value = row[col_idx]
            if type_ in (int, float):
                return float(value) if value is not None else 0
            return str(value).lower()
        
        rows = list(self._data.values())
        rows.sort(key=sort_key, reverse=self._sort_reverse)
        
        self.clear()
        for row_data in rows:
            cells = [cell.value for cell in row_data]
            self.add_row(*cells)
    
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle header click for sorting."""
        col_key = self.ordered_columns[event.column_index].key
        if col_key in self._column_types:
            self.sort_by(col_key)


# =============================================================================
# Custom ListView Items
# =============================================================================

class EmployeeListItem(ListItem):
    """Custom list item with rich formatting."""
    
    DEFAULT_CSS = """
    EmployeeListItem {
        height: auto;
        padding: 0;
    }
    
    EmployeeListItem > Static {
        height: auto;
        padding: 0 1;
    }
    
    EmployeeListItem.--highlight {
        background: $primary-darken-2;
    }
    """
    
    def __init__(self, employee: Employee):
        super().__init__()
        self.employee = employee
    
    def compose(self) -> ComposeResult:
        status = "🟢" if self.employee.active else "🔴"
        perf_bar = "█" * int(self.employee.performance * 10) + "░" * (10 - int(self.employee.performance * 10))
        
        content = f"""{status} [bold]{self.employee.name}[/bold]
[dim]{self.employee.role}[/dim] | {self.employee.department}
Salary: [green]${self.employee.salary:,.0f}[/green] | Tenure: {self.employee.tenure_years:.1f}y
Perf: [{self.employee.performance_color}]{perf_bar}[/{self.employee.performance_color}] {self.employee.performance:.0%}
"""
        yield Static(content)


class DepartmentListItem(ListItem):
    """Department summary item for list view."""
    
    DEFAULT_CSS = """
    DepartmentListItem {
        height: auto;
        padding: 0;
    }
    
    DepartmentListItem.--highlight {
        background: $primary-darken-2;
    }
    """
    
    def __init__(self, department: str, employees: list[Employee]):
        super().__init__()
        self.department = department
        self.employees = employees
    
    def compose(self) -> ComposeResult:
        active = sum(1 for e in self.employees if e.active)
        total = len(self.employees)
        avg_salary = sum(e.salary for e in self.employees) / total if total else 0
        avg_perf = sum(e.performance for e in self.employees) / total if total else 0
        
        perf_color = "green" if avg_perf >= 0.7 else "yellow" if avg_perf >= 0.5 else "red"
        
        content = f"""[bold]{self.department}[/bold] [dim]({active}/{total} active)[/dim]
Avg Salary: [green]${avg_salary:,.0f}[/green]
Avg Performance: [{perf_color}]{avg_perf:.0%}[/{perf_color}]
"""
        yield Static(content)


# =============================================================================
# Main Application Screen
# =============================================================================

class EmployeeBrowserScreen(Screen):
    """Main screen with DataTable and ListView demonstrations."""
    
    CSS = """
    EmployeeBrowserScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
    }
    
    #toolbar {
        height: 3;
        background: $surface-darken-1;
        padding: 0 1;
    }
    
    #main-content {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }
    
    #left-panel {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr;
    }
    
    #filter-bar {
        height: 3;
        background: $surface-darken-2;
        padding: 0 1;
    }
    
    #right-panel {
        border-left: solid $primary-darken-2;
    }
    
    #detail-view {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: solid $primary;
    }
    
    .panel-header {
        text-style: bold;
        color: $primary;
        height: 1;
        padding: 0 1;
    }
    
    #stats-bar {
        height: 3;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        content-align: center middle;
    }
    
    .metric {
        text-style: bold;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    TabPane {
        padding: 0;
    }
    
    #list-view-container {
        height: 1fr;
    }
    
    #list-view-container ListView {
        height: 100%;
        border: solid $primary;
    }
    
    #department-list {
        height: 100%;
        border: solid $primary;
    }
    
    .detail-row {
        height: 1;
        padding: 0 1;
    }
    
    .detail-label {
        color: $text-muted;
        width: 15;
    }
    
    .detail-value {
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("f", "focus_search", "Focus Search"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("a", "toggle_active_only", "Active Only"),
        Binding("s", "sort_dialog", "Sort"),
    ]
    
    filter_text: reactive[str] = reactive("")
    active_only: reactive[bool] = reactive(False)
    selected_department: reactive[Optional[str]] = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.all_employees = generate_employees(100)
        self._employees_cache: list[Employee] = []
        self._selected_employee: Optional[Employee] = None
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # Toolbar
        with Horizontal(id="toolbar"):
            yield Input(placeholder="Search employees...", id="search-input")
            yield Select(
                [(d, d) for d in ["All"] + DEPARTMENTS],
                value="All",
                id="dept-select"
            )
            yield Checkbox("Active Only", id="active-check")
            yield Button("Refresh", id="refresh-btn", variant="primary")
        
        # Main content
        with Horizontal(id="main-content"):
            # Left: DataTable with tabs
            with Vertical(id="left-panel"):
                with TabbedContent(id="main-tabs"):
                    # Tab 1: Employee Table
                    with TabPane("Employee Table", id="tab-table"):
                        with Vertical(id="table-container"):
                            yield SortableDataTable(id="employee-table")
                    
                    # Tab 2: Department View
                    with TabPane("Departments", id="tab-depts"):
                        with Vertical(id="dept-view"):
                            yield Static("Department Overview", classes="panel-header")
                            yield DataTable(id="dept-table")
            
            # Right: ListViews and Detail
            with Vertical(id="right-panel"):
                with TabbedContent(id="side-tabs"):
                    # Tab 1: Employee List
                    with TabPane("Employees", id="tab-list"):
                        with Vertical(id="list-view-container"):
                            yield Static("Employee List", classes="panel-header")
                            yield ListView(id="employee-list")
                    
                    # Tab 2: Department List
                    with TabPane("Summary", id="tab-summary"):
                        with Vertical():
                            yield Static("Departments", classes="panel-header")
                            yield ListView(id="department-list")
                
                # Detail panel (always visible)
                with Container(id="detail-view"):
                    yield Static("Select an employee", id="detail-content")
        
        # Stats bar
        with Horizontal(id="stats-bar"):
            yield Static("Total: 0", id="stat-total")
            yield Static(" | Active: 0", id="stat-active")
            yield Static(" | Avg Salary: $0", id="stat-salary")
            yield Static(" | Avg Performance: 0%", id="stat-perf")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize widgets with data - NOW widgets exist."""
        self._setup_table()
        self._setup_dept_table()
        self._apply_filters()
        self._update_department_list()
        self._update_dept_table()
    
    def _setup_table(self) -> None:
        """Configure the main employee table."""
        table = self.query_one("#employee-table", SortableDataTable)
        
        table.add_sortable_column("ID", "id", int, width=6)
        table.add_sortable_column("Name", "name", str, width=20)
        table.add_sortable_column("Department", "dept", str, width=14)
        table.add_sortable_column("Role", "role", str, width=18)
        table.add_sortable_column("Salary", "salary", float, width=12)
        table.add_sortable_column("Start Date", "start", str, width=12)
        table.add_sortable_column("Perf", "perf", float, width=6)
        table.add_sortable_column("Status", "status", str, width=8)
        
        table.cursor_type = "row"
        table.zebra_stripes = True
    
    def _setup_dept_table(self) -> None:
        """Configure department summary table."""
        table = self.query_one("#dept-table", DataTable)
        table.add_column("Department", width=14)
        table.add_column("Count", width=6)
        table.add_column("Active", width=6)
        table.add_column("Avg Salary", width=12)
        table.add_column("Avg Perf", width=10)
        table.add_column("Top Performer", width=20)
        table.cursor_type = "row"
        table.zebra_stripes = True
    
    def _update_all_views(self) -> None:
        """Update all views with current data."""
        self._update_table(self._employees_cache)
        self._update_employee_list(self._employees_cache)
        self._update_stats(self._employees_cache)
    
    def _update_table(self, employees: list[Employee]) -> None:
        """Populate the DataTable."""
        table = self.query_one("#employee-table", SortableDataTable)
        table.clear()
        
        for emp in employees:
            status = "Active" if emp.active else "Inactive"
            perf_str = f"[{emp.performance_color}]{emp.performance:.0%}[/{emp.performance_color}]"
            
            table.add_row(
                emp.id,
                emp.name,
                emp.department,
                emp.role,
                f"${emp.salary:,.0f}",
                emp.start_date.strftime("%Y-%m-%d"),
                perf_str,
                status,
                key=str(emp.id)
            )
    
    def _update_employee_list(self, employees: list[Employee]) -> None:
        """Populate the ListView with rich employee items."""
        list_view = self.query_one("#employee-list", ListView)
        list_view.clear()
        
        sorted_emps = sorted(employees, key=lambda e: e.performance, reverse=True)
        
        for emp in sorted_emps[:50]:
            list_view.append(EmployeeListItem(emp))
    
    def _update_department_list(self) -> None:
        """Populate department summary ListView."""
        list_view = self.query_one("#department-list", ListView)
        list_view.clear()
        
        by_dept = {}
        for emp in self.all_employees:
            by_dept.setdefault(emp.department, []).append(emp)
        
        for dept in sorted(by_dept.keys()):
            list_view.append(DepartmentListItem(dept, by_dept[dept]))
    
    def _update_dept_table(self) -> None:
        """Update department summary DataTable."""
        table = self.query_one("#dept-table", DataTable)
        table.clear()
        
        by_dept = {}
        for emp in self.all_employees:
            by_dept.setdefault(emp.department, []).append(emp)
        
        for dept, emps in sorted(by_dept.items()):
            active = [e for e in emps if e.active]
            avg_sal = sum(e.salary for e in emps) / len(emps)
            avg_perf = sum(e.performance for e in emps) / len(emps)
            top = max(emps, key=lambda e: e.performance)
            
            perf_color = "green" if avg_perf >= 0.7 else "yellow" if avg_perf >= 0.5 else "red"
            
            table.add_row(
                dept,
                str(len(emps)),
                str(len(active)),
                f"${avg_sal:,.0f}",
                f"[{perf_color}]{avg_perf:.0%}[/{perf_color}]",
                f"{top.name} ({top.performance:.0%})"
            )
    
    def _update_stats(self, employees: list[Employee]) -> None:
        """Update statistics bar."""
        total = len(employees)
        active = sum(1 for e in employees if e.active)
        avg_sal = sum(e.salary for e in employees) / total if total else 0
        avg_perf = sum(e.performance for e in employees) / total if total else 0
        
        self.query_one("#stat-total", Static).update(f"Total: [metric]{total}[/metric]")
        self.query_one("#stat-active", Static).update(f" | Active: [metric]{active}[/metric]")
        self.query_one("#stat-salary", Static).update(f" | Avg Salary: [metric]${avg_sal:,.0f}[/metric]")
        self.query_one("#stat-perf", Static).update(f" | Avg Performance: [metric]{avg_perf:.0%}[/metric]")
    
    def _update_detail_view(self, employee: Optional[Employee]) -> None:
        """Update the detail panel."""
        content = self.query_one("#detail-content", Static)
        
        if employee is None:
            content.update("Select an employee to view details")
            return
        
        perf_bar = "█" * int(employee.performance * 20) + "░" * (20 - int(employee.performance * 20))
        status_color = "green" if employee.active else "red"
        status_text = "Active" if employee.active else "Inactive"
        
        detail = f"""[bold underline]{employee.name}[/bold underline]

[dim]ID:[/dim]           {employee.id}
[dim]Department:[/dim]   {employee.department}
[dim]Role:[/dim]         {employee.role}
[dim]Salary:[/dim]       [green]${employee.salary:,.2f}[/green]
[dim]Start Date:[/dim]   {employee.start_date.strftime('%B %d, %Y')}
[dim]Tenure:[/dim]       {employee.tenure_years:.2f} years

[dim]Status:[/dim]       [{status_color}]{status_text}[/{status_color}]
[dim]Performance:[/dim]  [{employee.performance_color}]{perf_bar}[/{employee.performance_color}]
                       {employee.performance:.1%}

[dim]Last Review:[/dim]  {(datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d')}
"""
        content.update(detail)
    
    def _apply_filters(self) -> None:
        """Apply all active filters."""
        filtered = self.all_employees.copy()
        
        # Text filter
        if self.filter_text:
            text = self.filter_text.lower()
            filtered = [
                e for e in filtered
                if text in e.name.lower() 
                or text in e.role.lower()
                or text in str(e.id)
            ]
        
        # Department filter
        if self.selected_department and self.selected_department != "All":
            filtered = [e for e in filtered if e.department == self.selected_department]
        
        # Active only
        if self.active_only:
            filtered = [e for e in filtered if e.active]
        
        self._employees_cache = filtered
        self._update_all_views()
    
    def watch_filter_text(self, text: str) -> None:
        """Apply text filter."""
        self._apply_filters()
    
    def watch_active_only(self, active: bool) -> None:
        """Toggle active filter."""
        self._apply_filters()
    
    def watch_selected_department(self, dept: Optional[str]) -> None:
        """Filter by department."""
        self._apply_filters()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input."""
        if event.input.id == "search-input":
            self.filter_text = event.value
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle department selection."""
        if event.select.id == "dept-select":
            self.selected_department = event.value if event.value != "All" else None
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle active-only toggle."""
        if event.checkbox.id == "active-check":
            self.active_only = event.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "refresh-btn":
            self.action_refresh_data()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle table row selection."""
        row_key = event.row_key.value
        
        for emp in self._employees_cache:
            if str(emp.id) == row_key:
                self._selected_employee = emp
                self._update_detail_view(emp)
                break
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Preview on hover/highlight."""
        row_key = event.row_key.value
        for emp in self._employees_cache:
            if str(emp.id) == row_key:
                self._update_detail_view(emp)
                break
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection."""
        item = event.item
        if isinstance(item, EmployeeListItem):
            self._selected_employee = item.employee
            self._update_detail_view(item.employee)
        elif isinstance(item, DepartmentListItem):
            self.selected_department = item.department
            self.query_one("#dept-select", Select).value = item.department
            self.query_one("#main-tabs", TabbedContent).active = "tab-table"
    
    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()
    
    def action_refresh_data(self) -> None:
        """Refresh with new random data."""
        self.all_employees = generate_employees(100)
        self._apply_filters()
        self._update_department_list()
        self._update_dept_table()
        self.notify("Data refreshed!", severity="information")
    
    def action_toggle_active_only(self) -> None:
        """Toggle active-only filter."""
        checkbox = self.query_one("#active-check", Checkbox)
        checkbox.value = not checkbox.value
    
    def action_sort_dialog(self) -> None:
        """Show sort options."""
        table = self.query_one("#employee-table", SortableDataTable)
        columns = list(table._column_types.keys())
        current = table._sort_column
        if current is None:
            next_col = columns[0]
        else:
            idx = columns.index(current)
            next_col = columns[(idx + 1) % len(columns)]
        
        table.sort_by(next_col)
        self.notify(f"Sorted by: {next_col}")


class DataTableListViewApp(App):
    """Main application."""
    
    CSS = """
    Screen { align: center middle; }
    """
    
    def on_mount(self) -> None:
        self.push_screen(EmployeeBrowserScreen())


if __name__ == "__main__":
    app = DataTableListViewApp()
    app.run()
