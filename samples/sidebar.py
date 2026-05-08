"""
Sidebar Tree View Application with Search
Features: Nested menu tree, real-time search filtering, 
          dynamic content loading, breadcrumb navigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Tree, Input, Static, Header, Footer, Markdown, DataTable, ListView,
    ListItem, Button, TabbedContent, TabPane, Select, Switch, ProgressBar,
    Checkbox, Collapsible, ContentSwitcher, Digits, DirectoryTree,
    LoadingIndicator, Log, MaskedInput, OptionList, RadioButton, RadioSet,
    SelectionList, Sparkline, Tabs, TextArea
)
from textual.widgets.tree import TreeNode
from textual.containers import (
    Horizontal, Vertical, Container, ScrollableContainer, Grid
)
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
        
        if query_lower in self.search_text:
            results.append(self)
        
        for child in self.children:
            results.extend(child.search(query))
        
        return results

    @property
    def search_text(self) -> str:
        """Lower-cased searchable text cached by Python property access."""
        return f"{self.id} {self.label} {self.description}".lower()


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
                        content_type="complex_form"
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


def build_menu_indexes(root: MenuItem) -> tuple[dict[str, MenuItem], dict[str, list[MenuItem]]]:
    """Build fast lookup maps for menu items and breadcrumb paths."""
    items_by_id: dict[str, MenuItem] = {}
    paths_by_id: dict[str, list[MenuItem]] = {}

    def visit(node: MenuItem, path: list[MenuItem]) -> None:
        current_path = [*path, node]
        items_by_id[node.id] = node
        paths_by_id[node.id] = current_path[1:] if node.id == "root" else current_path
        for child in node.children:
            visit(child, current_path)

    visit(root, [])
    return items_by_id, paths_by_id


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
        self._expanded_nodes: set[str] = set()
        self._last_filter_text: Optional[str] = None
    
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
        if filter_text == self._last_filter_text:
            return
        self._last_filter_text = filter_text
        self.clear()
        self.root.remove_children()
        self.build_tree(self.root, self.root_data, filter_text)
        self.root.expand()
    
    def on_tree_node_selected(self, event: "TreeNode.Selected") -> None:
        """Handle node selection."""
        if event.node.data and event.node.data.id != "root":
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


class MenuContentView(Widget):
    """Base widget for a lazily loaded menu view."""

    def __init__(self, menu_item: MenuItem, **kwargs):
        super().__init__(**kwargs)
        self.menu_item = menu_item


class TextContentView(MenuContentView):
    """Lightweight text-based content view."""

    def compose(self) -> ComposeResult:
        content = self.menu_item.content or f"# {self.menu_item.label}\n\n{self.menu_item.description}"
        yield Static(content, classes="content-markdown")


class TableContentView(MenuContentView):
    """Table-based content view."""

    def compose(self) -> ComposeResult:
        yield DataTable(classes="data-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        columns = self.menu_item.data.get("columns", ["ID", "Name", "Status", "Date"])
        for col in columns:
            table.add_column(col, width=15)

        rows = [
            (f"#{1000 + index}", f"{self.menu_item.label} {index + 1}", status, "2024-01-15")
            for index, status in enumerate([
                "Active", "Pending", "Inactive", "Active", "Pending",
                "Active", "Inactive", "Active", "Pending", "Active",
            ])
        ]
        for row in rows:
            table.add_row(*row)


class FormContentView(MenuContentView):
    """Form summary content view."""

    def compose(self) -> ComposeResult:
        fields = self.menu_item.data.get("fields", [
            ("Name", "text", "Enter name..."),
            ("Email", "email", "Enter email..."),
            ("Role", "select", "Select role..."),
            ("Enabled", "toggle", ""),
        ])
        lines = [
            f"# {self.menu_item.icon} {self.menu_item.label}",
            "",
            self.menu_item.description or "Configuration screen",
            "",
            "## Fields",
        ]
        for field_name, field_type, placeholder in fields:
            detail = placeholder or "Toggle option"
            lines.append(f"- **{field_name}** ({field_type}): {detail}")
        lines.extend(["", "[green]Save[/green]  [red]Cancel[/red]"])
        yield Static("\n".join(lines), classes="content-markdown")


class DashboardContentView(MenuContentView):
    """Dashboard summary content view."""

    def compose(self) -> ComposeResult:
        stats = [
            ("Total Revenue", "$124,500", "+12%"),
            ("Active Users", "1,234", "+5%"),
            ("Conversion", "3.2%", "-0.5%"),
            ("Avg Order", "$85.50", "+8%"),
        ]
        lines = [
            f"# {self.menu_item.icon} {self.menu_item.label}",
            "",
            self.menu_item.description or "Dashboard overview",
            "",
            "## KPIs",
        ]
        for label, value, change in stats:
            lines.append(f"- **{label}**: {value} ({change})")
        lines.extend([
            "",
            "## Activity",
            "- ██████████",
            "- ███████",
            "- █████████████",
            "- ██████",
        ])
        yield Static("\n".join(lines), classes="content-markdown")


class ListContentView(MenuContentView):
    """List summary content view."""

    def compose(self) -> ComposeResult:
        lines = [
            f"# {self.menu_item.icon} {self.menu_item.label}",
            "",
            self.menu_item.description or "List view",
            "",
            "## Items",
        ]
        lines.extend(f"- Item {i + 1} for {self.menu_item.label} — 2 hours ago" for i in range(15))
        yield Static("\n".join(lines), classes="content-markdown")


class ContentRenderer(ContentSwitcher):
    """Hosts lazily created menu widgets in the content area."""
    
    DEFAULT_CSS = """
    ContentRenderer {
        height: 1fr;
        width: 100%;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._view_cache: dict[str, Widget] = {}

    def show_menu_item(self, menu_item: MenuItem) -> None:
        """Show a cached content view for the selected menu item."""
        widget = self._view_cache.get(menu_item.id)
        if widget is None:
            widget = self._create_view(menu_item)
            widget.id = f"view-{menu_item.id}"
            self._view_cache[menu_item.id] = widget
            self.mount(widget)
        self.current = widget.id

    def _create_view(self, menu_item: MenuItem) -> Widget:
        """Create a menu widget once, then reuse it."""
        content_type = menu_item.content_type
        if content_type == "markdown":
            return TextContentView(menu_item)
        if content_type == "table":
            return TableContentView(menu_item)
        if content_type == "form":
            return FormContentView(menu_item)
        if content_type == "complex_form":
            return ComplexWidgetForm(menu_item)
        if content_type == "dashboard":
            return DashboardContentView(menu_item)
        if content_type == "list":
            return ListContentView(menu_item)
        return Static(f"Unknown content type: {content_type}")


class ComplexWidgetForm(ScrollableContainer):
    """Rich widget showcase embedded in the content area."""

    def __init__(self, item: MenuItem, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self._heavy_widgets_initialized = False

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.item.icon} {self.item.label} — {self.item.description}",
            classes="form-title",
        )

        with Collapsible(title="Primary Inputs", collapsed=False):
            yield Input(placeholder="Full name", id="complex-name")
            yield MaskedInput(template="9999-99-99", id="complex-date")
            yield TextArea("Notes, comments, and longer form content...", id="complex-notes")
            yield Checkbox("Email notifications", value=True, id="complex-checkbox")
            yield Switch(value=True, id="complex-switch")
            yield Select(
                [("Admin", "admin"), ("Editor", "editor"), ("Viewer", "viewer")],
                prompt="Choose a role",
                id="complex-select",
            )
            yield SelectionList(
                ("Billing", "billing", True),
                ("Reports", "reports", False),
                ("Exports", "exports", True),
                id="complex-selection-list",
            )
            yield RadioSet(
                RadioButton("Daily", id="radio-daily"),
                RadioButton("Weekly", id="radio-weekly"),
                RadioButton("Monthly", id="radio-monthly"),
                id="complex-radio-set",
            )

        with Collapsible(title="Choices And Navigation", collapsed=False):
            yield Tabs("Overview", "Files", "Preview", id="complex-tabs")
            with ContentSwitcher(initial="switch-summary", id="complex-switcher"):
                with Container(id="switch-summary"):
                    yield Static("Summary content inside ContentSwitcher.")
                with Container(id="switch-files"):
                    yield Static("Files view inside ContentSwitcher.")
                with Container(id="switch-preview"):
                    yield Static("Preview view inside ContentSwitcher.")
            yield OptionList("Create", "Duplicate", "Archive", "Delete", id="complex-options")
            yield ListView(
                ListItem(Static("Review draft")),
                ListItem(Static("Assign owner")),
                ListItem(Static("Publish changes")),
                id="complex-list-view",
            )

        with Collapsible(title="Metrics", collapsed=False):
            yield Digits("12890", id="complex-digits")
            yield Sparkline([4, 8, 7, 12, 6, 15, 13, 18, 14, 20], id="complex-sparkline")
            yield ProgressBar(total=100, show_eta=False, id="complex-progress")
            yield Static("Metrics update instantly without reloading the whole screen.")

        with Collapsible(title="Structured Data", collapsed=False):
            yield DataTable(id="complex-table")
            yield Tree("Project Tree", id="complex-tree")
            yield Static("Open the advanced area below to load file explorer and logs.")

        with Collapsible(title="Advanced Widgets", collapsed=True, id="advanced-widgets"):
            yield LoadingIndicator(id="complex-loader")
            yield DirectoryTree(".", id="complex-directory-tree")
            yield Log(id="complex-log")

        with Collapsible(title="Tabbed Content", collapsed=True):
            with TabbedContent(initial="details"):
                with TabPane("Details", id="details"):
                    yield Static("Tabbed content details pane.")
                with TabPane("Activity", id="activity"):
                    yield Static("Tabbed content activity pane.")
                with TabPane("Preview", id="preview"):
                    yield Static("Tabbed content preview pane.")

        with Horizontal(classes="form-actions"):
            yield Button("Save", variant="success", id="btn-save")
            yield Button("Validate", variant="primary", id="btn-validate")
            yield Button("Cancel", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        table = self.query_one("#complex-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Field", "Value", "Status")
        table.add_row("Profile", "Configured", "Ready")
        table.add_row("Security", "2FA Enabled", "Healthy")
        table.add_row("Storage", "128 GB", "Warning")
        table.add_row("Backups", "Nightly", "Ready")

        form_tree = self.query_one("#complex-tree", Tree)
        root = form_tree.root
        identity = root.add("Identity")
        identity.add_leaf("Name")
        identity.add_leaf("Date")
        preferences = root.add("Preferences")
        preferences.add_leaf("Notifications")
        preferences.add_leaf("Access")
        root.expand_all()

        progress = self.query_one("#complex-progress", ProgressBar)
        progress.update(progress=72)

    def on_collapsible_toggled(self, event: Collapsible.Toggled) -> None:
        """Load heavier widgets only when needed."""
        if event.collapsible.id != "advanced-widgets":
            return
        if event.collapsible.collapsed or self._heavy_widgets_initialized:
            return

        log = self.query_one("#complex-log", Log)
        log.write_line("Advanced widgets initialized")
        log.write_line("Directory tree and log are ready")
        self._heavy_widgets_initialized = True


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
        self.menu_items_by_id, self.menu_paths_by_id = build_menu_indexes(self.menu_root)
        self.current_item: Optional[MenuItem] = None
        self.search_results: list[MenuItem] = []
        self._last_search_query = ""
    
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
        if self.menu_root.children:
            self._load_content(self.menu_root.children[0])
    
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
        if query == self._last_search_query:
            return
        self._last_search_query = query
        
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
        self._last_search_query = ""
        
        results_display = self.query_one("#search-results", Static)
        results_display.remove_class("visible")
        
        tree = self.query_one("#menu-tree", SearchTree)
        tree.refresh_tree()
        
        self.search_results = []
    
    def _load_content(self, item: MenuItem) -> None:
        """Load content for selected menu item."""
        if self.current_item and self.current_item.id == item.id:
            return
        self.current_item = item
        
        # Update breadcrumb
        self.query_one("#breadcrumb", Breadcrumb).set_path(
            self.menu_paths_by_id.get(item.id, [item])
        )
        
        # Update footer
        self.query_one("#content-footer", Static).update(
            f"{item.icon} {item.label} | {item.content_type} | {item.description}"
        )
        
        # Render content
        renderer = self.query_one("#content-renderer", ContentRenderer)
        renderer.show_menu_item(item)
    
    def _find_path(self, target: MenuItem) -> list[MenuItem]:
        """Find path from root to target item."""
        return self.menu_paths_by_id.get(target.id, [target])
    
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
    app = SidebarTreeApp()
    app.run()
