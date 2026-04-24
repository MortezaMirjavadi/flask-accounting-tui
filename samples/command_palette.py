"""
Advanced Custom Command Palette Example
Features: fuzzy search, categorized commands, keyboard shortcuts, 
          dynamic commands, action system, and rich previews
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Optional, Any
from enum import Enum, auto

from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Static, Input, ListView, ListItem, Label, 
    Header, Footer, DataTable, Tree, Markdown
)
from textual.containers import Horizontal, Vertical, Container, Grid
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.color import Color


class CommandCategory(Enum):
    """Command categories with associated styling."""
    FILE = ("📁 File", "#61afef")
    EDIT = ("✏️  Edit", "#98c379")
    VIEW = ("👁 View", "#e5c07b")
    NAVIGATE = ("🧭 Navigate", "#c678dd")
    TOOLS = ("🛠 Tools", "#56b6c2")
    SYSTEM = ("⚙️ System", "#e06c75")
    CUSTOM = ("⭐ Custom", "#d19a66")

    def __init__(self, icon: str, color: str):
        self.icon = icon
        self.color = color


@dataclass
class Command:
    """Represents a command in the palette."""
    id: str
    title: str
    description: str = ""
    category: CommandCategory = CommandCategory.CUSTOM
    shortcut: str = ""
    icon: str = "›"
    action: Optional[Callable] = None
    action_params: dict = field(default_factory=dict)
    enabled: bool = True
    context: Optional[str] = None  # When to show this command
    
    # Scoring for fuzzy matching
    score: float = 0.0
    
    def __post_init__(self):
        if not self.icon:
            self.icon = "›"
    
    @property
    def display_title(self) -> str:
        """Formatted title with icon."""
        return f"{self.icon} {self.title}"
    
    @property
    def search_text(self) -> str:
        """Text used for fuzzy matching."""
        return f"{self.title} {self.description} {self.category.name}".lower()


class FuzzyMatcher:
    """Advanced fuzzy matching with scoring."""
    
    @staticmethod
    def match(query: str, text: str) -> tuple[bool, float]:
        """
        Fuzzy match query against text.
        Returns (matched, score) where higher score is better.
        """
        if not query:
            return True, 1.0
        
        query = query.lower()
        text = text.lower()
        
        # Exact match
        if query == text:
            return True, 1000.0
        
        # Contains exact substring
        if query in text:
            return True, 100.0 + len(query) / len(text) * 10
        
        # Fuzzy match
        query_idx = 0
        text_idx = 0
        matches = []
        gaps = 0
        consecutive = 0
        max_consecutive = 0
        
        while query_idx < len(query) and text_idx < len(text):
            if query[query_idx] == text[text_idx]:
                matches.append(text_idx)
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
                query_idx += 1
            else:
                if matches:  # Gap after first match
                    gaps += 1
                consecutive = 0
            text_idx += 1
        
        if query_idx < len(query):
            return False, 0.0
        
        # Calculate score
        score = 0.0
        
        # Bonus for early matches
        if matches:
            score += 50.0 / (matches[0] + 1)
        
        # Bonus for consecutive matches
        score += max_consecutive * 10
        
        # Penalty for gaps
        score -= gaps * 5
        
        # Bonus for shorter overall match span
        if len(matches) > 1:
            span = matches[-1] - matches[0]
            score += max(0, 20 - span * 0.5)
        
        # Bonus for matching start of words
        for idx in matches:
            if idx == 0 or text[idx - 1] in ' _-/':
                score += 15
        
        return True, max(0, score)


class CommandPaletteScreen(ModalScreen[Optional[Command]]):
    """Custom command palette with advanced features."""
    
    DEFAULT_CSS = """
    CommandPaletteScreen {
        align: center middle;
    }
    
    #palette-container {
        width: 80;
        height: 35;
        border: thick $background 80%;
        background: $surface;
        padding: 0;
    }
    
    #palette-header {
        height: 3;
        background: $primary-darken-2;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }
    
    #search-container {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
    }
    
    #search-input {
        border: none;
        background: $surface;
        color: $text;
        height: 1;
        margin: 1 0;
    }
    
    #search-input:focus {
        border: none;
    }
    
    #results-container {
        height: 1fr;
        overflow: hidden;
    }
    
    #category-sidebar {
        width: 20;
        background: $surface-darken-1;
        border-right: solid $primary-darken-2;
    }
    
    .category-item {
        padding: 0 1;
        height: 1;
        color: $text-muted;
    }
    
    .category-item.active {
        background: $primary-darken-2;
        color: $text;
        text-style: bold;
    }
    
    #command-list {
        width: 1fr;
        height: 100%;
        border: none;
        background: transparent;
    }
    
    CommandPaletteScreen ListItem {
        height: auto;
        padding: 0;
        background: transparent;
    }
    
    CommandPaletteScreen ListItem.--highlight {
        background: $primary-darken-2;
    }
    
    #command-item {
        height: auto;
        padding: 0 1;
    }
    
    .command-title {
        text-style: bold;
    }
    
    .command-description {
        color: $text-muted;
        text-style: italic;
    }
    
    .command-shortcut {
        color: $success;
        text-style: bold;
    }
    
    .command-context {
        color: $warning;
    }
    
    #preview-panel {
        width: 30;
        background: $surface-darken-1;
        border-left: solid $primary-darken-2;
        padding: 1;
    }
    
    #preview-title {
        text-style: bold underline;
        color: $primary;
        height: 1;
        margin-bottom: 1;
    }
    
    #empty-state {
        display: block;
        text-align: center;
        color: $text-muted;
        padding: 2;
    }
    
    #no-results {
        display: none;
        text-align: center;
        color: $error;
        padding: 2;
    }
    
    #footer-hints {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("tab", "next_category", "Next Category", show=False),
        Binding("shift+tab", "prev_category", "Prev Category", show=False),
    ]
    
    def __init__(
        self,
        commands: list[Command],
        title: str = "Command Palette",
        placeholder: str = "Type a command...",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.all_commands = commands
        self.palette_title = title
        self.placeholder = placeholder
        self.filtered_commands: list[Command] = []
        self.selected_category: Optional[CommandCategory] = None
        self.matcher = FuzzyMatcher()
        
    def compose(self) -> ComposeResult:
        with Container(id="palette-container"):
            # Header
            yield Static(self.palette_title, id="palette-header")
            
            # Search input
            with Container(id="search-container"):
                yield Input(
                    placeholder=self.placeholder,
                    id="search-input"
                )
            
            # Main content area
            with Horizontal(id="results-container"):
                # Category filter sidebar
                with Vertical(id="category-sidebar"):
                    yield Static("Categories", classes="sidebar-header")
                    for cat in CommandCategory:
                        is_active = cat == self.selected_category
                        classes = "category-item active" if is_active else "category-item"
                        yield Static(
                            f"{cat.icon} {cat.name.title()}",
                            classes=classes,
                            id=f"cat-{cat.name}"
                        )
                
                # Command list
                yield ListView(id="command-list")
                
                # Preview panel
                with Vertical(id="preview-panel"):
                    yield Static("Preview", id="preview-title")
                    yield Static("", id="preview-content")
            
            # Empty state
            yield Static(
                "Start typing to search commands...\n"
                "Use ↑↓ to navigate, Enter to select",
                id="empty-state"
            )
            
            # No results
            yield Static("No commands found", id="no-results")
            
            # Footer hints
            yield Static(
                "↑↓ Navigate  |  Enter Select  |  Tab Category  |  Esc Close",
                id="footer-hints"
            )
    
    def on_mount(self) -> None:
        """Initialize the palette."""
        self.query_one("#search-input", Input).focus()
        self._update_category_highlight()
        self._show_empty_state(True)
    
    def _show_empty_state(self, show: bool) -> None:
        """Toggle empty state visibility."""
        empty = self.query_one("#empty-state", Static)
        empty.display = show
        list_view = self.query_one("#command-list", ListView)
        list_view.display = not show
    
    def _show_no_results(self, show: bool) -> None:
        """Toggle no results message."""
        no_results = self.query_one("#no-results", Static)
        no_results.display = show
        list_view = self.query_one("#command-list", ListView)
        list_view.display = not show
    
    def _update_category_highlight(self) -> None:
        """Update category sidebar highlighting."""
        for cat in CommandCategory:
            elem = self.query_one(f"#cat-{cat.name}", Static)
            if cat == self.selected_category:
                elem.add_class("active")
            else:
                elem.remove_class("active")
    
    def _filter_commands(self, query: str) -> list[Command]:
        """Filter and score commands based on query."""
        results = []
        
        for cmd in self.all_commands:
            # Skip disabled commands
            if not cmd.enabled:
                continue
            
            # Category filter
            if self.selected_category and cmd.category != self.selected_category:
                continue
            
            # Fuzzy match
            matched, score = self.matcher.match(query, cmd.search_text)
            if matched:
                cmd.score = score
                results.append(cmd)
        
        # Sort by score descending
        results.sort(key=lambda c: c.score, reverse=True)
        return results
    
    def _create_command_item(self, cmd: Command, query: str) -> ListItem:
        """Create a rich list item for a command."""
        # Highlight matching characters
        title = self._highlight_matches(cmd.title, query)
        desc = self._highlight_matches(cmd.description, query) if cmd.description else ""
        
        # Build content
        content = f"[{cmd.category.color}]{cmd.icon}[/{cmd.category.color}] "
        content += f"[bold]{title}[/bold]"
        
        if desc:
            content += f"\n[dim italic]{desc}[/dim italic]"
        
        # Footer line with shortcut and context
        footer_parts = []
        if cmd.shortcut:
            footer_parts.append(f"[green]{cmd.shortcut}[/green]")
        if cmd.context:
            footer_parts.append(f"[yellow]{cmd.context}[/yellow]")
        
        if footer_parts:
            content += f"\n{' • '.join(footer_parts)}"
        
        # Category badge
        content += f"\n[{cmd.category.color} dim]{cmd.category.icon} {cmd.category.name}[/]"
        
        item = Static(content, id="command-item")
        return ListItem(item)
    
    def _highlight_matches(self, text: str, query: str) -> str:
        """Highlight matching characters in text."""
        if not query:
            return text
        
        result = []
        query_lower = query.lower()
        text_lower = text.lower()
        query_idx = 0
        
        for char in text:
            if query_idx < len(query_lower) and char.lower() == query_lower[query_idx]:
                result.append(f"[bold reverse]{char}[/bold reverse]")
                query_idx += 1
            else:
                result.append(char)
        
        return "".join(result)
    
    def _update_preview(self, cmd: Optional[Command]) -> None:
        """Update preview panel for selected command."""
        preview_title = self.query_one("#preview-title", Static)
        preview_content = self.query_one("#preview-content", Static)
        
        if cmd is None:
            preview_title.update("Preview")
            preview_content.update("Select a command to see details")
            return
        
        preview_title.update(f"{cmd.icon} {cmd.title}")
        
        content = f"""[bold]Description:[/bold]
{cmd.description or 'No description'}

[bold]Category:[/bold] {cmd.category.icon} {cmd.category.name}

[bold]ID:[/bold] [dim]{cmd.id}[/dim]
"""
        if cmd.shortcut:
            content += f"\n[bold]Shortcut:[/bold] [green]{cmd.shortcut}[/green]"
        if cmd.context:
            content += f"\n[bold]Context:[/bold] [yellow]{cmd.context}[/yellow]"
        
        preview_content.update(content)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()
        
        if not query and not self.selected_category:
            self._show_empty_state(True)
            self._show_no_results(False)
            self.filtered_commands = []
            return
        
        self._show_empty_state(False)
        
        self.filtered_commands = self._filter_commands(query)
        
        list_view = self.query_one("#command-list", ListView)
        list_view.clear()
        
        if not self.filtered_commands:
            self._show_no_results(True)
            self._update_preview(None)
            return
        
        self._show_no_results(False)
        
        for cmd in self.filtered_commands:
            list_view.append(self._create_command_item(cmd, query))
        
        # Select first item and update preview
        if list_view.children:
            list_view.index = 0
            self._update_preview(self.filtered_commands[0])
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update preview when selection changes."""
        if event.list_view.id == "command-list" and self.filtered_commands:
            idx = event.list_view.index
            if 0 <= idx < len(self.filtered_commands):
                self._update_preview(self.filtered_commands[idx])
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle command selection."""
        if self.filtered_commands:
            idx = event.list_view.index
            if 0 <= idx < len(self.filtered_commands):
                self.dismiss(self.filtered_commands[idx])
    
    def action_cursor_up(self) -> None:
        """Move selection up."""
        list_view = self.query_one("#command-list", ListView)
        if list_view.display and list_view.children:
            list_view.action_cursor_up()
    
    def action_cursor_down(self) -> None:
        """Move selection down."""
        list_view = self.query_one("#command-list", ListView)
        if list_view.display and list_view.children:
            list_view.action_cursor_down()
    
    def action_page_up(self) -> None:
        """Page up in results."""
        list_view = self.query_one("#command-list", ListView)
        if list_view.display:
            for _ in range(5):
                list_view.action_cursor_up()
    
    def action_page_down(self) -> None:
        """Page down in results."""
        list_view = self.query_one("#command-list", ListView)
        if list_view.display:
            for _ in range(5):
                list_view.action_cursor_down()
    
    def action_select(self) -> None:
        """Select current item."""
        list_view = self.query_one("#command-list", ListView)
        if list_view.display and self.filtered_commands:
            idx = list_view.index
            if 0 <= idx < len(self.filtered_commands):
                self.dismiss(self.filtered_commands[idx])
    
    def action_next_category(self) -> None:
        """Cycle to next category."""
        categories = list(CommandCategory)
        if self.selected_category is None:
            self.selected_category = categories[0]
        else:
            idx = categories.index(self.selected_category)
            self.selected_category = categories[(idx + 1) % len(categories)]
        
        self._update_category_highlight()
        self._refresh_with_category()
    
    def action_prev_category(self) -> None:
        """Cycle to previous category."""
        categories = list(CommandCategory)
        if self.selected_category is None:
            self.selected_category = categories[-1]
        else:
            idx = categories.index(self.selected_category)
            self.selected_category = categories[(idx - 1) % len(categories)]
        
        self._update_category_highlight()
        self._refresh_with_category()
    
    def _refresh_with_category(self) -> None:
        """Refresh results with current category filter."""
        input_widget = self.query_one("#search-input", Input)
        # Trigger refresh by re-emitting current value
        self.on_input_changed(Input.Changed(input_widget, input_widget.value))
    
    def on_click(self, event) -> None:
        """Handle clicks on category items."""
        # Check if a category was clicked
        for cat in CommandCategory:
            try:
                elem = self.query_one(f"#cat-{cat.name}", Static)
                if elem.mouse_over:
                    self.selected_category = cat if self.selected_category != cat else None
                    self._update_category_highlight()
                    self._refresh_with_category()
                    return
            except Exception:
                pass


class MainApp(App):
    """Demo application showcasing the custom command palette."""
    
    CSS = """
    Screen { align: center middle; }
    
    #main-content {
        width: 60;
        height: auto;
        border: thick $primary;
        padding: 1;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 3;
    }
    
    #info {
        text-align: center;
        color: $text-muted;
    }
    
    #recent-commands {
        height: 10;
        border: solid $primary-darken-2;
        margin-top: 1;
        padding: 1;
    }
    
    .recent-item {
        color: $success;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+k", "command_palette", "Command Palette"),
        Binding("ctrl+shift+p", "command_palette", "Command Palette", show=False),
        Binding("ctrl+n", "new_file", "New File"),
        Binding("ctrl+o", "open_file", "Open File"),
        Binding("ctrl+s", "save_file", "Save"),
    ]
    
    def __init__(self):
        super().__init__()
        self.recent_commands: list[str] = []
        self.commands = self._build_commands()
        self.file_count = 0
        self.edit_history: list[str] = []
    
    def _build_commands(self) -> list[Command]:
        """Build the command registry."""
        return [
            # File commands
            Command(
                id="file.new",
                title="New File",
                description="Create a new empty file",
                category=CommandCategory.FILE,
                shortcut="Ctrl+N",
                icon="📄",
                action=self.action_new_file,
            ),
            Command(
                id="file.new_window",
                title="New Window",
                description="Open a new application window",
                category=CommandCategory.FILE,
                shortcut="Ctrl+Shift+N",
                icon="🗔",
            ),
            Command(
                id="file.open",
                title="Open File...",
                description="Open an existing file from disk",
                category=CommandCategory.FILE,
                shortcut="Ctrl+O",
                icon="📂",
                action=self.action_open_file,
            ),
            Command(
                id="file.open_recent",
                title="Open Recent",
                description="Reopen a recently used file",
                category=CommandCategory.FILE,
                icon="🕐",
                context="5 recent files",
            ),
            Command(
                id="file.save",
                title="Save",
                description="Save the current file",
                category=CommandCategory.FILE,
                shortcut="Ctrl+S",
                icon="💾",
                action=self.action_save_file,
            ),
            Command(
                id="file.save_as",
                title="Save As...",
                description="Save with a new name or location",
                category=CommandCategory.FILE,
                shortcut="Ctrl+Shift+S",
                icon="💾",
            ),
            Command(
                id="file.close",
                title="Close File",
                description="Close the current file",
                category=CommandCategory.FILE,
                shortcut="Ctrl+W",
                icon="🗙",
            ),
            
            # Edit commands
            Command(
                id="edit.undo",
                title="Undo",
                description="Reverse the last action",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+Z",
                icon="↶",
            ),
            Command(
                id="edit.redo",
                title="Redo",
                description="Reapply the last undone action",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+Y",
                icon="↷",
            ),
            Command(
                id="edit.cut",
                title="Cut",
                description="Remove selection and copy to clipboard",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+X",
                icon="✂",
            ),
            Command(
                id="edit.copy",
                title="Copy",
                description="Copy selection to clipboard",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+C",
                icon="📋",
            ),
            Command(
                id="edit.paste",
                title="Paste",
                description="Insert from clipboard",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+V",
                icon="📋",
            ),
            Command(
                id="edit.find",
                title="Find and Replace...",
                description="Search and replace text in document",
                category=CommandCategory.EDIT,
                shortcut="Ctrl+H",
                icon="🔍",
            ),
            
            # View commands
            Command(
                id="view.toggle_sidebar",
                title="Toggle Sidebar",
                description="Show or hide the side panel",
                category=CommandCategory.VIEW,
                shortcut="Ctrl+B",
                icon="◫",
            ),
            Command(
                id="view.toggle_terminal",
                title="Toggle Integrated Terminal",
                description="Show or hide the terminal panel",
                category=CommandCategory.VIEW,
                shortcut="Ctrl+`",
                icon="🖥",
            ),
            Command(
                id="view.zoom_in",
                title="Zoom In",
                description="Increase the display scale",
                category=CommandCategory.VIEW,
                shortcut="Ctrl+=",
                icon="🔎+",
            ),
            Command(
                id="view.zoom_out",
                title="Zoom Out",
                description="Decrease the display scale",
                category=CommandCategory.VIEW,
                shortcut="Ctrl+-",
                icon="🔎-",
            ),
            Command(
                id="view.fullscreen",
                title="Toggle Full Screen",
                description="Enter or exit full screen mode",
                category=CommandCategory.VIEW,
                shortcut="F11",
                icon="⛶",
            ),
            
            # Navigate commands
            Command(
                id="nav.goto_file",
                title="Go to File...",
                description="Quickly open a file by name",
                category=CommandCategory.NAVIGATE,
                shortcut="Ctrl+P",
                icon="🚀",
            ),
            Command(
                id="nav.goto_line",
                title="Go to Line...",
                description="Jump to a specific line number",
                category=CommandCategory.NAVIGATE,
                shortcut="Ctrl+G",
                icon="#",
            ),
            Command(
                id="nav.goto_symbol",
                title="Go to Symbol...",
                description="Jump to a function or variable",
                category=CommandCategory.NAVIGATE,
                shortcut="Ctrl+Shift+O",
                icon="⚛",
            ),
            Command(
                id="nav.back",
                title="Go Back",
                description="Navigate to previous location",
                category=CommandCategory.NAVIGATE,
                shortcut="Alt+Left",
                icon="←",
            ),
            Command(
                id="nav.forward",
                title="Go Forward",
                description="Navigate to next location",
                category=CommandCategory.NAVIGATE,
                shortcut="Alt+Right",
                icon="→",
            ),
            
            # Tools commands
            Command(
                id="tools.command_palette",
                title="Command Palette",
                description="Access all available commands",
                category=CommandCategory.TOOLS,
                shortcut="Ctrl+Shift+P",
                icon="⌘",
                action=self.action_command_palette,
            ),
            Command(
                id="tools.terminal",
                title="New Terminal",
                description="Open a new terminal instance",
                category=CommandCategory.TOOLS,
                shortcut="Ctrl+Shift+`",
                icon="⌨",
            ),
            Command(
                id="tools.snippets",
                title="Insert Snippet",
                description="Insert a code template",
                category=CommandCategory.TOOLS,
                icon="🧩",
            ),
            Command(
                id="tools.format",
                title="Format Document",
                description="Auto-format the entire document",
                category=CommandCategory.TOOLS,
                shortcut="Shift+Alt+F",
                icon="✨",
            ),
            
            # System commands
            Command(
                id="sys.settings",
                title="Settings",
                description="Open application preferences",
                category=CommandCategory.SYSTEM,
                shortcut="Ctrl+,",
                icon="⚙",
            ),
            Command(
                id="sys.extensions",
                title="Extensions",
                description="Manage installed extensions",
                category=CommandCategory.SYSTEM,
                icon="🧩",
            ),
            Command(
                id="sys.keyboard",
                title="Keyboard Shortcuts",
                description="Customize key bindings",
                category=CommandCategory.SYSTEM,
                icon="⌨",
            ),
            Command(
                id="sys.reload",
                title="Reload Window",
                description="Restart the application",
                category=CommandCategory.SYSTEM,
                shortcut="Ctrl+R",
                icon="↻",
            ),
            
            # Dynamic/contextual commands
            Command(
                id="custom.git_commit",
                title="Git: Commit",
                description="Commit staged changes",
                category=CommandCategory.CUSTOM,
                shortcut="Ctrl+Enter",
                icon="🌿",
                context="Git repo detected",
            ),
            Command(
                id="custom.git_push",
                title="Git: Push",
                description="Push commits to remote",
                category=CommandCategory.CUSTOM,
                icon="🚀",
                context="Unpushed commits",
            ),
        ]
    
    def compose(self) -> ComposeResult:
        with Container(id="main-content"):
            yield Static("Custom Command Palette Demo", id="title")
            yield Static("Press Ctrl+K or Ctrl+Shift+P to open", id="info")
            
            with Vertical(id="recent-commands"):
                yield Static("Recent Commands:", classes="recent-header")
                yield Static("No commands yet...", id="recent-list")
        
        yield Header()
        yield Footer()
    
    def _add_recent(self, cmd: Command) -> None:
        """Add command to recent history."""
        self.recent_commands.insert(0, f"{cmd.icon} {cmd.title}")
        self.recent_commands = self.recent_commands[:10]
        
        recent = self.query_one("#recent-list", Static)
        if self.recent_commands:
            recent.update("\n".join(f"[green]• {c}[/green]" for c in self.recent_commands))
    
    async def action_command_palette(self) -> None:
        """Open the custom command palette."""
        def handle_result(result: Optional[Command]) -> None:
            if result is None:
                return  # User cancelled
            
            self._add_recent(result)
            
            # Execute the command action if available
            if result.action:
                if asyncio.iscoroutinefunction(result.action):
                    self.run_worker(result.action())
                else:
                    result.action()
            else:
                self.notify(
                    f"Selected: {result.title}",
                    title="Command Palette",
                    severity="information"
                )
        
        self.push_screen(
            CommandPaletteScreen(
                self.commands,
                title="⌘ Command Palette",
                placeholder="Type a command, or use @category to filter..."
            ),
            callback=handle_result
        )
    
    def action_new_file(self) -> None:
        """Create a new file."""
        self.file_count += 1
        self.notify(f"Created new file #{self.file_count}", title="New File")
    
    def action_open_file(self) -> None:
        """Open a file dialog."""
        self.notify("Open file dialog would appear here", title="Open File")
    
    def action_save_file(self) -> None:
        """Save current file."""
        self.notify("File saved successfully", title="Save", severity="success")


if __name__ == "__main__":
    app = MainApp()
    app.run()
