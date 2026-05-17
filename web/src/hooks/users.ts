import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { User } from "@/types";
import type { ApiListResponse } from "@/types/api";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useUsers(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.users.list(pagination as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<User>>(`/auth/users${qs ? "?" + qs : ""}`),
  });
}

export function usePendingUsers(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.users.list({ pending: "true", ...(pagination || {}) } as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<User>>(`/auth/pending-users${qs ? "?" + qs : ""}`),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      username: string;
      password: string;
      display_name: string;
      email?: string;
      role?: string;
      is_active?: boolean;
    }) => apiPost<User>("/auth/users", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<User> & { password?: string } }) =>
      apiPut<User>(`/auth/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/auth/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useApproveUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/auth/approve-user/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useRejectUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/auth/reject-user/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useActivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/auth/activate-user/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/auth/deactivate-user/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}
