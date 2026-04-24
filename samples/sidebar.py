"""
Sidebar Tree View Application with Search
Features: Nested menu tree, real-time search filtering, 
          dynamic content loading, breadcrumb navigation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Tree, Input, Static, Header, Footer, 
    Markdown, DataTable, ListView, ListItem, Button,
    TabbedContent, TabPane, Select, Switch, ProgressBar
)
from textual.widgets.tree import TreeNode
from textual.containers import (
    Horizontal, Vertical, Container, ScrollableContainer, Grid
)
from textual.reactive import reactive
from textual.binding import Binding
from textual.widget import Widget
from textual.message import Message


# =============================================================================
# Menu Data Model
# =============================================================================

@dataclass
class MenuItem:
    """Represents a menu item with content."""
    id: str
    label: str
    icon: str = "📄"
    description: str = ""
    content_type: str = "markdown"  # markdown, table, form, dashboard, list
    content: str = ""
    data: dict = field(default_factory=dict)
    children: list[MenuItem] = field(default_factory=list)
    badge: Optional[str] = None
    disabled: bool = False
    
    def to_tree_label(self, search_highlight: str = "") -> str:
        """Format for tree display with optional search highlight."""
        badge_str = f" [{badge}]" if (badge := self.badge) else ""
        label = self.label
        
        if search_highlight and search_highlight.lower() in label.lower():
            # Highlight matching portion
            idx = label.lower().index(search_highlight.lower())
            matched = label[idx:idx + len(search_highlight)]
            label = f"{label[:idx]}[reverse]{matched}[/reverse]{label[idx + len(search_highlight):]}"
        
        return f"{self.icon} {label}{badge_str}"
    
    @property
    def full_path(self) -> str:
        """Get full path for breadcrumbs."""
        return self.label
    
    def flatten(self) -> list[tuple[str, MenuItem]]:
        """Flatten tree to list of (path, item) tuples."""
        result = [(self.label, self)]
        for child in self.children:
            for subpath, item in child.flatten():
                result.append((f"{self.label} / {subpath}", item))
        return result
    
    def search(self, query: str) -> list[MenuItem]:
        """Search for matching items in tree."""
        results = []
        query_lower = query.lower()
        
        if (query_lower in self.label.lower() or 
            query_lower in self.description.lower()):
            results.append(self)
        
        for child in self.children:
            results.extend(child.search(query))
        
        return results


# =============================================================================
# Sample Menu Data
# =============================================================================

def create_sample_menu() -> MenuItem:
    """Create comprehensive sample menu structure."""
    
    return MenuItem(
        id="root",
        label="Root",
        icon="🏠",
        children=[
            # Dashboard
            MenuItem(
                id="dashboard",
                label="Dashboard",
                icon="📊",
                description="Overview and analytics",
                content_type="dashboard",
                content="# Dashboard\n\nWelcome to your personal dashboard!",
                data={"widgets": ["stats", "chart", "recent"]}
            ),
            
            # Users Section
            MenuItem(
                id="users",
                label="User Management",
                icon="👥",
                description="Manage system users",
                children=[
                    MenuItem(
                        id="users-all",
                        label="All Users",
                        icon="📋",
                        description="List of all users",
                        content_type="table",
                        content="User data table",
                        data={"columns": ["ID", "Name", "Email", "Role", "Status"]}
                    ),
                    MenuItem(
                        id="users-roles",
                        label="Roles & Permissions",
                        icon="🔐",
                        description="Manage user roles",
                        content_type="form",
                        content="Role configuration form",
                        data={"roles": ["Admin", "Editor", "Viewer"]}
                    ),
                    MenuItem(
                        id="users-activity",
                        label="Activity Log",
                        icon="📜",
                        description="User activity history",
                        content_type="list",
                        content="Recent user activities",
                        badge="12"
                    ),
                ]
            ),
            
            # Products Section
            MenuItem(
                id="products",
                label="Products",
                icon="📦",
                description="Product catalog management",
                children=[
                    MenuItem(
                        id="products-list",
                        label="Product List",
                        icon="📋",
                        description="All products",
                        content_type="table",
                        content="Product inventory"
                    ),
                    MenuItem(
                        id="products-categories",
                        label="Categories",
                        icon="🏷️",
                        description="Product categories",
                        children=[
                            MenuItem(
                                id="cat-electronics",
                                label="Electronics",
                                icon="💻",
                                description="Electronic devices",
                                content_type="markdown",
                                content="# Electronics\n\nLaptops, phones, tablets..."
                            ),
                            MenuItem(
                                id="cat-clothing",
                                label="Clothing",
                                icon="👕",
                                description="Apparel and accessories",
                                content_type="markdown",
                                content="# Clothing\n\nShirts, pants, shoes..."
                            ),
                            MenuItem(
                                id="cat-food",
                                label="Food & Beverage",
                                icon="🍔",
                                description="Edible products",
                                content_type="markdown",
                                content="# Food & Beverage\n\nOrganic and fresh..."
                            ),
                        ]
                    ),
                    MenuItem(
                        id="products-inventory",
                        label="Inventory",
                        icon="📦",
                        description="Stock management",
                        content_type="dashboard",
                        badge="Low"
                    ),
                ]
            ),
            
            # Orders Section
            MenuItem(
                id="orders",
                label="Orders",
                icon="🛒",
                description="Order management",
                children=[
                    MenuItem(
                        id="orders-pending",
                        label="Pending Orders",
                        icon="⏳",
                        description="Awaiting processing",
                        content_type="table",
                        badge="5"
                    ),
                    MenuItem(
                        id="orders-processing",
                        label="Processing",
                        icon="⚙️",
                        description="Currently processing",
                        content_type="table"
                    ),
                    MenuItem(
                        id="orders-completed",
                        label="Completed",
                        icon="✅",
                        description="Finished orders",
                        content_type="table"
                    ),
                    MenuItem(
                        id="orders-returns",
                        label="Returns",
                        icon="↩️",
                        description="Return requests",
                        content_type="form",
                        badge="3"
                    ),
                ]
            ),
            
            # Reports Section
            MenuItem(
                id="reports",
                label="Reports",
                icon="📈",
                description="Analytics and reports",
                children=[
                    MenuItem(
                        id="reports-sales",
                        label="Sales Report",
                        icon="💰",
                        description="Revenue analytics",
                        content_type="dashboard"
                    ),
                    MenuItem(
                        id="reports-traffic",
                        label="Traffic Analysis",
                        icon="🌐",
                        description="Website traffic",
                        content_type="dashboard"
                    ),
                    MenuItem(
                        id="reports-custom",
                        label="Custom Reports",
                        icon="🔧",
                        description="Build custom reports",
                        content_type="form"
                    ),
                ]
            ),
            
            # Settings
            MenuItem(
                id="settings",
                label="Settings",
                icon="⚙️",
                description="System configuration",
                children=[
                    MenuItem(
                        id="settings-general",
                        label="General",
                        icon="🔧",
                        description="General settings",
                        content_type="form"
                    ),
                    MenuItem(
                        id="settings-security",
                        label="Security",
                        icon="🔒",
                        description="Security settings",
                        content_type="form"
                    ),
                    MenuItem(
                        id="settings-notifications",
                        label="Notifications",
                        icon="🔔",
                        description="Notification preferences",
                        content_type="form"
                    ),
                    MenuItem(
                        id="settings-integrations",
                        label="Integrations",
                        icon="🔌",
                        description="Third-party integrations",
                        content_type="list",
                        children=[
                            MenuItem(
                                id="int-slack",
                                label="Slack",
                                icon="💬",
                                description="Slack integration",
                                content_type="form"
                            ),
                            MenuItem(
                                id="int-github",
                                label="GitHub",
                                icon="🐙",
                                description="GitHub integration",
                                content_type="form"
                            ),
                        ]
                    ),
                ]
            ),
            
            # Help
            MenuItem(
                id="help",
                label="Help & Support",
                icon="❓",
                description="Documentation and support",
                children=[
                    MenuItem(
                        id="help-docs",
                        label="Documentation",
                        icon="📚",
                        description="User documentation",
                        content_type="markdown",
                        content="# Documentation\n\nWelcome to the help center..."
                    ),
                    MenuItem(
                        id="help-faq",
                        label="FAQ",
                        icon="❔",
                        description="Frequently asked questions",
                        content_type="markdown",
                        content="# FAQ\n\n**Q: How do I reset my password?**\n\nA: Go to Settings > Security..."
                    ),
                    MenuItem(
                        id="help-contact",
                        label="Contact Support",
                        icon="📧",
                        description="Get in touch",
                        content_type="form"
                    ),
                ]
            ),
        ]
    )


# =============================================================================
# Custom Widgets
# =============================================================================

class SearchTree(Tree[MenuItem]):
    """Tree with search filtering capabilities."""
    
    DEFAULT_CSS = """
    SearchTree {
        width: 100%;
        height: 1fr;
        border: none;
        background: transparent;
        padding: 0;
    }
    
    SearchTree > .tree--cursor {
        background: $primary-darken-1;
        color: $text;
        text-style: bold;
    }
    
    SearchTree > .tree--highlight {
        background: $primary-darken-2;
    }
    
    SearchTree > .tree--guides {
        color: $surface-lighten-2;
    }
    
    SearchTree > .tree--guides-selected {
        color: $primary;
    }
    
    SearchTree > .tree--label {
        width: 100%;
    }
    """
    
    def __init__(self, root: MenuItem, **kwargs):
        super().__init__(root.label, data=root, **kwargs)
        self.root_data = root
        self._search_query: str = ""
        self._expanded_nodes: set[str] = set()
    
    def build_tree(self, node: "TreeNode", menu_item: MenuItem, filter_text: str = "") -> None:
        """Build tree nodes recursively with optional filtering."""
        for child in menu_item.children:
            if filter_text and not self._matches_search(child, filter_text):
                # Still show if any descendant matches
                if not any(self._matches_search(d, filter_text) for _, d in child.flatten()):
                    continue
            
            child_node = node.add(child.to_tree_label(filter_text), data=child)
            child_node.allow_expand = len(child.children) > 0
            
            if filter_text:
                child_node.expand()
            elif child.id in self._expanded_nodes:
                child_node.expand()
            
            if child.children:
                self.build_tree(child_node, child, filter_text)
    
    def _matches_search(self, item: MenuItem, query: str) -> bool:
        """Check if item matches search query."""
        query_lower = query.lower()
        return (query_lower in item.label.lower() or 
                query_lower in item.description.lower() or
                query_lower in item.id.lower())
    
    def refresh_tree(self, filter_text: str = "") -> None:
        """Rebuild tree with optional filter."""
        self.clear()
        self.root.remove_children()
        self.build_tree(self.root, self.root_data, filter_text)
        self.root.expand()
    
    def on_tree_node_selected(self, event: "TreeNode.Selected") -> None:
        """Handle node selection."""
        if event.node.data and not event.node.data.children:
            # Only select leaf nodes or nodes with content
            self.post_message(self.MenuSelected(event.node.data))
    
    def on_tree_node_expanded(self, event: "TreeNode.Expanded") -> None:
        """Track expanded nodes."""
        if event.node.data:
            self._expanded_nodes.add(event.node.data.id)
    
    def on_tree_node_collapsed(self, event: "TreeNode.Collapsed") -> None:
        """Track collapsed nodes."""
        if event.node.data and event.node.data.id in self._expanded_nodes:
            self._expanded_nodes.remove(event.node.data.id)
    
    class MenuSelected(Message):
        """Message sent when a menu item is selected."""
        
        def __init__(self, menu_item: MenuItem) -> None:
            self.menu_item = menu_item
            super().__init__()


class Breadcrumb(Static):
    """Breadcrumb navigation widget."""
    
    DEFAULT_CSS = """
    Breadcrumb {
        height: 1;
        color: $text-muted;
        text-style: italic;
    }
    
    Breadcrumb .crumb {
        color: $primary;
    }
    
    Breadcrumb .crumb:hover {
        text-style: underline;
    }
    
    Breadcrumb .separator {
        color: $text-muted;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__("Select an item from the menu", *args, **kwargs)
        self.path: list[MenuItem] = []
    
    def set_path(self, path: list[MenuItem]) -> None:
        """Update breadcrumb path."""
        self.path = path
        if not path:
            self.update("Select an item from the menu")
            return
        
        crumbs = []
        for i, item in enumerate(path):
            if i > 0:
                crumbs.append("[dim] / [/dim]")
            crumbs.append(f"[bold]{item.icon} {item.label}[/bold]")
        
        self.update("".join(crumbs))


class ContentRenderer(Static):
    """Renders different content types dynamically."""
    
    DEFAULT_CSS = """
    ContentRenderer {
        height: 1fr;
        width: 100%;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_widget: Optional[Widget] = None
    
    def render_content(self, menu_item: MenuItem) -> ComposeResult:
        """Render appropriate content based on type."""
        # Remove previous content
        for child in list(self.children):
            child.remove()
        
        content_type = menu_item.content_type
        
        if content_type == "markdown":
            yield self._render_markdown(menu_item)
        elif content_type == "table":
            yield self._render_table(menu_item)
        elif content_type == "form":
            yield self._render_form(menu_item)
        elif content_type == "dashboard":
            yield self._render_dashboard(menu_item)
        elif content_type == "list":
            yield self._render_list(menu_item)
        else:
            yield Static(f"Unknown content type: {content_type}")
    
    def _render_markdown(self, item: MenuItem) -> Widget:
        """Render markdown content."""
        content = item.content or f"# {item.label}\n\n{item.description}"
        return Markdown(content, classes="content-markdown")
    
    def _render_table(self, item: MenuItem) -> Widget:
        """Render data table."""
        container = Vertical(classes="content-table")
        
        # Sample data based on item
        table = DataTable(classes="data-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        columns = item.data.get("columns", ["ID", "Name", "Status", "Date"])
        for col in columns:
            table.add_column(col, width=15)
        
        # Generate sample rows
        import random
        for i in range(20):
            status = random.choice(["Active", "Pending", "Inactive"])
            status_color = {"Active": "green", "Pending": "yellow", "Inactive": "red"}[status]
            row = [
                f"#{1000 + i}",
                f"Sample {item.label} {i+1}",
                f"[{status_color}]{status}[/{status_color}]",
                "2024-01-15"
            ]
            table.add_row(*row)
        
        return table
    
    def _render_form(self, item: MenuItem) -> Widget:
        """Render configuration form."""
        container = ScrollableContainer(classes="content-form")
        
        with container:
            yield Static(f"## {item.icon} {item.label}", classes="form-title")
            yield Static(item.description, classes="form-description")
            
            # Sample form fields
            fields = item.data.get("fields", [
                ("Name", "text", "Enter name..."),
                ("Email", "email", "Enter email..."),
                ("Role", "select", "Select role..."),
                ("Enabled", "toggle", ""),
            ])
            
            for field_name, field_type, placeholder in fields:
                with Horizontal(classes="form-row"):
                    yield Static(f"{field_name}:", classes="form-label")
                    if field_type == "toggle":
                        yield Switch(value=True, classes="form-input")
                    elif field_type == "select":
                        yield Select([("Option 1", "1"), ("Option 2", "2")], classes="form-input")
                    else:
                        yield Input(placeholder=placeholder, classes="form-input")
            
            with Horizontal(classes="form-actions"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="error", id="btn-cancel")
        
        return container
    
    def _render_dashboard(self, item: MenuItem) -> Widget:
        """Render dashboard with widgets."""
        grid = Grid(classes="content-dashboard")
        grid.styles.grid_size_rows = 2
        grid.styles.grid_size_columns = 2
        grid.styles.height = "100%"
        
        with grid:
            # Stats cards
            for i, (label, value, change) in enumerate([
                ("Total Revenue", "$124,500", "+12%"),
                ("Active Users", "1,234", "+5%"),
                ("Conversion", "3.2%", "-0.5%"),
                ("Avg Order", "$85.50", "+8%"),
            ]):
                with Container(classes="dashboard-card"):
                    yield Static(label, classes="card-label")
                    yield Static(value, classes="card-value")
                    color = "green" if "+" in change else "red"
                    yield Static(f"[{color}]{change}[/{color}]", classes="card-change")
            
            # Chart placeholder
            with Container(classes="dashboard-chart"):
                yield Static(f"## {item.label} Chart", classes="chart-title")
                # Simple bar chart using text
                bars = ["█" * random.randint(5, 20) for _ in range(10)]
                for bar in bars:
                    yield Static(bar, classes="chart-bar")
        
        return grid
    
    def _render_list(self, item: MenuItem) -> Widget:
        """Render list view."""
        container = Vertical(classes="content-list")
        
        with container:
            yield Static(f"## {item.icon} {item.label}", classes="list-title")
            
            # Sample list items
            for i in range(15):
                with Horizontal(classes="list-row"):
                    yield Static(f"● Item {i+1} for {item.label}")
                    yield Static("2 hours ago", classes="list-time")
        
        return container


# =============================================================================
# Main Screen
# =============================================================================

class SidebarAppScreen(Screen):
    """Main application screen with sidebar and content area."""
    
    CSS = """
    SidebarAppScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr;
    }
    
    #main-layout {
        layout: grid;
        grid-size: 2;
        grid-columns: 35 1fr;
        height: 1fr;
    }
    
    /* Sidebar Styles */
    #sidebar {
        background: $surface-darken-1;
        border-right: solid $primary-darken-2;
        layout: grid;
        grid-size: 1;
        grid-rows: auto auto 1fr;
    }
    
    #sidebar-header {
        height: 3;
        background: $primary-darken-2;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }
    
    #search-container {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
    }
    
    #search-input {
        border: none;
        background: $surface;
        height: 1;
        margin: 1 0;
    }
    
    #search-input:focus {
        border: none;
    }
    
    #search-results {
        display: none;
        height: auto;
        max-height: 10;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }
    
    #search-results.visible {
        display: block;
    }
    
    #tree-container {
        padding: 0;
        overflow: hidden auto;
    }
    
    /* Content Area Styles */
    #content-area {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
        background: $surface;
    }
    
    #content-header {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-2;
        padding: 0 2;
        content-align: left middle;
    }
    
    #breadcrumb {
        width: 1fr;
    }
    
    #content-actions {
        width: auto;
        height: 100%;
    }
    
    #content-body {
        padding: 1 2;
        overflow: hidden auto;
    }
    
    #content-footer {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 2;
        content-align: left middle;
    }
    
    /* Content Type Specific Styles */
    .content-markdown {
        padding: 1;
    }
    
    .content-table {
        height: 100%;
        width: 100%;
    }
    
    .data-table {
        height: 100%;
        border: solid $primary-darken-2;
    }
    
    .content-form {
        padding: 2;
        height: auto;
    }
    
    .form-title {
        text-style: bold;
        color: $primary;
        height: 2;
    }
    
    .form-description {
        color: $text-muted;
        margin-bottom: 1;
    }
    
    .form-row {
        height: 3;
        margin: 1 0;
    }
    
    .form-label {
        width: 20;
        content-align: left middle;
    }
    
    .form-input {
        width: 1fr;
    }
    
    .form-actions {
        height: 3;
        margin-top: 2;
    }
    
    .form-actions Button {
        margin-right: 1;
    }
    
    .content-dashboard {
        padding: 1;
        grid-gutter: 1;
    }
    
    .dashboard-card {
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        padding: 1;
        height: 100%;
    }
    
    .card-label {
        color: $text-muted;
        text-style: bold;
    }
    
    .card-value {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 2;
        content-align: center middle;
    }
    
    .card-change {
        text-align: right;
    }
    
    .dashboard-chart {
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        padding: 1;
        column-span: 2;
        height: 100%;
    }
    
    .chart-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    .chart-bar {
        color: $primary;
    }
    
    .content-list {
        padding: 1;
    }
    
    .list-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .list-row {
        height: 2;
        border-bottom: solid $surface-darken-2;
        content-align: left middle;
    }
    
    .list-time {
        color: $text-muted;
        text-align: right;
        width: auto;
    }
    
    /* Quick actions */
    #quick-actions {
        height: auto;
        background: $surface-darken-2;
        padding: 1;
    }
    
    .action-btn {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("ctrl+1", "focus_sidebar", "Sidebar"),
        Binding("ctrl+2", "focus_content", "Content"),
        Binding("escape", "clear_search", "Clear Search"),
    ]
    
    def __init__(self):
        super().__init__()
        self.menu_root = create_sample_menu()
        self.current_item: Optional[MenuItem] = None
        self.search_results: list[MenuItem] = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal(id="main-layout"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("📋 Navigation", id="sidebar-header")
                
                with Container(id="search-container"):
                    yield Input(
                        placeholder="🔍 Search menu...",
                        id="search-input"
                    )
                
                yield Static("", id="search-results")
                
                with Container(id="tree-container"):
                    yield SearchTree(self.menu_root, id="menu-tree")
                
                with Horizontal(id="quick-actions"):
                    yield Button("Expand All", id="btn-expand", variant="primary")
                    yield Button("Collapse", id="btn-collapse", variant="default")
            
            # Content Area
            with Vertical(id="content-area"):
                with Horizontal(id="content-header"):
                    yield Breadcrumb(id="breadcrumb")
                    with Horizontal(id="content-actions"):
                        yield Button("✏️ Edit", id="btn-edit", variant="primary")
                        yield Button("🔄 Refresh", id="btn-refresh")
                        yield Button("⚙️ Settings", id="btn-settings")
                
                with Container(id="content-body"):
                    yield ContentRenderer(id="content-renderer")
                
                yield Static("Ready", id="content-footer")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the tree."""
        tree = self.query_one("#menu-tree", SearchTree)
        tree.refresh_tree()
        tree.focus()
    
    def on_search_tree_menu_selected(self, event: SearchTree.MenuSelected) -> None:
        """Handle menu selection from tree."""
        self._load_content(event.menu_item)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            query = event.value.strip()
            self._perform_search(query)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if self.search_results:
                self._load_content(self.search_results[0])
                self._clear_search_ui()
    
    def _perform_search(self, query: str) -> None:
        """Perform search and update UI."""
        results_display = self.query_one("#search-results", Static)
        tree = self.query_one("#menu-tree", SearchTree)
        
        if not query:
            tree.refresh_tree()
            results_display.remove_class("visible")
            results_display.update("")
            self.search_results = []
            return
        
        # Search in tree
        self.search_results = self.menu_root.search(query)
        
        # Update tree with filter
        tree.refresh_tree(query)
        
        # Show result count
        count = len(self.search_results)
        results_display.update(f"[dim]{count} result{'s' if count != 1 else ''} found[/dim]")
        results_display.add_class("visible")
    
    def _clear_search_ui(self) -> None:
        """Clear search and restore normal tree view."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        
        results_display = self.query_one("#search-results", Static)
        results_display.remove_class("visible")
        
        tree = self.query_one("#menu-tree", SearchTree)
        tree.refresh_tree()
        
        self.search_results = []
    
    def _load_content(self, item: MenuItem) -> None:
        """Load content for selected menu item."""
        self.current_item = item
        
        # Update breadcrumb
        path = self._find_path(item)
        self.query_one("#breadcrumb", Breadcrumb).set_path(path)
        
        # Update footer
        self.query_one("#content-footer", Static).update(
            f"{item.icon} {item.label} | {item.content_type} | {item.description}"
        )
        
        # Render content
        renderer = self.query_one("#content-renderer", ContentRenderer)
        renderer.render_content(item)
    
    def _find_path(self, target: MenuItem) -> list[MenuItem]:
        """Find path from root to target item."""
        def search(node: MenuItem, path: list[MenuItem]) -> Optional[list[MenuItem]]:
            current = path + [node]
            if node.id == target.id:
                return current
            for child in node.children:
                result = search(child, current)
                if result:
                    return result
            return None
        
        result = search(self.menu_root, [])
        return result[1:] if result else []  # Exclude root
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id
        
        if btn_id == "btn-expand":
            tree = self.query_one("#menu-tree", SearchTree)
            tree.root.expand_all()
        
        elif btn_id == "btn-collapse":
            tree = self.query_one("#menu-tree", SearchTree)
            tree.root.collapse_all()
        
        elif btn_id == "btn-refresh":
            if self.current_item:
                self._load_content(self.current_item)
                self.notify("Refreshed!", severity="information")
        
        elif btn_id == "btn-edit":
            self.notify("Edit mode activated", severity="warning")
        
        elif btn_id == "btn-save":
            self.notify("Changes saved!", severity="success")
        
        elif btn_id == "btn-cancel":
            self.notify("Cancelled", severity="error")
    
    def action_focus_search(self) -> None:
        """Focus search input."""
        self.query_one("#search-input", Input).focus()
    
    def action_focus_sidebar(self) -> None:
        """Focus sidebar tree."""
        self.query_one("#menu-tree", SearchTree).focus()
    
    def action_focus_content(self) -> None:
        """Focus content area."""
        self.query_one("#content-renderer", ContentRenderer).focus()
    
    def action_clear_search(self) -> None:
        """Clear search and reset tree."""
        self._clear_search_ui()


class SidebarTreeApp(App):
    """Main application."""
    
    CSS = """
    Screen { align: center middle; }
    """
    
    def on_mount(self) -> None:
        self.push_screen(SidebarAppScreen())


if __name__ == "__main__":
    import random
    app = SidebarTreeApp()
    app.run()
