import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { Transaction, TransactionItem, TransferListItem } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { TransactionFormData, TransferFormData } from "@/schemas/transaction";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useTransactions(filters?: Record<string, string>, pagination?: PaginationParams) {
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
    queryKey: queryKeys.transactions.list({ ...filters, ...(pagination || {}) } as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<Transaction>>(`/transactions${qs ? "?" + qs : ""}`),
  });
}

export function useTransaction(id: number) {
  return useQuery({
    queryKey: queryKeys.transactions.detail(id),
    queryFn: () => apiGet<Transaction>(`/transactions/${id}`),
    enabled: !!id,
  });
}

export function useTransactionItems(txId: number) {
  return useQuery({
    queryKey: queryKeys.transactions.items(txId),
    queryFn: () => apiGet<TransactionItem[]>(`/transactions/${txId}/items`),
    enabled: !!txId,
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TransactionFormData) =>
      apiPost<Transaction>("/transactions", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TransactionFormData }) =>
      apiPut<Transaction>(`/transactions/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/transactions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useAddTransactionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txId, data }: { txId: number; data: Partial<TransactionItem> }) =>
      apiPost<TransactionItem>(`/transactions/${txId}/items`, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.items(variables.txId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.detail(variables.txId) });
    },
  });
}

export function useUpdateTransactionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txId, itemId, data }: { txId: number; itemId: number; data: Partial<TransactionItem> }) =>
      apiPut<TransactionItem>(`/transactions/${txId}/items/${itemId}`, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.items(variables.txId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.detail(variables.txId) });
    },
  });
}

export function useDeleteTransactionItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txId, itemId }: { txId: number; itemId: number }) =>
      apiDelete(`/transactions/${txId}/items/${itemId}`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.items(variables.txId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.detail(variables.txId) });
    },
  });
}

export function useCreateTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TransferFormData) =>
      apiPost<Transaction>("/transactions", { ...data, is_transfer: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transfers.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useTransfers(filters?: Record<string, string>, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  params.set("include_transfers", "true");
  params.set("category_type", "transfer");
  if (filters) {
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.set(k, String(v));
    });
  }
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  return useQuery({
    queryKey: queryKeys.transfers.list({ ...filters, ...(pagination || {}) } as Record<string, string>),
    queryFn: () =>
      apiGet<ApiListResponse<TransferListItem>>(`/transactions?${params.toString()}`),
  });
}
