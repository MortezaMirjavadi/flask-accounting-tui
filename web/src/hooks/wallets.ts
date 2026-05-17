import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type {
  Wallet,
  WalletMember,
  WalletInvitation,
  WalletActivity,
  ExchangeRate,
  ConsolidatedBalance,
} from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { WalletFormData } from "@/schemas/wallet";
import type { TransferReport } from "@/types";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

// ── Queries ─────────────────────────────────────────────────────────

export function useWallets(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.wallets.list(pagination as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<Wallet>>(`/wallets${qs ? "?" + qs : ""}`),
  });
}

export function useWallet(id: number) {
  return useQuery({
    queryKey: queryKeys.wallets.detail(id),
    queryFn: () => apiGet<Wallet>(`/wallets/${id}`),
    enabled: !!id,
  });
}

export function useWalletBalance(id: number) {
  return useQuery({
    queryKey: queryKeys.wallets.balance(id),
    queryFn: () =>
      apiGet<{
        wallet_id: number;
        wallet_name: string;
        currency: string;
        initial_amount: number;
        total_income: number;
        total_cost: number;
        balance: number;
      }>(`/wallets/${id}/balance`),
    enabled: !!id,
  });
}

export function useWalletTransfers(id: number, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.wallets.transfers(id),
    queryFn: () => apiGet<TransferReport & ApiListResponse<unknown>>(`/wallets/${id}/transfers${qs ? "?" + qs : ""}`),
    enabled: !!id,
  });
}

export function useWalletMembers(id: number, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.wallets.members(id),
    queryFn: () => apiGet<ApiListResponse<WalletMember>>(`/wallets/${id}/members${qs ? "?" + qs : ""}`),
    enabled: !!id,
  });
}

export function useWalletActivity(id: number, pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.wallets.activity(id),
    queryFn: () => apiGet<ApiListResponse<WalletActivity>>(`/wallets/${id}/activity${qs ? "?" + qs : ""}`),
    enabled: !!id,
  });
}

export function useWalletInvitations(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.wallets.invitations(),
    queryFn: () => apiGet<ApiListResponse<WalletInvitation>>(`/wallets/invitations${qs ? "?" + qs : ""}`),
  });
}

export function useConsolidatedBalance() {
  return useQuery({
    queryKey: queryKeys.wallets.consolidated(),
    queryFn: () => apiGet<ConsolidatedBalance>("/wallets/consolidated"),
  });
}

// ── Mutations ───────────────────────────────────────────────────────

export function useCreateWallet() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WalletFormData) => apiPost<Wallet>("/wallets", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useUpdateWallet() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: WalletFormData }) =>
      apiPut<Wallet>(`/wallets/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useDeleteWallet() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/wallets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useInviteToWallet(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { username: string; role: "editor" | "viewer" }) =>
      apiPost(`/wallets/${walletId}/invite`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.members(walletId),
      });
    },
  });
}

export function useRemoveMember(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) =>
      apiPost(`/wallets/${walletId}/members/${userId}/remove`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.members(walletId),
      });
    },
  });
}

export function useUpdateMemberRole(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      role,
    }: {
      userId: number;
      role: "editor" | "viewer";
    }) => apiPut(`/wallets/${walletId}/members/${userId}/role`, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.members(walletId),
      });
    },
  });
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: number) =>
      apiPost(`/wallets/invitations/${invitationId}/accept`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.invitations(),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useRejectInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: number) =>
      apiPost(`/wallets/invitations/${invitationId}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.invitations(),
      });
    },
  });
}

// ── Exchange Rates ──────────────────────────────────────────────────

export function useExchangeRates() {
  return useQuery({
    queryKey: queryKeys.exchangeRates.list(),
    queryFn: () => apiGet<ExchangeRate[]>("/exchange-rates"),
  });
}

export function useCreateExchangeRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      from_currency: string;
      to_currency: string;
      rate: number;
    }) => apiPost<ExchangeRate>("/exchange-rates", data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.exchangeRates.all,
      });
    },
  });
}

export function useUpdateExchangeRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: { from_currency: string; to_currency: string; rate: number };
    }) => apiPut<ExchangeRate>(`/exchange-rates/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.exchangeRates.all,
      });
    },
  });
}

export function useDeleteExchangeRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/exchange-rates/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.exchangeRates.all,
      });
    },
  });
}

export function useSupportedCurrencies() {
  return useQuery({
    queryKey: queryKeys.exchangeRates.currencies(),
    queryFn: () => apiGet<string[]>("/exchange-rates/currencies"),
  });
}
