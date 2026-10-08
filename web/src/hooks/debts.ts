import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/api";
import { queryKeys } from "@/keys";
import type { Debt, DebtPayment, DebtStatusHistory, DebtSummary } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { DebtFormData, DebtPaymentFormData } from "@/schemas/debt";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useDebts(filters?: Record<string, string>, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (filters) {
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.set(k, v);
    });
  }
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.debts.list({ ...filters, ...(pagination || {}) } as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<Debt>>(`/debts${qs ? "?" + qs : ""}`),
  });
}

export function useDebt(id: number) {
  return useQuery({
    queryKey: queryKeys.debts.detail(id),
    queryFn: () => apiGet<Debt>(`/debts/${id}`),
    enabled: !!id,
  });
}

export function useDebtPayments(id: number) {
  return useQuery({
    queryKey: queryKeys.debts.payments(id),
    queryFn: () => apiGet<DebtPayment[]>(`/debts/${id}/payments`),
    enabled: !!id,
  });
}

export function useDebtHistory(id: number) {
  return useQuery({
    queryKey: queryKeys.debts.history(id),
    queryFn: () => apiGet<DebtStatusHistory[]>(`/debts/${id}/history`),
    enabled: !!id,
  });
}

export function useDebtSummary() {
  return useQuery({
    queryKey: queryKeys.debts.summary(),
    queryFn: () => apiGet<DebtSummary>("/debts/summary"),
  });
}

export function useOverdueDebts(filters?: Record<string, string>) {
  const params = filters
    ? "?" + new URLSearchParams(filters).toString()
    : "";
  return useQuery({
    queryKey: queryKeys.debts.overdue(filters),
    queryFn: () => apiGet<Debt[]>(`/debts/overdue${params}`),
  });
}

export function useDueSoonDebts(days?: number) {
  const params = days ? `?days=${days}` : "";
  return useQuery({
    queryKey: queryKeys.debts.dueSoon({ days: String(days || 7) }),
    queryFn: () => apiGet<Debt[]>(`/debts/due-soon${params}`),
  });
}

export function useCreateDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DebtFormData) => apiPost<Debt>("/debts", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
    },
  });
}

export function useUpdateDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DebtFormData }) =>
      apiPut<Debt>(`/debts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
    },
  });
}

export function useSettleDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/debts/${id}/settle`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
    },
  });
}

export function useCancelDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/debts/${id}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
    },
  });
}

export function useMonthlyRepayments() {
  return useQuery({
    queryKey: queryKeys.debts.monthlyRepayments(),
    queryFn: () => apiGet<{ month: string; total: number }[]>("/debts/repayments/monthly"),
  });
}

export function useTopCounterparties(limit?: number) {
  const params = limit ? `?limit=${limit}` : "";
  return useQuery({
    queryKey: queryKeys.debts.topCounterparties(),
    queryFn: () => apiGet<{ counterparty_name: string; total: number; count: number }[]>(`/debts/counterparties/top${params}`),
  });
}

export function useAgingReport() {
  return useQuery({
    queryKey: queryKeys.debts.aging(),
    queryFn: () => apiGet<Record<string, number>>("/debts/aging"),
  });
}

export function useAddDebtPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, data }: { debtId: number; data: DebtPaymentFormData }) =>
      apiPost<DebtPayment>(`/debts/${debtId}/payments`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
    },
  });
}

export function useReverseDebtPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, paymentId }: { debtId: number; paymentId: number }) =>
      apiPost(`/debts/${debtId}/payments/${paymentId}/reverse`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
    },
  });
}

export function useWriteOffDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/debts/${id}/write-off`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.debts.all });
    },
  });
}
