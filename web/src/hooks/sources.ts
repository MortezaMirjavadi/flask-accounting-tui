import {
  useWallets,
  useWallet,
  useWalletBalance,
  useWalletTransfers,
  useCreateWallet,
  useUpdateWallet,
  useDeleteWallet,
} from "./wallets";
import type { WalletFormData } from "@/schemas/wallet";

// Backward compat re-exports
export const useSources = useWallets;
export const useSource = useWallet;
export const useSourceBalance = useWalletBalance;
export const useSourceTransfers = useWalletTransfers;
export const useCreateSource = useCreateWallet;
export const useUpdateSource = useUpdateWallet;
export const useDeleteSource = useDeleteWallet;

export type { WalletFormData as SourceFormData };
