"""Screen modules package."""

from tui.screens.auth import LoginScreen
from tui.screens.main_menu import MainMenuScreen
from tui.screens.categories import (
    CategoriesScreen,
    CategoryListScreen,
    CategoryAddScreen,
    CategoryEditScreen,
)
from tui.screens.sources import (
    SourcesScreen,
    SourceListScreen,
    SourceAddScreen,
    SourceEditScreen,
)
from tui.screens.transactions import (
    TransactionsScreen,
    TransactionListScreen,
    TransactionByCategoryScreen,
    TransactionAddScreen,
    TransactionEditScreen,
)
from tui.screens.reports import (
    ReportsScreen,
    SummaryScreen,
    CategoryReportScreen,
    MonthlyReportScreen,
    BarChartScreen,
    PieChartScreen,
)
from tui.screens.budget import (
    BudgetScreen,
    BudgetTreeScreen,
    BudgetPeriodListScreen,
    BudgetPeriodAddScreen,
    BudgetPeriodEditScreen,
    BudgetItemListScreen,
    BudgetItemAddScreen,
    BudgetItemEditScreen,
    BudgetReportScreen,
)
from tui.screens.settings import SettingsScreen

__all__ = [
    # Auth
    "LoginScreen",
    # Main Menu
    "MainMenuScreen",
    # Categories
    "CategoriesScreen",
    "CategoryListScreen",
    "CategoryAddScreen",
    "CategoryEditScreen",
    # Sources
    "SourcesScreen",
    "SourceListScreen",
    "SourceAddScreen",
    "SourceEditScreen",
    # Transactions
    "TransactionsScreen",
    "TransactionListScreen",
    "TransactionByCategoryScreen",
    "TransactionAddScreen",
    "TransactionEditScreen",
    # Reports
    "ReportsScreen",
    "SummaryScreen",
    "CategoryReportScreen",
    "MonthlyReportScreen",
    "BarChartScreen",
    "PieChartScreen",
    # Budget
    "BudgetScreen",
    "BudgetTreeScreen",
    "BudgetPeriodListScreen",
    "BudgetPeriodAddScreen",
    "BudgetPeriodEditScreen",
    "BudgetItemListScreen",
    "BudgetItemAddScreen",
    "BudgetItemEditScreen",
    "BudgetReportScreen",
    # Settings
    "SettingsScreen",
]
