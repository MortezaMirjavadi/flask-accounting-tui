"""
Sidebar Tree Menu for Accounting Application
Embeds screens in the right content area by mounting Screen widgets directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import importlib

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Tree, Input, Static, Header, Footer, Button, ContentSwitcher
)
from textual.widgets.tree import TreeNode
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget


# =============================================================================
# Menu Data Model
# =============================================================================

@dataclass
class MenuItem:
    id: str
    label: str
    icon: str = "📄"
    description: str = ""
    screen_module: str = ""
    screen_class: str = ""
    action: str = ""
    children: list[MenuItem] = field(default_factory=list)
    badge: Optional[str] = None
    admin_only: bool = False

    def to_tree_label(self) -> str:
        badge_str = f" [{self.badge}]" if self.badge else ""
        return f"{self.icon} {self.label}{badge_str}"

    def search(self, query: str) -> list[MenuItem]:
        results = []
        query_lower = query.lower()
        if query_lower in self.label.lower() or query_lower in self.description.lower():
            results.append(self)
        for child in self.children:
            results.extend(child.search(query))
        return results


# =============================================================================
# Menu Structure
# =============================================================================

def create_accounting_menu() -> MenuItem:
    return MenuItem(
        id="root", label="Accounting System", icon="🏠",
        children=[
            MenuItem(
                id="dashboard", label="Dashboard", icon="📊",
                description="Overview — sources and today's transactions",
                screen_module="tui.screens.base", screen_class="DashboardScreen",
            ),
            MenuItem(
                id="financial", label="Financial Management", icon="💰",
                description="Manage transactions and accounts",
                children=[
                    MenuItem(id="transactions", label="Transactions", icon="💳",
                             description="View and manage transactions",
                             children=[
                                 MenuItem(id="tx-list", label="List Transactions", icon="📋",
                                          description="View all transactions",
                                          screen_module="tui.screens.transactions", screen_class="TransactionListScreen"),
                                 MenuItem(id="tx-by-category", label="List by Category", icon="📊",
                                          description="View transactions grouped by category",
                                          screen_module="tui.screens.transactions", screen_class="TransactionByCategoryScreen"),
                                 MenuItem(id="tx-add", label="Add Transaction", icon="➕",
                                          description="Add a new transaction",
                                          screen_module="tui.screens.transactions", screen_class="TransactionAddScreen"),
                             ]),
                    MenuItem(id="sources", label="Sources", icon="🏦",
                             description="Manage financial sources",
                             children=[
                                 MenuItem(id="src-list", label="List Sources", icon="📋",
                                          description="View all sources",
                                          screen_module="tui.screens.sources", screen_class="SourceListScreen"),
                                 MenuItem(id="src-add", label="Add Source", icon="➕",
                                          description="Add a new source",
                                          screen_module="tui.screens.sources", screen_class="SourceAddScreen"),
                             ]),
                    MenuItem(id="categories", label="Categories", icon="📁",
                             description="Manage transaction categories",
                             children=[
                                 MenuItem(id="cat-list", label="List Categories", icon="📋",
                                          description="View all categories",
                                          screen_module="tui.screens.categories", screen_class="CategoryListScreen"),
                                 MenuItem(id="cat-add", label="Add Category", icon="➕",
                                          description="Add a new category",
                                          screen_module="tui.screens.categories", screen_class="CategoryAddScreen"),
                             ]),
                ]
            ),
            MenuItem(
                id="planning", label="Budget & Planning", icon="📊",
                description="Budget management and planning",
                children=[
                    MenuItem(id="budget", label="Budget", icon="💵",
                             description="Manage budgets",
                             children=[
                                 MenuItem(id="budget-tree", label="Budget Tree View", icon="🌳",
                                          description="View budget tree",
                                          screen_module="tui.screens.budget", screen_class="BudgetTreeScreen"),
                                 MenuItem(id="budget-periods", label="Budget Periods", icon="📅",
                                          description="Manage budget periods",
                                          screen_module="tui.screens.budget", screen_class="BudgetPeriodListScreen"),
                                 MenuItem(id="budget-report", label="Budget Report", icon="📈",
                                          description="View budget report",
                                          screen_module="tui.screens.budget", screen_class="BudgetReportScreen"),
                             ]),
                    MenuItem(id="calendar", label="Calendar", icon="📅",
                             description="View calendar and scheduled transactions",
                             screen_module="tui.calendar_view", screen_class="CalendarScreen"),
                ]
            ),
            MenuItem(
                id="payments", label="Payments", icon="💸",
                description="Manage checks and installments",
                children=[
                    MenuItem(id="checks", label="Checks", icon="📝",
                             description="Manage checks",
                             children=[
                                 MenuItem(id="chk-list", label="List Checks", icon="📋",
                                          description="View all checks",
                                          screen_module="tui.screens.checks", screen_class="CheckListScreen"),
                                 MenuItem(id="chk-add", label="Add Check", icon="➕",
                                          description="Add a new check",
                                          screen_module="tui.screens.checks", screen_class="CheckAddScreen"),
                             ]),
                    MenuItem(id="installments", label="Installments", icon="📆",
                             description="Manage installment payments",
                             children=[
                                 MenuItem(id="inst-list", label="List Installments", icon="📋",
                                          description="View all installment plans",
                                          screen_module="tui.screens.installments", screen_class="InstallmentListScreen"),
                                 MenuItem(id="inst-add", label="Add Installment", icon="➕",
                                          description="Add a new installment plan",
                                          screen_module="tui.screens.installments", screen_class="InstallmentAddScreen"),
                             ]),
                ]
            ),
            MenuItem(
                id="reports_section", label="Reports & Analysis", icon="📈",
                description="View reports and analytics",
                children=[
                    MenuItem(id="reports", label="Reports", icon="📊",
                             description="Generate financial reports",
                             children=[
                                 MenuItem(id="report-dashboard", label="Dashboard", icon="📊",
                                          description="Daily / Weekly / Monthly dashboard",
                                          screen_module="tui.screens.reports", screen_class="AdvancedReportScreen"),
                                 MenuItem(id="item-reports", label="Item Analytics & Inflation", icon="🔍",
                                          description="Item-level analytics, price trends, spending velocity, personal inflation tracker",
                                          screen_module="tui.screens.item_reports", screen_class="ItemReportsScreen"),
                             ]),
                ]
            ),
            MenuItem(
                id="system", label="System", icon="⚙️",
                description="System settings and account",
                children=[
                    MenuItem(id="user-mgmt", label="User Management", icon="👥",
                             description="Approve or reject user registrations",
                             screen_module="tui.screens.users", screen_class="UserManagementScreen",
                             admin_only=True),
                    MenuItem(id="settings", label="Settings", icon="🔧",
                             description="Application settings",
                             screen_module="tui.screens.settings", screen_class="SettingsScreen"),
                    MenuItem(id="logout", label="Logout", icon="🚪",
                             description="Logout from the system", action="logout"),
                    MenuItem(id="exit", label="Exit", icon="❌",
                             description="Exit application", action="exit"),
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


def _screen_class_to_label(class_name: str) -> str:
    """Convert a screen class name to a human-readable label.

    Examples: TransactionAddScreen -> Transaction Add
              SourceEditScreen -> Source Edit
              UserManagementScreen -> User Management
    """
    import re
    # Insert space before each uppercase letter that follows a lowercase letter
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", class_name)
    # Insert space before uppercase letters that follow other uppercase letters (e.g., "TwoFA" -> "Two FA")
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    # Remove trailing "Screen" if present
    spaced = re.sub(r"\s*Screen$", "", spaced)
    return spaced


# =============================================================================
# Search Tree Widget
# =============================================================================

class SearchTree(Tree):
    search_query = reactive("")

    class ItemSelected(Message):
        def __init__(self, item: MenuItem) -> None:
            self.item = item
            super().__init__()

    def __init__(self, menu_root: MenuItem, **kwargs):
        super().__init__(menu_root.label, **kwargs)
        self.menu_root = menu_root
        self._last_query = ""
        self._is_admin = True  # default: show everything until filtered
        self._build_tree(self.root, menu_root)
        self.root.expand_all()

    def _build_tree(self, tree_node: TreeNode, menu_item: MenuItem):
        for child in menu_item.children:
            if child.admin_only and not self._is_admin:
                continue
            label = child.to_tree_label()
            child_node = tree_node.add(label, data=child, allow_expand=bool(child.children))
            if child.children:
                self._build_tree(child_node, child)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data and isinstance(node.data, MenuItem):
            self.post_message(self.ItemSelected(node.data))

    def filter_tree(self, query: str):
        query = query.strip()
        if query == self._last_query:
            return

        self._last_query = query
        self.search_query = query
        self.root.remove_children()
        if not query:
            self._build_tree(self.root, self.menu_root)
            self.root.expand_all()
            return
        try:
            matches = self.menu_root.search(query)
            if matches:
                self._build_filtered_tree(self.root, self.menu_root, matches)
                self.root.expand_all()
            else:
                return
        except Exception:
            self._build_tree(self.root, self.menu_root)
            self.root.expand_all()

    def _build_filtered_tree(self, tree_node: TreeNode, menu_item: MenuItem, matches: list[MenuItem]):
        match_ids = {m.id for m in matches}
        for child in menu_item.children:
            if child.admin_only and not self._is_admin:
                continue
            should_include = child.id in match_ids or self._has_matching_descendant(child, match_ids)
            if should_include:
                label = child.to_tree_label()
                child_node = tree_node.add(label, data=child, allow_expand=bool(child.children))
                if child.children:
                    self._build_filtered_tree(child_node, child, matches)

    def _has_matching_descendant(self, item: MenuItem, match_ids: set) -> bool:
        if not item.children:
            return False
        for child in item.children:
            if child.id in match_ids:
                return True
            if self._has_matching_descendant(child, match_ids):
                return True
        return False

    def filter_admin_only(self, is_admin: bool) -> None:
        """Rebuild tree, hiding admin-only items for non-admin users."""
        self._is_admin = is_admin
        self.root.remove_children()
        self._build_tree(self.root, self.menu_root)
        self.root.expand_all()


# =============================================================================
# Content Renderer
# =============================================================================

class ContentRenderer(ContentSwitcher):
    """Cached right-pane renderer inspired by samples/sidebar.py."""

    DEFAULT_CSS = """
    ContentRenderer {
        width: 1fr;
        height: 1fr;
        min-width: 0;
        min-height: 0;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._screen_cache: dict[str, Widget] = {}
        self._message_cache: dict[str, Static] = {}
        self._loaded_screen: Widget | None = None
        self._nav_stack: list[str] = []  # widget IDs for back navigation

    def show_message(self, key: str, message: str, css_class: str = "screen-msg") -> None:
        widget_id = f"msg-{key}"
        widget = self._message_cache.get(widget_id)
        if widget is None:
            widget = Static(message, id=widget_id, classes=css_class)
            self._prepare_embedded_widget(widget)
            self._message_cache[widget_id] = widget
            self.mount(widget)
        else:
            widget.update(message)
            widget.set_classes(css_class)
        self._loaded_screen = None
        self.current = widget_id

    def show_screen(self, item: MenuItem, app) -> Widget:
        self._nav_stack.clear()  # top-level nav resets the stack
        was_cached = item.id in self._screen_cache
        screen_instance = self._screen_cache.get(item.id)
        if screen_instance is None:
            screen_instance = self._create_screen(item, app)
            screen_instance.id = f"screen-{item.id}"
            self._prepare_embedded_widget(screen_instance)
            self._screen_cache[item.id] = screen_instance
            self.mount(screen_instance)
        else:
            # Refresh data on cached screens so list screens show latest changes
            if hasattr(screen_instance, 'load_data'):
                screen_instance.load_data()
        self._loaded_screen = screen_instance
        self.current = screen_instance.id
        self.call_after_refresh(lambda: screen_instance.refresh(layout=True))
        self.call_after_refresh(self._focus_first)
        host = getattr(app, "_sidebar_host_screen", None)
        if host is not None:
            host.set_cache_status(item, was_cached)
        return screen_instance

    def show_instance(self, screen_instance, app, callback=None) -> None:
        """Load a screen instance directly into the content area."""
        # Push current screen onto the navigation stack
        if self._loaded_screen is not None:
            self._nav_stack.append(self._loaded_screen.id)

        screen_class = type(screen_instance)

        # Build embedded widget class from MRO
        attrs: dict = {}
        _skip = {"__dict__", "__weakref__", "__module__", "__doc__"}
        for base_cls in screen_class.__mro__:
            if base_cls in (Screen, Widget, object):
                break
            for name, value in base_cls.__dict__.items():
                if name not in _skip and name not in attrs:
                    attrs[name] = value

        attrs.pop("__init__", None)

        def __init__(self_inner, *args, **kwargs):
            Widget.__init__(self_inner)

        attrs["__init__"] = __init__
        attrs["_sidebar_embedded"] = True
        attrs["__module__"] = screen_class.__module__

        embedded_class = type(f"Embedded{screen_class.__name__}", (Widget,), attrs)
        embedded = embedded_class()

        # Copy instance attributes from the pushed screen
        for key, value in screen_instance.__dict__.items():
            if not key.startswith("_NodeList__") and key not in {"_parent", "_app"}:
                setattr(embedded, key, value)

        self._patch_embedded_screen_navigation(embedded, callback=callback)
        self._prepare_embedded_widget(embedded)

        instance_id = f"instance-{type(screen_instance).__name__}-{id(screen_instance)}"
        embedded.id = instance_id
        self.mount(embedded)
        self._loaded_screen = embedded
        self.current = instance_id
        self.call_after_refresh(lambda: embedded.refresh(layout=True))
        self.call_after_refresh(self._focus_first)

        # Update breadcrumb with sub-screen label
        host = getattr(app, "_sidebar_host_screen", None)
        if host is not None:
            label = _screen_class_to_label(screen_class.__name__)
            host._push_breadcrumb_label(label)

    def go_back(self) -> bool:
        """Navigate to the previous screen in the stack. Returns True if navigated."""
        while self._nav_stack:
            prev_id = self._nav_stack.pop()
            try:
                prev = self.query_one(f"#{prev_id}")
                self._loaded_screen = prev
                self.current = prev_id
                if hasattr(prev, 'load_data'):
                    prev.load_data()
                self.call_after_refresh(lambda: prev.refresh(layout=True))
                self.call_after_refresh(self._focus_first)
                # Restore breadcrumb
                host = getattr(self.app, "_sidebar_host_screen", None)
                if host is not None:
                    host._pop_breadcrumb()
                return True
            except Exception:
                continue
        return False

    def _focus_first(self) -> None:
        """Focus the first focusable widget in the loaded screen."""
        if self._loaded_screen is None:
            return
        for widget in self._loaded_screen.query("*"):
            if widget.can_focus and widget.visible:
                widget.focus()
                return
        # No focusable children (e.g. reports, calendar with only Static widgets).
        # Focus the screen container itself so its key bindings receive events.
        self._loaded_screen.can_focus = True
        self._loaded_screen.focus()

    def refresh_current_screen(self) -> None:
        if self._loaded_screen is not None:
            self.call_after_refresh(lambda: self._loaded_screen.refresh(layout=True))

    def _create_screen(self, item: MenuItem, app) -> Widget:
        module = importlib.import_module(item.screen_module)
        screen_class = getattr(module, item.screen_class)
        embedded_class = self._make_embedded_widget_class(screen_class)

        if item.screen_class == "CalendarScreen":
            user = getattr(app, "user", None)
            user_id = user.get("id") if user else None
            if user_id is None:
                raise RuntimeError("No user logged in")
            screen = embedded_class(user_id=user_id)
        else:
            screen = embedded_class()

        self._patch_embedded_screen_navigation(screen)
        return screen

    def _make_embedded_widget_class(self, screen_class: type) -> type[Widget]:
        attrs: dict = {}
        _skip = {"__dict__", "__weakref__", "__module__", "__doc__"}

        # Walk the MRO and copy members from the screen class
        # and its custom bases (stop before Screen/Widget/object)
        for base_cls in screen_class.__mro__:
            if base_cls in (Screen, Widget, object):
                break
            for name, value in base_cls.__dict__.items():
                if name not in _skip and name not in attrs:
                    attrs[name] = value

        original_init = attrs.pop("__init__", None)

        def __init__(self, *args, **kwargs):
            Widget.__init__(self)
            if original_init is not None:
                self._run_screen_init(original_init, *args, **kwargs)

        def _run_screen_init(self, init_method, *args, **kwargs):
            screen_instance = screen_class(*args, **kwargs)
            for key, value in screen_instance.__dict__.items():
                if not key.startswith("_NodeList__") and key not in {"_parent", "_app"}:
                    setattr(self, key, value)

        attrs["__init__"] = __init__
        attrs["_run_screen_init"] = _run_screen_init
        attrs["_sidebar_embedded"] = True
        attrs["__module__"] = screen_class.__module__
        return type(f"Embedded{screen_class.__name__}", (Widget,), attrs)

    def _prepare_embedded_widget(self, widget: Widget) -> Widget:
        widget.styles.width = "100%"
        widget.styles.height = "100%"
        widget.styles.min_width = 0
        widget.styles.min_height = 0
        widget.styles.padding = 0
        widget.styles.margin = 0
        try:
            widget.styles.align = ("left", "top")
            widget.styles.content_align = ("left", "top")
        except Exception:
            pass
        return widget

    def _patch_embedded_screen_navigation(self, screen: Widget, callback=None) -> None:
        setattr(screen, "_sidebar_embedded", True)
        _cb_fired = [False]

        def _fire_callback(result):
            if callback and not _cb_fired[0]:
                _cb_fired[0] = True
                callback(result)

        def _navigate_back():
            host = getattr(screen.app, "_sidebar_host_screen", None)
            if host is not None:
                renderer = host.query_one(ContentRenderer)
                if not renderer.go_back():
                    host.query_one("#menu-tree", SearchTree).focus()

        def embedded_go_back() -> None:
            _fire_callback(None)
            _navigate_back()

        def embedded_dismiss(*args, **kwargs) -> None:
            _fire_callback(args[0] if args else None)
            _navigate_back()

        if hasattr(screen, "action_go_back"):
            screen.action_go_back = embedded_go_back
        screen.dismiss = embedded_dismiss


# =============================================================================
# Main Sidebar Screen
# =============================================================================

class SidebarMainMenuScreen(Screen):
    CSS = """
    SidebarMainMenuScreen {
        layout: horizontal;
        align: left top;
        content-align: left top;
    }

    #sidebar {
        width: 40;
        min-width: 40;
        height: 1fr;
        border-right: solid $primary;
        background: $surface-darken-1;
    }

    #sidebar.collapsed {
        width: 0;
        min-width: 0;
        padding: 0;
        border: none;
    }

    #sidebar-header {
        height: 3;
        width: 100%;
        background: $primary-darken-2;
        align: center middle;
    }

    #search-container {
        width: 100%;
        height: 3;
        padding: 0 1;
    }

    #search-input {
        width: 100%;
        border: solid $primary-darken-1;
    }

    #menu-tree {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-2;
        background: $surface;
    }

    #tree-controls {
        width: 100%;
        height: auto;
        padding: 1;
    }

    #tree-controls Button {
        margin: 0 1 0 0;
    }

    #content-area {
        width: 1fr;
        height: 1fr;
        background: $surface;
        layout: vertical;
        align: left top;
        content-align: left top;
        min-width: 0;
        min-height: 0;
    }

    #breadcrumb {
        height: 1;
        width: 100%;
        color: $text-muted;
        padding: 0 2;
        margin: 1 0 0 0;
    }

    #content-title {
        text-style: bold;
        color: $primary-lighten-2;
        text-align: center;
        margin: 0 0 1 0;
        height: 1;
    }

    #content-description {
        color: $text;
        text-align: center;
        margin: 0 0 1 0;
        height: auto;
        padding: 0 2;
    }

    #screen-container {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        padding: 0;
        min-width: 0;
        min-height: 0;
    }

    #screen-container Header,
    #screen-container Footer {
        display: none;
    }

    .screen-msg {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        padding: 2;
    }

    .screen-error {
        width: 100%;
        height: auto;
        color: $error;
        padding: 2;
        border: round $error;
        background: $surface-darken-1;
    }

    /* Make embedded screen content fill the container */
    #screen-container .wide_panel {
        width: 100%;
        height: 1fr;
        border: none;
        align: left top;
    }

    #screen-container .main_panel {
        width: 100%;
        border: none;
        align: left top;
    }

    #screen-container .center_screen {
        content-align: left top;
    }

    #screen-container .split_row {
        height: 1fr;
    }

    /* Dashboard layout overrides for embedded mode */
    #screen-container #dash-split {
        width: 100%;
        height: 1fr;
    }

    #screen-container #dash-left {
        width: 45%;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 0 1;
        min-width: 0;
    }

    #screen-container #dash-right {
        width: 55%;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 0 1;
        min-width: 0;
    }

    #screen-container .dash-section-title {
        width: 1fr;
        height: 3;
        text-style: bold;
        color: $primary;
        content-align: left middle;
        padding: 0 0 0 1;
    }

    #screen-container #balance-container {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        align: center middle;
    }

    #screen-container #balance-digits {
        width: auto;
        height: auto;
        text-align: center;
        color: $success;
        text-style: bold;
    }

    #screen-container .dash-btn-row {
        height: 3;
        width: 100%;
        margin: 0;
        align: left middle;
    }

    #screen-container .dash-btn-row Button {
        width: auto;
        margin: 0 1 0 0;
        min-width: 18;
    }

    #screen-container #tx-summary-row {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
    }

    #screen-container .tx-metric {
        width: 1fr;
        height: auto;
        align: center middle;
    }

    #screen-container .tx-metric-digits {
        width: auto;
        height: auto;
        text-align: center;
    }

    #screen-container .income-color {
        color: $success;
    }

    #screen-container .cost-color {
        color: $error;
    }

    #screen-container .net-color {
        color: $primary;
    }

    #screen-container .left_pane {
        height: 1fr;
    }

    #screen-container .right_pane {
        height: 1fr;
    }

    #screen-container .bottom_bar {
        height: 2;
        width: 100%;
    }

    #screen-container .form_panel {
        width: 100%;
        height: 1fr;
        border: none;
        overflow: hidden;
        min-height: 0;
    }

    #screen-container .form_scroll {
        height: 1fr;
        min-height: 0;
    }

    #screen-container .report_scroll {
        height: 1fr;
        min-height: 0;
    }

    #screen-container .button_row {
        height: auto;
        min-height: 3;
    }

    #screen-container Screen {
        display: block;
        width: 100%;
        height: 100%;
        min-width: 0;
        min-height: 0;
        align: left top;
        content-align: left top;
    }
    """

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("ctrl+g", "focus_content", "Focus Content"),
        Binding("escape", "clear_search", "Clear"),
        Binding("q", "quit", "Exit"),
        Binding("l", "logout", "Logout"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu_root = create_accounting_menu()
        self.menu_items_by_id, self.menu_paths_by_id = build_menu_indexes(self.menu_root)
        self.current_item: Optional[MenuItem] = None
        self._sidebar_visible = True
        self._breadcrumb_text: str = ""
        self._breadcrumb_stack: list[str] = []

    def _refresh_loaded_content(self) -> None:
        self.query_one(ContentRenderer).refresh_current_screen()

    def _set_breadcrumb_from_path(self, path: list[MenuItem]) -> None:
        """Render full breadcrumb from a list of MenuItems."""
        crumbs = []
        for i, item in enumerate(path):
            if i > 0:
                crumbs.append("[dim] > [/dim]")
            crumbs.append(f"{item.icon} {item.label}")
        self._breadcrumb_text = "".join(crumbs)
        self.query_one("#breadcrumb", Static).update(self._breadcrumb_text)

    def _push_breadcrumb_label(self, label: str) -> None:
        """Append a sub-screen label to the breadcrumb (e.g. for Add/Edit screens)."""
        self._breadcrumb_stack.append(self._breadcrumb_text)
        self.query_one("#breadcrumb", Static).update(
            f"{self._breadcrumb_text}[dim] > [/dim]{label}"
        )

    def _pop_breadcrumb(self) -> None:
        """Restore the previous breadcrumb state."""
        if self._breadcrumb_stack:
            self._breadcrumb_text = self._breadcrumb_stack.pop()
            self.query_one("#breadcrumb", Static).update(self._breadcrumb_text)

    def action_toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        try:
            sidebar = self.query_one("#sidebar")
            if self._sidebar_visible:
                sidebar.remove_class("collapsed")
            else:
                sidebar.add_class("collapsed")
            self._refresh_loaded_content()
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="sidebar"):
            # yield Static("⚡ Personal Accounting", id="sidebar-header")
            with Container(id="search-container"):
                yield Input(placeholder="Search menu...", id="search-input")
            yield SearchTree(self.menu_root, id="menu-tree")
            with Horizontal(id="tree-controls"):
                yield Button("Expand", id="btn-expand", variant="primary")
                yield Button("Collapse", id="btn-collapse", variant="default")

        with Vertical(id="content-area"):
            yield Static("", id="breadcrumb")
            yield Static("", id="content-title")
            yield Static("", id="content-description")
            with Container(id="screen-container"):
                yield ContentRenderer(id="content-renderer")

        yield Footer()

    def on_mount(self):
        self.app._sidebar_host_screen = self
        user = getattr(self.app, "user", None)
        username = user.get("username", "User") if user else "User"
        is_admin = user.get("is_admin", False) if user else False
        self.query_one("#content-title", Static).update(f"Welcome, {username}!")

        # Hide admin-only menu items for non-admin users
        self.query_one("#menu-tree", SearchTree).filter_admin_only(is_admin)

        # Auto-load dashboard as the default view
        dashboard_item = None
        for child in self.menu_root.children:
            if child.id == "dashboard":
                dashboard_item = child
                break
        if dashboard_item and dashboard_item.screen_module:
            self.current_item = dashboard_item
            self._set_breadcrumb_from_path(
                self.menu_paths_by_id.get(dashboard_item.id, [dashboard_item])
            )
            self.query_one("#content-description", Static).update(dashboard_item.description or "")
            self._load_screen(dashboard_item)
        else:
            self.query_one("#content-description", Static).update(
                "Select a menu item from the sidebar."
            )
            self.query_one(ContentRenderer).show_message(
                "welcome",
                "[bold green]Welcome to Terminal Accounting![/bold green]\n\n"
                "Select a menu item from the sidebar to get started.\n\n"
                "[dim]Press Ctrl+B to toggle sidebar[/dim]",
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query_one("#menu-tree", SearchTree).filter_tree(event.value)

    def on_search_tree_item_selected(self, event: SearchTree.ItemSelected) -> None:
        item = event.item
        self.current_item = item

        self._set_breadcrumb_from_path(
            self.menu_paths_by_id.get(item.id, [item])
        )
        self.query_one("#content-title", Static).update(f"{item.icon} {item.label}")
        self.query_one("#content-description", Static).update(item.description or "")

        if item.action == "logout":
            self.action_logout()
            return
        elif item.action == "exit":
            self.app.action_quit()
            return

        if item.screen_module and item.screen_class:
            self._load_screen(item)
        else:
            self._show_message(
                f"{item.icon} {item.label}\n\n"
                f"{item.description or 'Expand to see options.'}"
            )

    def _load_screen(self, item: MenuItem) -> None:
        """Load a cached screen in the content switcher."""
        try:
            self.app._sidebar_embed_loading = True
            self.query_one(ContentRenderer).show_screen(item, self.app)
        except Exception as e:
            self._show_message(f"[error]Error loading {item.label}: {e}[/error]", is_error=True)
        finally:
            self.app._sidebar_embed_loading = False

    def _show_message(self, message: str, is_error: bool = False) -> None:
        css_class = "screen-error" if is_error else "screen-msg"
        key = f"message-{abs(hash((message, css_class)))}"
        self.query_one(ContentRenderer).show_message(key, message, css_class=css_class)

    def set_cache_status(self, item: MenuItem, was_cached: bool) -> None:
        state = "reused from cache" if was_cached else "created and cached"
        self.query_one("#content-description", Static).update(
            f"{item.description or item.label}  |  [green]{state}[/green]"
        )

    def show_embedded_error(self, title: str, message: str, is_error: bool = False) -> None:
        text = f"{title}\n\n{message}"
        self._show_message(text, is_error=is_error or title.lower() == "error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-expand":
            self.query_one("#menu-tree", SearchTree).root.expand_all()
        elif btn_id == "btn-collapse":
            self.query_one("#menu-tree", SearchTree).root.collapse_all()

    def action_focus_search(self) -> None:
        if not self._sidebar_visible:
            self.action_toggle_sidebar()
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        self.query_one("#search-input", Input).value = ""
        self.query_one("#menu-tree", SearchTree).filter_tree("")

    def action_focus_content(self) -> None:
        """Focus the first focusable widget in the content area."""
        content_area = self.query_one("#content-area")
        for widget in content_area.query("*"):
            if widget.can_focus and widget.visible:
                widget.focus()
                return

    def action_logout(self):
        self.app.user = None
        self.app._sidebar_host_screen = None
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        from tui.screens.auth import LoginScreen
        self.app.push_screen(LoginScreen())
