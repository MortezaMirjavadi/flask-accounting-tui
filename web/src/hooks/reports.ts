import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api";
import { queryKeys } from "@/keys";
import type {
  DailyReport,
  WeeklyReport,
  MonthlySummary,
  CategoryBreakdown,
  TransactionsSummary,
  BudgetHealth,
  BudgetHealthItem,
  TopItem,
  PricePoint,
  MonthlyBasketItem,
  CategoryItem,
  VelocityItem,
  SourcePrice,
  InflationReport,
  InflationSpike,
  BestStoreItem,
} from "@/types";

export function useDailyReport(date?: string, walletId?: number) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (walletId) params.set("wallet_id", String(walletId));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.daily(date, walletId),
    queryFn: () => apiGet<DailyReport>(`/reports/daily${qs}`),
  });
}

export function useWeeklyReport(date?: string, walletId?: number) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (walletId) params.set("wallet_id", String(walletId));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.weekly(date, walletId),
    queryFn: () => apiGet<WeeklyReport>(`/reports/weekly${qs}`),
  });
}

export function useMonthlyReport(year?: number, month?: number, walletId?: number) {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  if (month) params.set("month", String(month));
  if (walletId) params.set("wallet_id", String(walletId));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.monthly(year, month, walletId),
    queryFn: () => apiGet<MonthlySummary>(`/reports/monthly${qs}`),
  });
}

export function useTransactionsSummary(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.summary(filters),
    queryFn: () => apiGet<TransactionsSummary>(`/reports/transactions/summary${params}`),
  });
}

export function useReportByCategory(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.byCategory(filters),
    queryFn: () => apiGet<CategoryBreakdown[]>(`/reports/transactions/category${params}`),
  });
}

export function useReportByMonth(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.byMonth(filters),
    queryFn: () => apiGet<MonthlySummary[]>(`/reports/transactions/monthly${params}`),
  });
}

export function useCategoryChart(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.categoryChart(filters),
    queryFn: () => apiGet<CategoryBreakdown[]>(`/reports/transactions/category-chart${params}`),
  });
}

export function useBudgetReport(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.budget(filters),
    queryFn: async () => {
      const raw = await apiGet<{
        period: { year: number; month: number };
        categories: {
          category_id: number;
          category_name: string;
          planned_amount: number;
          total_spent: number;
          remaining_amount: number;
        }[];
        total_planned: number;
        total_spent: number;
        total_remaining: number;
      }>(`/reports/budget${params}`);

      const items: BudgetHealthItem[] = raw.categories.map((cat) => ({
        category_id: cat.category_id,
        category_name: cat.category_name,
        planned: cat.planned_amount,
        actual: cat.total_spent,
        variance: cat.total_spent - cat.planned_amount,
        utilization:
          cat.planned_amount > 0
            ? (cat.total_spent / cat.planned_amount) * 100
            : 0,
      }));

      const report: BudgetHealth = {
        period: {
          id: 0,
          user_id: 0,
          year: raw.period.year,
          month: raw.period.month,
          created_at: "",
          updated_at: "",
        },
        total_planned: raw.total_planned,
        total_actual: raw.total_spent,
        variance: raw.total_spent - raw.total_planned,
        utilization:
          raw.total_planned > 0
            ? (raw.total_spent / raw.total_planned) * 100
            : 0,
        items,
      };

      return [report];
    },
  });
}

export function useTopItems(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.itemsTop(filters),
    queryFn: () => apiGet<TopItem[]>(`/reports/items/top${params}`),
  });
}

export function usePriceHistory(name: string) {
  return useQuery({
    queryKey: queryKeys.reports.itemsPriceHistory(name),
    queryFn: () => apiGet<PricePoint[]>(`/reports/items/price-history?name=${encodeURIComponent(name)}`),
    enabled: !!name,
  });
}

export function useMonthlyBasket(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.itemsMonthlyBasket(filters),
    queryFn: () => apiGet<MonthlyBasketItem[]>(`/reports/items/monthly-basket${params}`),
  });
}

export function useItemsByCategory(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.itemsByCategory(filters),
    queryFn: () => apiGet<CategoryItem[]>(`/reports/items/by-category${params}`),
  });
}

export function useItemVelocity(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.itemsVelocity(filters),
    queryFn: () => apiGet<VelocityItem[]>(`/reports/items/velocity${params}`),
  });
}

export function usePriceComparison(name = "") {
  return useQuery({
    queryKey: queryKeys.reports.itemsPriceComparison(name),
    queryFn: () => apiGet<SourcePrice[]>(`/reports/items/price-comparison?name=${encodeURIComponent(name)}`),
    enabled: !!name,
  });
}

export function usePersonalInflation(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.inflationPersonal(filters),
    queryFn: () => apiGet<InflationReport>(`/reports/inflation/personal${params}`),
  });
}

export function usePriceSpikes(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.inflationSpikes(filters),
    queryFn: () => apiGet<InflationSpike[]>(`/reports/inflation/spikes${params}`),
  });
}

export function useBestStores(filters?: Record<string, string>) {
  const params = filters ? `?${new URLSearchParams(filters).toString()}` : "";
  return useQuery({
    queryKey: queryKeys.reports.itemsBestStores(filters),
    queryFn: () => apiGet<BestStoreItem[]>(`/reports/items/best-stores${params}`),
  });
}
