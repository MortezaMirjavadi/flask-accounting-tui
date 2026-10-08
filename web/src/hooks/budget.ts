import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { BudgetPeriod, BudgetPeriodWithItems, BudgetItem, ApiListResponse } from "@/types";
import type { BudgetPeriodFormData, BudgetItemFormData } from "@/schemas/budget";

export function useBudgetPeriods() {
  return useQuery({
    queryKey: queryKeys.budget.periods(),
    queryFn: () => apiGet<BudgetPeriod[]>("/budget/periods"),
  });
}

export function useBudgetPeriodsWithItems() {
  return useQuery({
    queryKey: queryKeys.budget.periodsWithItems(),
    queryFn: () => apiGet<BudgetPeriodWithItems[]>("/budget/periods/with-items"),
  });
}

export function useBudgetPeriod(id: number) {
  return useQuery({
    queryKey: queryKeys.budget.periodDetail(id),
    queryFn: () => apiGet<BudgetPeriod>(`/budget/periods/${id}`),
    enabled: !!id,
  });
}

export function useBudgetItems(periodId: number) {
  return useQuery({
    queryKey: queryKeys.budget.items(periodId),
    queryFn: () =>
      apiGet<ApiListResponse<BudgetItem>>(`/budget/periods/${periodId}/items?per_page=1000`),
    enabled: !!periodId,
    select: (data) => data.items,
  });
}

export function useCreateBudgetPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetPeriodFormData) =>
      apiPost<BudgetPeriod>("/budget/periods", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}

export function useUpdateBudgetPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BudgetPeriodFormData> }) =>
      apiPut<BudgetPeriod>(`/budget/periods/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}

export function useDeleteBudgetPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/budget/periods/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}

export function useCreateBudgetItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetItemFormData & { budget_period_id: number }) =>
      apiPost<BudgetItem>("/budget/items", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}

export function useUpdateBudgetItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BudgetItemFormData> }) =>
      apiPut<BudgetItem>(`/budget/items/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}

export function useDeleteBudgetItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/budget/items/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all });
    },
  });
}
