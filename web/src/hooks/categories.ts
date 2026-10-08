import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { Category } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { CategoryFormData } from "@/schemas/category";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useCategories(filters?: Record<string, string>, pagination?: PaginationParams) {
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
    queryKey: queryKeys.categories.list({ ...filters, ...(pagination || {}) } as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<Category>>(`/categories${qs ? "?" + qs : ""}`),
  });
}

export function useCategoryTree(filters?: Record<string, string>) {
  const params = new URLSearchParams({ tree: "true" });
  if (filters) {
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.set(k, v);
    });
  }
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.categories.tree(filters),
    queryFn: () => apiGet<Category[]>(`/categories?${qs}`),
  });
}

export function useCategory(id: number) {
  return useQuery({
    queryKey: queryKeys.categories.detail(id),
    queryFn: () => apiGet<Category>(`/categories/${id}`),
    enabled: !!id,
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CategoryFormData) => apiPost<Category>("/categories", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}

export function useUpdateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: CategoryFormData }) =>
      apiPut<Category>(`/categories/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/categories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}
