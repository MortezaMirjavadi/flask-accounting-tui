import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useWallets } from "@/hooks/wallets";
import { STORAGE_KEYS } from "@/lib/constants";
import type { Wallet } from "@/types";

interface WalletContextType {
  activeWallet: Wallet | null;
  setActiveWallet: (wallet: Wallet | null) => void;
  wallets: Wallet[];
  isLoading: boolean;
  needsSetup: boolean;
}

const WalletContext = createContext<WalletContextType | null>(null);

export function WalletProvider({ children }: { children: ReactNode }) {
  const { data: walletsResp, isLoading } = useWallets();
  const wallets = walletsResp?.items ?? [];
  const [activeWalletId, setActiveWalletId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.ACTIVE_WALLET);
    return stored ? parseInt(stored, 10) : null;
  });

  const activeWallet = wallets.find((w) => w.id === activeWalletId) ?? null;

  // Auto-select first wallet if none selected and wallets exist
  useEffect(() => {
    if (!isLoading && wallets.length > 0 && !activeWalletId) {
      setActiveWalletId(wallets[0].id);
      localStorage.setItem(STORAGE_KEYS.ACTIVE_WALLET, String(wallets[0].id));
    }
  }, [isLoading, wallets, activeWalletId]);

  // Reset if wallet no longer exists
  useEffect(() => {
    if (wallets.length > 0 && activeWalletId && !wallets.find((w) => w.id === activeWalletId)) {
      setActiveWalletId(wallets[0].id);
      localStorage.setItem(STORAGE_KEYS.ACTIVE_WALLET, String(wallets[0].id));
    }
  }, [wallets, activeWalletId]);

  const setActiveWallet = useCallback((wallet: Wallet | null) => {
    setActiveWalletId(wallet?.id ?? null);
    if (wallet) {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_WALLET, String(wallet.id));
    } else {
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_WALLET);
    }
  }, []);

  const needsSetup = !isLoading && wallets.length === 0;

  const value: WalletContextType = {
    activeWallet,
    setActiveWallet,
    wallets,
    isLoading,
    needsSetup,
  };

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}

export function useWalletContext(): WalletContextType {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWalletContext must be used within a WalletProvider");
  }
  return context;
}
