import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { Account } from "@/types";
import type { AccountFormData } from "@/schemas/wallet";

export function useAccounts(walletId: number) {
  return useQuery({
    queryKey: queryKeys.wallets.accounts(walletId),
    queryFn: () => apiGet<Account[]>(`/wallets/${walletId}/accounts`),
    enabled: !!walletId,
  });
}

export function useAccount(walletId: number, accountId: number) {
  return useQuery({
    queryKey: queryKeys.wallets.accountDetail(walletId, accountId),
    queryFn: () => apiGet<Account>(`/wallets/${walletId}/accounts/${accountId}`),
    enabled: !!walletId && !!accountId,
  });
}

export function useCreateAccount(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AccountFormData) =>
      apiPost<Account>(`/wallets/${walletId}/accounts`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.accounts(walletId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.detail(walletId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useUpdateAccount(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      accountId,
      data,
    }: {
      accountId: number;
      data: Partial<AccountFormData>;
    }) => apiPut(`/wallets/${walletId}/accounts/${accountId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.accounts(walletId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.detail(walletId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}

export function useDeleteAccount(walletId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (accountId: number) =>
      apiDelete(`/wallets/${walletId}/accounts/${accountId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.accounts(walletId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.wallets.detail(walletId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallets.all });
    },
  });
}
