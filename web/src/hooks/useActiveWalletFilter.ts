import { useWalletContext } from "@/context/wallet-context";

/**
 * Returns wallet_id filter object based on the active wallet.
 * Returns `{ wallet_id: "123" }` when a wallet is selected,
 * or `{}` (empty) for the consolidated view.
 */
export function useActiveWalletFilter(): Record<string, string> {
  const { activeWallet } = useWalletContext();
  if (!activeWallet) return {};
  return { wallet_id: String(activeWallet.id) };
}
