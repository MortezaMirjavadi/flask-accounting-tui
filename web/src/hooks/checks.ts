import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/api";
import { queryKeys } from "@/keys";
import type { Check } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { CheckFormData } from "@/schemas/check";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useChecks(filters?: Record<string, string>, pagination?: PaginationParams) {
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
    queryKey: queryKeys.checks.list({ ...filters, ...(pagination || {}) } as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<Check>>(`/checks${qs ? "?" + qs : ""}`),
  });
}

export function useCheck(id: number) {
  return useQuery({
    queryKey: queryKeys.checks.detail(id),
    queryFn: () => apiGet<Check>(`/checks/${id}`),
    enabled: !!id,
  });
}

export function useUpcomingChecks() {
  return useQuery({
    queryKey: queryKeys.checks.upcoming(),
    queryFn: () => apiGet<Check[]>("/checks/upcoming"),
  });
}

export function useCreateCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CheckFormData) => apiPost<Check>("/checks", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.checks.all });
    },
  });
}

export function useClearCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/checks/${id}/clear`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.checks.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useBounceCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/checks/${id}/bounce`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.checks.all });
    },
  });
}

export function useCancelCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/checks/${id}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.checks.all });
    },
  });
}

export function useChangeCheckDueDate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dueDate }: { id: number; dueDate: string }) =>
      apiPut(`/checks/${id}/due-date`, { due_date: dueDate }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.checks.all });
    },
  });
}
