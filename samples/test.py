from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    DataTable,
    Static,
    Button,
    Tree,
    RichLog,
    OptionList,
    Label,
    DirectoryTree
)
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets.option_list import Option
from textual.command import Provider, Hit, DiscoveryHit
from textual.types import IgnoreReturnCallbackType
from textual import on

from switch import Switch

class MyCommandProvider(Provider):
    """Command Provider سفارشی"""
    
    async def search(self, query: str):
        """جستجو در کامندها"""
        
        commands = [
            ("add-task", "➕ افزودن تسک جدید", self.add_task),
            ("show-stats", "📊 نمایش آمار", self.show_stats),
            ("export-data", "💾 خروجی گرفتن", self.export_data),
            ("clear-all", "🗑️ پاک کردن همه", self.clear_all),
            ("settings", "⚙️ تنظیمات", self.open_settings),
        ]
        
        # فیلتر بر اساس query
        matcher = self.matcher(query)
        
        for cmd_id, title, callback in commands:
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(title),
                    callback,
                    help=f"اجرای {title}"
                )
    
    async def discover(self):
        """کامندهای پیشنهادی (وقتی چیزی تایپ نشده)"""
        yield DiscoveryHit(
            "➕ Add new task",
            self.add_task,
            help="adding new task"
        )
        yield DiscoveryHit(
            "📊 Show statistics",
            self.show_stats,
            help="look at statistics"
        )
        yield DiscoveryHit(
            "📊 Erase all data",
            self.clear_all,
            help="Erase all information"
        )
    
    # Callback ها
    async def add_task(self) -> None:
        self.app.notify("✅ تسک جدید اضافه شد")
    
    async def show_stats(self) -> None:
        self.app.notify("📊 نمایش آمار...")
    
    async def export_data(self) -> None:
        self.app.notify("💾 در حال خروجی گرفتن...")
    
    async def clear_all(self) -> None:
        self.app.notify("🗑️ همه پاک شد")
    
    async def open_settings(self) -> None:
        self.app.notify("⚙️ تنظیمات باز شد")

class ComplexScreen(Screen):
    CSS = """
    #main_container {
        height: 1fr;
    }
    
    TabbedContent {
        height: 1fr;
    }
    
    DataTable {
        height: 1fr;
    }
    
    #stats_panel {
        height: 5;
        border: solid $primary;
        padding: 1;
    }
    
    .button_bar {
        height: auto;
        padding: 1;
    }
    
    VerticalScroll {
        height: 1fr;
    }
    
    Tree {
        height: auto;
    }

    /* استایل تب سوییچ‌ها */
    #switches_container {
        padding: 2;
        height: 1fr;
    }

    .switch-row {
        layout: horizontal;
        height: auto;
        width: 100%;
        margin: 1 0;
    }

    .switch-row Label {
        width: 1fr;
        content-align: left middle;
    }

    .switch-row Switch {
        width: auto;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main_container"):
            # پنل آمار بالا
            yield Static(
                "آمار کلی: مجموع دوره‌ها: ۵ | مجموع آیتم‌ها: ۲۳ | کل مبلغ: ۱۵۰,۰۰۰ تومان",
                id="stats_panel",
            )
            
            # تب‌ها
            with TabbedContent():
                # تب اول: جدول دوره‌ها
                with TabPane("دوره‌ها", id="tab_periods"):
                    with Vertical():
                        yield DataTable(id="periods_table")
                        with Horizontal(classes="button_bar"):
                            yield Button("افزودن", id="add_period", variant="success")
                            yield Button("ویرایش", id="edit_period", variant="primary")
                            yield Button("حذف", id="delete_period", variant="error")
                
                # تب دوم: جدول آیتم‌ها
                with TabPane("آیتم‌ها", id="tab_items"):
                    with Vertical():
                        yield DataTable(id="items_table")
                        with Horizontal(classes="button_bar"):
                            yield Button("افزودن", id="add_item", variant="success")
                            yield Button("ویرایش", id="edit_item", variant="primary")
                            yield Button("حذف", id="delete_item", variant="error")
                
                # تب سوم: درخت بودجه
                with TabPane("درخت", id="tab_tree"):
                    with VerticalScroll():
                        yield Tree("بودجه", id="budget_tree")
                
                # تب چهارم: گزارش
                with TabPane("گزارش", id="tab_report"):
                    with VerticalScroll():
                        yield RichLog(id="report_log", highlight=True, markup=True)

                # تب پنجم: تنظیم تم (OptionList موجودِ شما)
                with TabPane("Options", id="option_tab"):
                    with Container(id="settings_container"):
                        yield Label("⚙️ Theme Setting", classes="section_title")
                        yield OptionList(
                            Option("☀️ Classic", id="light_classic"),
                            Option("🌸 Pink", id="light_pastel"),
                            Option("🌊 Blue", id="light_ocean"),

                            Option("──────────", disabled=True),

                            Option("🌙 Classic Dark", id="dark_classic"),
                            Option("🎨 Violate Classic", id="dark_neon"),
                            Option("🌲 Matrix Green", id="dark_matrix"),

                            Option("──────────", disabled=True),

                            Option("🎭 Customize 1", id="custom_1", disabled=True),
                            Option("🎪 Customize 2", id="custom_2", disabled=True),

                            id="theme_list",
                        )

                # with TabPane("Switches", id="switches_tab"):
                #     with Container(id="switches_container"):
                #         yield Label("⚙️ تنظیمات عمومی", classes="section_title")

                #         with Container(classes="switch-row"):
                #             yield Label("حالت تاریک:")
                #             yield Switch(id="dark_mode", value=False)

                #         with Container(classes="switch-row"):
                #             yield Label("اعلان‌ها:")
                #             yield Switch(id="notifications_switch", value=True)

                #         with Container(classes="switch-row"):
                #             yield Label("هماهنگی با سیستم عامل:")
                #             yield Switch(id="sync_with_system", value=True)

                with TabPane("Switches", id="switches_tab"):
                    with Container(id="switches_container"):
                        yield DirectoryTree("/path/to/dir")
                        yield DirectoryTree("/path/to/dir")
                        yield DirectoryTree("/path/to/dir")
                        yield DirectoryTree("/path/to/dir")
                        yield DirectoryTree("/path/to/dir")

        yield Footer()
    
    def on_mount(self) -> None:
        # مقداردهی جدول دوره‌ها
        periods_table = self.query_one("#periods_table", DataTable)
        periods_table.add_columns("نام", "تاریخ شروع", "تاریخ پایان", "مبلغ")
        periods_table.add_row("دوره بهار ۱۴۰۵", "۱۴۰۵/۰۱/۰۱", "۱۴۰۵/۰۳/۳۱", "۵۰,۰۰۰")
        periods_table.add_row("دوره تابستان ۱۴۰۵", "۱۴۰۵/۰۴/۰۱", "۱۴۰۵/۰۶/۳۱", "۶۰,۰۰۰")
        periods_table.add_row("دوره پاییز ۱۴۰۵", "۱۴۰۵/۰۷/۰۱", "۱۴۰۵/۰۹/۳۰", "۴۰,۰۰۰")
        periods_table.cursor_type = "row"
        periods_table.zebra_stripes = True
        
        # مقداردهی جدول آیتم‌ها
        items_table = self.query_one("#items_table", DataTable)
        items_table.add_columns("شرح", "دسته", "مبلغ", "تاریخ")
        items_table.add_row("هزینه اجاره", "مسکن", "۳۰,۰۰۰", "۱۴۰۵/۰۱/۰۵")
        items_table.add_row("خرید مواد غذایی", "خوراک", "۵,۰۰۰", "۱۴۰۵/۰۱/۱۰")
        items_table.add_row("قبض برق", "خدمات", "۲,۵۰۰", "۱۴۰۵/۰۱/۱۵")
        items_table.add_row("بنزین", "حمل‌ونقل", "۳,۰۰۰", "۱۴۰۵/۰۱/۲۰")
        items_table.add_row("اینترنت", "خدمات", "۱,۵۰۰", "۱۴۰۵/۰۱/۲۵")
        items_table.cursor_type = "row"
        items_table.zebra_stripes = True
        
        # مقداردهی درخت بودجه
        tree = self.query_one("#budget_tree", Tree)
        tree.show_root = True
        tree.show_guides = True
        
        year_node = tree.root.add("سال ۱۴۰۵", expand=True)
        
        spring = year_node.add("بهار (۵۰,۰۰۰ تومان)", expand=True)
        spring.add_leaf("🏠 مسکن: ۳۰,۰۰۰")
        spring.add_leaf("🍔 خوراک: ۱۰,۰۰۰")
        spring.add_leaf("⚡ خدمات: ۱۰,۰۰۰")
        
        summer = year_node.add("تابستان (۶۰,۰۰۰ تومان)", expand=True)
        summer.add_leaf("🏠 مسکن: ۳۵,۰۰۰")
        summer.add_leaf("🍔 خوراک: ۱۵,۰۰۰")
        summer.add_leaf("🚗 حمل‌ونقل: ۱۰,۰۰۰")
        
        fall = year_node.add("پاییز (۴۰,۰۰۰ تومان)")
        fall.add_leaf("🏠 مسکن: ۲۵,۰۰۰")
        fall.add_leaf("🍔 خوراک: ۱۰,۰۰۰")
        fall.add_leaf("📚 آموزش: ۵,۰۰۰")
        
        # مقداردهی لاگ گزارش
        log = self.query_one("#report_log", RichLog)
        log.write("[bold green]✓ صفحه با موفقیت بارگذاری شد[/bold green]")
        log.write("")
        log.write("[bold cyan]گزارش خلاصه:[/bold cyan]")
        log.write("  • تعداد دوره‌ها: [yellow]۳[/yellow]")
        log.write("  • تعداد آیتم‌ها: [yellow]۵[/yellow]")
        log.write("  • مجموع هزینه‌ها: [yellow]۴۲,۰۰۰ تومان[/yellow]")
        log.write("")
        log.write("[bold magenta]بیشترین هزینه:[/bold magenta]")
        log.write("  🏠 مسکن: [red]۹۰,۰۰۰ تومان[/red]")
        log.write("")
        log.write("[bold blue]آخرین تراکنش‌ها:[/bold blue]")
        log.write("  • ۱۴۰۵/۰۱/۲۵ - اینترنت: ۱,۵۰۰ تومان")
        log.write("  • ۱۴۰۵/۰۱/۲۰ - بنزین: ۳,۰۰۰ تومان")
        log.write("  • ۱۴۰۵/۰۱/۱۵ - قبض برق: ۲,۵۰۰ تومان")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "add_period":
            self.notify("افزودن دوره جدید...")
        elif button_id == "edit_period":
            self.notify("ویرایش دوره...")
        elif button_id == "delete_period":
            self.notify("حذف دوره...")
        elif button_id == "add_item":
            self.notify("افزودن آیتم جدید...")
        elif button_id == "edit_item":
            self.notify("ویرایش آیتم...")
        elif button_id == "delete_item":
            self.notify("حذف آیتم...")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table_id = event.data_table.id
        row_key = event.row_key
        
        if table_id == "periods_table":
            self.notify(f"دوره انتخاب شد: {row_key}")
        elif table_id == "items_table":
            self.notify(f"آیتم انتخاب شد: {row_key}")
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node_label = event.node.label
        self.notify(f"انتخاب شد: {node_label}")

    # نمونه‌ی هندل کردن تغییر سوییچ‌ها (اختیاری)
    def on_switch_changed(self, message: Switch.Changed) -> None:
        if message.switch.id == "dark_mode":
            self.notify(f"Dark mode: {'ON' if message.value else 'OFF'}")
        elif message.switch.id == "notifications_switch":
            self.notify(f"Notifications: {'ON' if message.value else 'OFF'}")
        elif message.switch.id == "sync_with_system":
            self.notify(f"Sync with system: {'ON' if message.value else 'OFF'}")


class MyApp(App):
    ENABLE_COMMAND_PALETTE = True

    COMMANDS = {MyCommandProvider}

    def on_mount(self) -> None:
        self.push_screen(ComplexScreen())


if __name__ == "__main__":
    app = MyApp()
    app.run()
