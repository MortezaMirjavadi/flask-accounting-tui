import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/api";
import { queryKeys } from "@/keys";
import type { InstallmentPlan, Installment } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { InstallmentPlanFormData, InstallmentPaymentFormData } from "@/schemas/installment";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useInstallmentPlans(walletId?: number, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (walletId) params.set("wallet_id", String(walletId));
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.installments.plans(walletId),
    queryFn: () => apiGet<ApiListResponse<InstallmentPlan>>(`/installments/plans${qs}`),
  });
}

export function useInstallmentPlan(id: number) {
  return useQuery({
    queryKey: queryKeys.installments.planDetail(id),
    queryFn: () => apiGet<InstallmentPlan>(`/installments/plans/${id}`),
    enabled: !!id,
  });
}

export function useUpcomingInstallments() {
  return useQuery({
    queryKey: queryKeys.installments.upcoming(),
    queryFn: () => apiGet<Installment[]>("/installments/upcoming"),
  });
}

export function useOverdueInstallments() {
  return useQuery({
    queryKey: queryKeys.installments.overdue(),
    queryFn: () => apiGet<Installment[]>("/installments/overdue"),
  });
}

export function useInstallmentDebt() {
  return useQuery({
    queryKey: queryKeys.installments.debt(),
    queryFn: () => apiGet<{ total_remaining: number }>("/installments/debt"),
  });
}

export function useCreateInstallmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InstallmentPlanFormData) =>
      apiPost<InstallmentPlan>("/installments/plans", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.installments.all });
    },
  });
}

export function useGenerateInstallments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: number) =>
      apiPost(`/installments/plans/${planId}/generate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.installments.all });
    },
  });
}

export function useCancelInstallmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: number) =>
      apiPost(`/installments/plans/${planId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.installments.all });
    },
  });
}

export function usePayInstallments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InstallmentPaymentFormData) =>
      apiPost("/installments/pay", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.installments.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useChangeInstallmentDueDate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dueDate }: { id: number; dueDate: string }) =>
      apiPut(`/installments/${id}/due-date`, { due_date: dueDate }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.installments.all });
    },
  });
}
