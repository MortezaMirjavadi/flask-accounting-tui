"""
Sidebar Tree View Application with Search
Features: Nested menu tree, real-time search filtering, 
          dynamic content loading, breadcrumb navigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import jdatetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Tree, Input, Static, Header, Footer, Button, 
    DataTable, Markdown, ContentSwitcher, LoadingIndicator
)
from textual.widgets.tree import TreeNode
from textual.widget import Widget


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
    content_type: str = "screen"
    content: str = ""
    data: dict = field(default_factory=dict)
    children: list[MenuItem] = field(default_factory=list)
    badge: Optional[str] = None
    disabled: bool = False

    def to_tree_label(self, search_highlight: str = "") -> str:
        """Format for tree display with optional search highlight."""
        badge_str = f" [{self.badge}]" if self.badge else ""
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
# Accounting Menu Structure
# =============================================================================

def create_accounting_menu() -> MenuItem:
    """Create accounting menu structure."""
    return MenuItem(
        id="root", label="Root", icon="🏠",
        children=[
            MenuItem(id="dashboard", label="Dashboard", icon="📊", description="Overview", content="dashboard"),
            MenuItem(id="categories", label="Categories", icon="🏷️", description="Manage categories",
                children=[
                    MenuItem(id="categories-all", label="All Categories", icon="📋", content="categories"),
                    MenuItem(id="categories-add", label="Add Category", icon="➕", content="categories_add"),
                ]),
            MenuItem(id="sources", label="Sources", icon="💰", description="Manage sources",
                children=[
                    MenuItem(id="sources-all", label="All Sources", icon="📋", content="sources"),
                    MenuItem(id="sources-add", label="Add Source", icon="➕", content="sources_add"),
                ]),
            MenuItem(id="transactions", label="Transactions", icon="💳", description="Manage transactions",
                children=[
                    MenuItem(id="transactions-all", label="All Transactions", icon="📋", content="transactions"),
                    MenuItem(id="transactions-add", label="Add Transaction", icon="➕", content="transactions_add"),
                ]),
            MenuItem(id="reports", label="Reports", icon="📈", description="Financial reports",
                children=[
                    MenuItem(id="reports-financial", label="Financial Report", icon="💰", content="reports"),
                    MenuItem(id="reports-category", label="Category Report", icon="🏷️", content="reports_category"),
                ]),
            MenuItem(id="budget", label="Budget", icon="🎯", description="Budget management",
                children=[
                    MenuItem(id="budget-monthly", label="Monthly Budget", icon="📅", content="budget"),
                    MenuItem(id="budget-rules", label="Budget Rules", icon="⚙️", content="budget_rules"),
                ]),
            MenuItem(id="calendar", label="Calendar", icon="📅", description="Financial calendar",
                children=[
                    MenuItem(id="calendar-events", label="Events", icon="📋", content="calendar"),
                    MenuItem(id="calendar-add", label="Add Event", icon="➕", content="calendar_add"),
                ]),
            MenuItem(id="checks", label="Checks", icon="📝", description="Check management",
                children=[
                    MenuItem(id="checks-issued", label="Issued Checks", icon="📤", content="checks"),
                    MenuItem(id="checks-received", label="Received Checks", icon="📥", content="checks_received"),
                    MenuItem(id="checks-add", label="Add Check", icon="➕", content="checks_add"),
                ]),
            MenuItem(id="installments", label="Installments", icon="📅", description="Installment plans",
                children=[
                    MenuItem(id="installments-active", label="Active Plans", icon="✅", content="installments"),
                    MenuItem(id="installments-completed", label="Completed Plans", icon="✔️", content="installments_completed"),
                    MenuItem(id="installments-add", label="Add Plan", icon="➕", content="installments_add"),
                ]),
            MenuItem(id="settings", label="Settings", icon="⚙️", description="System settings",
                children=[
                    MenuItem(id="settings-general", label="General", icon="🔧", content="settings"),
                    MenuItem(id="settings-security", label="Security", icon="🔒", content="settings_security"),
                ]),
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


# =============================================================================
# Content View Widgets
# =============================================================================

class MenuContentView(Widget):
    """Base widget for a lazily loaded menu view."""

    def __init__(self, menu_item: MenuItem, **kwargs):
        super().__init__(**kwargs)
        self.menu_item = menu_item


class PreviewContentView(MenuContentView):
    """Preview content view showing menu item info."""

    def compose(self) -> ComposeResult:
        content = (
            f"# {self.menu_item.icon} {self.menu_item.label}\n\n"
            f"{self.menu_item.description}\n\n"
            f"[yellow]Press Enter or click 'Open' to launch full screen[/yellow]\n\n"
            f"[dim]Content Type: {self.menu_item.content_type}[/dim]\n"
            f"[dim]Press Ctrl+B to toggle sidebar | Ctrl+F to search[/dim]"
        )
        yield Markdown(content, classes="content-markdown")


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
        return PreviewContentView(menu_item)


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
        grid-rows: auto auto 1fr auto;
    }

    #sidebar.hidden {
        display: none;
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
    
    #quick-actions {
        height: auto;
        background: $surface-darken-2;
        padding: 1;
    }
    
    .action-btn {
        margin: 0 1;
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
    """

    BINDINGS = [
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("ctrl+1", "focus_sidebar", "Sidebar"),
        Binding("ctrl+2", "focus_content", "Content"),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        Binding("escape", "clear_search", "Clear Search"),
        Binding("ctrl+q", "logout", "Logout"),
    ]

    sidebar_visible = reactive(True)

    def __init__(self):
        super().__init__()
        self.menu_root = create_accounting_menu()
        self.menu_items_by_id, self.menu_paths_by_id = build_menu_indexes(self.menu_root)
        self.current_item: Optional[MenuItem] = None
        self.search_results: list[MenuItem] = []
        self._last_search_query = ""

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-layout"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("📋 Accounting Menu", id="sidebar-header")

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
                        yield Button("Open", id="btn-open", variant="primary")
                        yield Button("🔄 Refresh", id="btn-refresh")
                        yield Button("Toggle", id="btn-toggle-sidebar", variant="default")

                with Container(id="content-body"):
                    yield ContentRenderer(id="content-renderer")

                yield Static("Ready | Select a menu item to view details", id="content-footer")

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
        
        elif btn_id == "btn-open":
            if self.current_item:
                self._open_screen(self.current_item)
        
        elif btn_id == "btn-toggle-sidebar":
            self.action_toggle_sidebar()
    
    def _open_screen(self, item: MenuItem) -> None:
        """Open the full screen for the selected menu item."""
        screen_map = {
            "dashboard": ("tui.screens.base", "DashboardScreen"),
            "categories": ("tui.screens.categories", "CategoriesScreen"),
            "categories_add": ("tui.screens.categories", "CategoryFormScreen"),
            "sources": ("tui.screens.sources", "SourcesScreen"),
            "sources_add": ("tui.screens.sources", "SourceFormScreen"),
            "transactions": ("tui.screens.transactions", "TransactionsScreen"),
            "transactions_add": ("tui.screens.transactions", "TransactionFormScreen"),
            "reports": ("tui.screens.reports", "ReportsScreen"),
            "reports_category": ("tui.screens.reports", "CategoryReportScreen"),
            "budget": ("tui.screens.budget", "BudgetScreen"),
            "budget_rules": ("tui.screens.budget", "BudgetRulesScreen"),
            "checks": ("tui.screens.checks", "ChecksScreen"),
            "checks_received": ("tui.screens.checks", "ReceivedChecksScreen"),
            "checks_add": ("tui.screens.checks", "CheckFormScreen"),
            "installments": ("tui.screens.installments", "InstallmentsScreen"),
            "installments_completed": ("tui.screens.installments", "CompletedInstallmentsScreen"),
            "installments_add": ("tui.screens.installments", "InstallmentFormScreen"),
            "settings": ("tui.screens.settings", "SettingsScreen"),
            "settings_security": ("tui.screens.settings", "SettingsScreen"),
        }
        
        if item.content in screen_map:
            module_name, class_name = screen_map[item.content]
            try:
                import importlib
                module = importlib.import_module(module_name)
                screen_class = getattr(module, class_name)
                self.app.push_screen(screen_class())
            except Exception as e:
                self.notify(f"Error opening screen: {e}", severity="error")
        else:
            self.notify(f"Screen not implemented: {item.label}", severity="warning")
    
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
    
    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        self.sidebar_visible = not self.sidebar_visible
        try:
            sidebar = self.query_one("#sidebar", Vertical)
            if self.sidebar_visible:
                sidebar.remove_class("hidden")
            else:
                sidebar.add_class("hidden")
        except Exception:
            pass

    def action_logout(self) -> None:
        """Logout and return to login screen."""
        self.app.user = None
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        from tui.screens.auth import LoginScreen
        self.app.push_screen(LoginScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.action_quit()


# Backward compatibility
SidebarMenuScreen = SidebarAppScreen
MainMenuScreen = SidebarAppScreen
