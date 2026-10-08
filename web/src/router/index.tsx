import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import RootLayout from "@/components/layout/RootLayout";
import LoadingPage from "@/components/shared/LoadingPage";

const LoginPage = lazy(() => import("@/pages/auth/LoginPage"));
const RegisterPage = lazy(() => import("@/pages/auth/RegisterPage"));
const SetupPage = lazy(() => import("@/pages/auth/SetupPage"));
const IntroPage = lazy(() => import("@/pages/auth/IntroPage"));
const DashboardPage = lazy(() => import("@/pages/dashboard/DashboardPage"));
const CategoriesPage = lazy(() => import("@/pages/categories/CategoriesPage"));
const TransactionsPage = lazy(() => import("@/pages/transactions/TransactionsPage"));
const TransactionFormPage = lazy(() => import("@/pages/transactions/TransactionFormPage"));
const TransactionDetailPage = lazy(() => import("@/pages/transactions/TransactionDetailPage"));
const TransfersPage = lazy(() => import("@/pages/transfers/TransfersPage"));
const CalendarPage = lazy(() => import("@/pages/calendar/CalendarPage"));
const EventFormPage = lazy(() => import("@/pages/calendar/EventFormPage"));
const EventDetailPage = lazy(() => import("@/pages/calendar/EventDetailPage"));
const BudgetPeriodsPage = lazy(() => import("@/pages/budget/BudgetPeriodsPage"));
const BudgetPeriodFormPage = lazy(() => import("@/pages/budget/BudgetPeriodFormPage"));
const BudgetReportPage = lazy(() => import("@/pages/budget/BudgetReportPage"));
const ReportsPage = lazy(() => import("@/pages/reports/ReportsPage"));
const InstallmentPlansPage = lazy(() => import("@/pages/installments/InstallmentPlansPage"));
const InstallmentPlanFormPage = lazy(() => import("@/pages/installments/InstallmentPlanFormPage"));
const InstallmentDetailPage = lazy(() => import("@/pages/installments/InstallmentDetailPage"));
const ChecksPage = lazy(() => import("@/pages/checks/ChecksPage"));
const CheckFormPage = lazy(() => import("@/pages/checks/CheckFormPage"));
const DebtsPage = lazy(() => import("@/pages/debts/DebtsPage"));
const DebtFormPage = lazy(() => import("@/pages/debts/DebtFormPage"));
const DebtDetailPage = lazy(() => import("@/pages/debts/DebtDetailPage"));
const ContactsPage = lazy(() => import("@/pages/contacts/ContactsPage"));
const TagsPage = lazy(() => import("@/pages/tags/TagsPage"));
const LabelsPage = lazy(() => import("@/pages/labels/LabelsPage"));
const SettingsPage = lazy(() => import("@/pages/settings/SettingsPage"));
const UsersPage = lazy(() => import("@/pages/users/UsersPage"));
const ItemReportsPage = lazy(() => import("@/pages/reports/ItemReportsPage"));
const SourceTransferReportPage = lazy(() => import("@/pages/sources/SourceTransferReportPage"));
const WalletsPage = lazy(() => import("@/pages/wallets/WalletsPage"));
const WalletDetailPage = lazy(() => import("@/pages/wallets/WalletDetailPage"));
const WalletTransferReportPage = lazy(() => import("@/pages/wallets/WalletTransferReportPage"));
const SourcesPage = lazy(() => import("@/pages/wallets/SourcesPage"));
const TransactionsByCategoryPage = lazy(() => import("@/pages/transactions/TransactionsByCategoryPage"));
const BudgetTreePage = lazy(() => import("@/pages/budget/BudgetTreePage"));
const BudgetItemsPage = lazy(() => import("@/pages/budget/BudgetItemsPage"));

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingPage />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <SuspenseWrapper><LoginPage /></SuspenseWrapper>,
  },
  {
    path: "/register",
    element: <SuspenseWrapper><RegisterPage /></SuspenseWrapper>,
  },
  {
    path: "/intro",
    element: <SuspenseWrapper><IntroPage /></SuspenseWrapper>,
  },
  {
    path: "/setup",
    element: <SuspenseWrapper><SetupPage /></SuspenseWrapper>,
  },
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <SuspenseWrapper><DashboardPage /></SuspenseWrapper> },
      { path: "categories", element: <SuspenseWrapper><CategoriesPage /></SuspenseWrapper> },
      { path: "wallets/sources", element: <SuspenseWrapper><SourcesPage /></SuspenseWrapper> },
      { path: "sources/:id/transfers", element: <SuspenseWrapper><SourceTransferReportPage /></SuspenseWrapper> },
      { path: "wallets", element: <SuspenseWrapper><WalletsPage /></SuspenseWrapper> },
      { path: "wallets/:id", element: <SuspenseWrapper><WalletDetailPage /></SuspenseWrapper> },
      { path: "wallets/:id/transfers", element: <SuspenseWrapper><WalletTransferReportPage /></SuspenseWrapper> },
      { path: "transactions", element: <SuspenseWrapper><TransactionsPage /></SuspenseWrapper> },
      { path: "transactions/by-category", element: <SuspenseWrapper><TransactionsByCategoryPage /></SuspenseWrapper> },
      { path: "transactions/new", element: <SuspenseWrapper><TransactionFormPage /></SuspenseWrapper> },
      { path: "transactions/:id", element: <SuspenseWrapper><TransactionDetailPage /></SuspenseWrapper> },
      { path: "transactions/:id/edit", element: <SuspenseWrapper><TransactionFormPage /></SuspenseWrapper> },
      { path: "transfers", element: <SuspenseWrapper><TransfersPage /></SuspenseWrapper> },
      { path: "calendar", element: <SuspenseWrapper><CalendarPage /></SuspenseWrapper> },
      { path: "calendar/new", element: <SuspenseWrapper><EventFormPage /></SuspenseWrapper> },
      { path: "calendar/:id", element: <SuspenseWrapper><EventDetailPage /></SuspenseWrapper> },
      { path: "calendar/:id/edit", element: <SuspenseWrapper><EventFormPage /></SuspenseWrapper> },
      { path: "budget/periods", element: <SuspenseWrapper><BudgetPeriodsPage /></SuspenseWrapper> },
      { path: "budget/periods/new", element: <SuspenseWrapper><BudgetPeriodFormPage /></SuspenseWrapper> },
      { path: "budget/periods/:id/edit", element: <SuspenseWrapper><BudgetPeriodFormPage /></SuspenseWrapper> },
      { path: "budget/periods/:id/items", element: <SuspenseWrapper><BudgetItemsPage /></SuspenseWrapper> },
      { path: "budget/report", element: <SuspenseWrapper><BudgetReportPage /></SuspenseWrapper> },
      { path: "budget/tree", element: <SuspenseWrapper><BudgetTreePage /></SuspenseWrapper> },
      { path: "reports", element: <SuspenseWrapper><ReportsPage /></SuspenseWrapper> },
      { path: "reports/:tab", element: <SuspenseWrapper><ReportsPage /></SuspenseWrapper> },
      { path: "reports/items", element: <SuspenseWrapper><ItemReportsPage /></SuspenseWrapper> },
      { path: "installments", element: <SuspenseWrapper><InstallmentPlansPage /></SuspenseWrapper> },
      { path: "installments/new", element: <SuspenseWrapper><InstallmentPlanFormPage /></SuspenseWrapper> },
      { path: "installments/:id", element: <SuspenseWrapper><InstallmentDetailPage /></SuspenseWrapper> },
      { path: "installments/:id/edit", element: <SuspenseWrapper><InstallmentPlanFormPage /></SuspenseWrapper> },
      { path: "checks", element: <SuspenseWrapper><ChecksPage /></SuspenseWrapper> },
      { path: "checks/new", element: <SuspenseWrapper><CheckFormPage /></SuspenseWrapper> },
      { path: "checks/:id/edit", element: <SuspenseWrapper><CheckFormPage /></SuspenseWrapper> },
      { path: "debts", element: <SuspenseWrapper><DebtsPage /></SuspenseWrapper> },
      { path: "debts/new", element: <SuspenseWrapper><DebtFormPage /></SuspenseWrapper> },
      { path: "debts/:id", element: <SuspenseWrapper><DebtDetailPage /></SuspenseWrapper> },
      { path: "debts/:id/edit", element: <SuspenseWrapper><DebtFormPage /></SuspenseWrapper> },
      { path: "contacts", element: <SuspenseWrapper><ContactsPage /></SuspenseWrapper> },
      { path: "tags", element: <SuspenseWrapper><TagsPage /></SuspenseWrapper> },
      { path: "labels", element: <SuspenseWrapper><LabelsPage /></SuspenseWrapper> },
      { path: "settings", element: <SuspenseWrapper><SettingsPage /></SuspenseWrapper> },
      { path: "users", element: <SuspenseWrapper><UsersPage /></SuspenseWrapper> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
