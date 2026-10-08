export interface User {
  id: number;
  username: string;
  display_name: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  is_approved: boolean;
  totp_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  requires_2fa: boolean;
}

export interface Category {
  id: number;
  user_id: number;
  name: string;
  type: "income" | "cost";
  parent_id: number | null;
  parent_name?: string;
  children?: Category[];
  _depth?: number;
  created_at: string;
  updated_at: string;
}

export interface Wallet {
  id: number;
  user_id: number;
  name: string;
  currency: "IRR" | "USD" | "EUR" | "GBP" | "AED";
  wallet_type: "personal" | "shared";
  variant?: "family" | "team" | "travel" | "business" | "savings" | null;
  icon: string | null;
  description: string | null;
  role?: "owner" | "editor" | "viewer";
  member_count?: number;
  account_count?: number;
  accounts?: Account[];
  total_balance?: number;
  default_account_id?: number;
  created_at: string;
  updated_at: string;
}

// Backward compat alias
export type Source = Wallet;

export interface Account {
  id: number;
  wallet_id: number;
  name: string;
  account_type: "cash" | "bank" | "card" | "savings" | "wallet" | "other";
  bank_type: string;
  amount: string;
  icon: string | null;
  description: string | null;
  is_default: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface WalletMember {
  id: number;
  wallet_id: number;
  user_id: number;
  username: string;
  display_name: string;
  role: "owner" | "editor" | "viewer";
  joined_at: string;
}

export interface WalletInvitation {
  id: number;
  wallet_id: number;
  wallet_name: string;
  currency: string;
  inviter_name: string;
  inviter_display_name: string;
  role: "editor" | "viewer";
  status: "pending" | "accepted" | "rejected";
  created_at: string;
}

export interface WalletActivity {
  id: number;
  wallet_id: number;
  user_id: number;
  username: string;
  display_name: string;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  details: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface ExchangeRate {
  id: number;
  user_id: number;
  from_currency: string;
  to_currency: string;
  rate: number;
  effective_date: string;
  created_at: string;
  updated_at: string;
}

export interface ConsolidatedBalance {
  preferred_currency: string;
  total_converted_balance: number;
  wallet_count: number;
  wallets: {
    wallet_id: number;
    wallet_name: string;
    currency: string;
    wallet_type: string;
    role: string;
    balance: number;
    converted_balance: number | null;
    preferred_currency: string;
  }[];
}

export const SUPPORTED_CURRENCIES = [
  "IRR",
  "USD",
  "EUR",
  "GBP",
  "AED",
] as const;
export type Currency = (typeof SUPPORTED_CURRENCIES)[number];

export interface Transfer {
  id: number;
  user_id: number;
  from_source_id: number;
  to_source_id: number;
  amount: number;
  date: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface TransferRecord {
  id: number;
  amount: number;
  date: string;
  notes?: string | null;
  description?: string | null;
  from_source_id?: number;
  to_source_id?: number;
  from_source_name?: string;
  to_source_name?: string;
  from_wallet_id?: number;
  to_wallet_id?: number;
  from_wallet_name?: string;
  to_wallet_name?: string;
}

export interface TransferReport {
  records: TransferRecord[];
  summary: {
    total_transfer_in: number;
    total_transfer_out: number;
    net_transfer: number;
  };
}

export interface TransferListItem {
  id: number;
  user_id: number;
  from_source_id: number;
  to_source_id: number;
  amount: number;
  date: string;
  notes: string;
  from_source_name: string;
  to_source_name: string;
  record_type: "transfer";
  is_transfer: true;
  category_name: string;
  source_name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: number;
  user_id: number;
  date: string;
  amount: number;
  category_id: number;
  source_id: number;
  wallet_id?: number;
  account_id?: number;
  description: string;
  reference_type: string | null;
  reference_id: number | null;
  is_transfer: boolean;
  is_private?: boolean;
  transfer_pair_id: number | null;
  record_type: "transaction" | "transfer";
  category_name?: string;
  category_type?: string;
  source_name?: string;
  wallet_type?: "personal" | "shared";
  wallet_owner_id?: number;
  creator_username?: string;
  creator_display_name?: string;
  tags?: Tag[];
  labels?: Label[];
  created_at: string;
  updated_at: string;
}

export interface TransactionItem {
  id: number;
  transaction_id: number;
  name: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BudgetPeriod {
  id: number;
  user_id: number;
  year: number;
  month: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetPeriodWithItems extends BudgetPeriod {
  items: BudgetItem[];
}

export interface BudgetItem {
  id: number;
  budget_period_id: number;
  category_id: number;
  planned_amount: number;
  actual_amount?: number;
  notes: string;
  category_name?: string;
  created_at: string;
  updated_at: string;
}

export interface InstallmentPlan {
  id: number;
  user_id: number;
  title: string;
  total_amount: number;
  installment_count: number;
  installment_amount: number;
  start_date: string;
  due_day_of_month: number;
  category_id: number | null;
  source_id: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Installment {
  id: number;
  plan_id: number;
  installment_number: number;
  amount: number;
  due_date: string;
  paid_date: string | null;
  status: string;
  transaction_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface Check {
  id: number;
  user_id: number;
  check_number: string;
  bank_name: string;
  amount: number;
  issue_date: string;
  due_date: string;
  type: "issued" | "received";
  source_id: number | null;
  category_id: number | null;
  status: string;
  transaction_id: number | null;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Debt {
  id: number;
  user_id: number;
  type: "payable" | "receivable";
  counterparty_name: string;
  counterparty_type: string;
  title: string;
  description: string;
  original_amount: number;
  remaining_amount: number;
  currency: string;
  issue_date: string;
  due_date: string | null;
  status: string;
  priority: string;
  reference_type: string | null;
  reference_id: number | null;
  wallet_id: number | null;
  category_id: number | null;
  source_id: number | null;
  has_interest: boolean;
  interest_type: string | null;
  interest_rate: number | null;
  created_at: string;
  updated_at: string;
}

export interface DebtPayment {
  id: number;
  debt_id: number;
  transaction_id: number | null;
  amount: number;
  payment_date: string;
  payment_method: string;
  source_id: number | null;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface DebtStatusHistory {
  id: number;
  debt_id: number;
  old_status: string;
  new_status: string;
  changed_at: string;
  note: string;
}

export interface Contact {
  id: number;
  user_id: number;
  name: string;
  phone: string;
  email: string;
  address: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  user_id: number;
  name: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface Label {
  id: number;
  user_id: number;
  name: string;
  color: string;
  created_at: string;
  updated_at: string;
}

// Report types
export interface DailyReport {
  date: string;
  total_income: number;
  total_expenses: number;
  balance: number;
  transactions: Transaction[];
  income?: number;
  cost?: number;
  net?: number;
  last_5_transactions?: Transaction[];
}

export interface WeeklyReport {
  start_date: string;
  end_date: string;
  total_income: number;
  total_cost: number;
  balance: number;
  days: DailyReport[];
}

export interface MonthlySummary {
  year: number;
  month: number;
  total_income: number;
  total_cost: number;
  balance: number;
  transaction_count: number;
  total_expenses?: number;
  net?: number;
  summary?: MonthlySummary;
  category_breakdown?: CategoryBreakdown[];
}

export interface CategoryBreakdown {
  category_id: number;
  category_name: string;
  category_type: string;
  total: number;
  count: number;
  percentage: number;
  actual_amount?: number;
  percent_used?: number;
}

export interface TransactionsSummary {
  total_income: number;
  total_cost: number;
  balance: number;
  transaction_count: number;
  average_transaction: number;
}

export interface BudgetHealth {
  period: BudgetPeriod;
  total_planned: number;
  total_actual: number;
  variance: number;
  utilization: number;
  items: BudgetHealthItem[];
}

export interface BudgetHealthItem {
  category_id: number;
  category_name: string;
  planned: number;
  actual: number;
  variance: number;
  utilization: number;
}

export interface TopItem {
  name: string;
  total_spent: number;
  purchase_count: number;
  avg_price: number;
}

export interface PricePoint {
  date: string;
  avg_price: number;
  min_price: number;
  max_price: number;
  purchase_count: number;
}

export interface MonthlyBasketItem {
  year: number;
  month: number;
  items: { name: string; quantity: number; total: number }[];
  total: number;
}

export interface CategoryItem {
  category_id: number;
  category_name: string;
  items: { name: string; total: number; count: number }[];
  category_total: number;
}

export interface VelocityItem {
  name: string;
  avg_monthly_spend: number;
  avg_monthly_quantity: number;
  trend: "increasing" | "decreasing" | "stable";
}

export interface SourcePrice {
  name: string;
  source_id: number;
  source_name: string;
  avg_price: number;
  min_price: number;
  max_price: number;
  purchase_count: number;
}

export interface InflationItem {
  name: string;
  first_price: number;
  last_price: number;
  change_pct: number;
  months_tracked: number;
}

export interface InflationReport {
  items: InflationItem[];
  overall_inflation_pct: number;
  period_start: string;
  period_end: string;
}

export interface InflationSpike extends InflationItem {
  current_price?: number;
  avg_price?: number;
  spike_pct?: number;
}

export interface BestStoreItem {
  name: string;
  best_source: string;
  best_price: number;
  avg_price: number;
}

export interface ForecastReport {
  expected_income: number;
  expected_expenses: number;
  forecast_balance: number;
}

export interface AlertItem {
  severity: "low" | "medium" | "high" | string;
  message: string;
}

export interface AlertsReport {
  alerts: AlertItem[];
}

export interface Setup2FAResponse {
  secret: string;
  otpauth_url?: string;
}

export interface DebtSummary {
  payable_total: number;
  receivable_total: number;
  net_position: number;
  overdue_count: number;
  overdue_amount: number;
  due_soon: { count: number; total: string };
  by_status: Record<
    string,
    Record<string, { count: number; total_original: number; total_remaining: number }>
  >;
  recent_payments: DebtPayment[];
}

export interface FinancialEvent {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  amount: number;
  category_id: number;
  source_id: number | null;
  frequency: "once" | "daily" | "weekly" | "monthly" | "yearly";
  repeat_interval: number;
  start_date: string;
  end_date: string | null;
  occurrence_limit: number | null;
  status: "active" | "paused" | "cancelled";
}

export interface EventInstance {
  id: number;
  event_id: number;
  user_id: number;
  due_date: string;
  status: "pending" | "snoozed" | "confirmed" | "cancelled";
  transaction_id: number | null;
  snoozed_from: string | null;
  title: string;
  description: string | null;
  amount: number;
  category_id: number;
  source_id: number | null;
  category_name: string;
  category_type: "income" | "cost";
}
