import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useWalletContext } from "@/context/wallet-context";
import { useWalletInvitations } from "@/hooks/wallets";
import {
  Wallet,
  Users,
  ChevronDown,
  Globe,
  Mail,
  Briefcase,
  Plane,
  PiggyBank,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Wallet as WalletType } from "@/types";

const CURRENCY_SYMBOLS: Record<string, string> = {
  IRR: "تومان",
  USD: "$",
  EUR: "€",
  GBP: "£",
  AED: "د.إ",
};

function getVariantIcon(variant: string | null | undefined) {
  switch (variant) {
    case "family":
      return <Users className="h-4 w-4" />;
    case "team":
      return <Shield className="h-4 w-4" />;
    case "travel":
      return <Plane className="h-4 w-4" />;
    case "business":
      return <Briefcase className="h-4 w-4" />;
    case "savings":
      return <PiggyBank className="h-4 w-4" />;
    default:
      return <Wallet className="h-4 w-4" />;
  }
}

function WalletItem({
  wallet,
  isActive,
  onSelect,
}: {
  wallet: WalletType;
  isActive: boolean;
  onSelect: () => void;
}) {
  return (
    <DropdownMenuItem
      onClick={onSelect}
      className={cn(isActive && "bg-accent")}
    >
      <span className="me-2">{getVariantIcon(wallet.variant)}</span>
      <span className="flex-1 truncate">{wallet.name}</span>
      <div className="flex items-center gap-1">
        {wallet.wallet_type === "shared" && (
          <Badge variant="outline" className="text-[10px] px-1 shrink-0">
            {wallet.role}
          </Badge>
        )}
        <Badge variant="secondary" className="text-[10px] shrink-0">
          {CURRENCY_SYMBOLS[wallet.currency] || wallet.currency}
        </Badge>
      </div>
    </DropdownMenuItem>
  );
}

export function WalletSwitcher() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { activeWallet, setActiveWallet, wallets } = useWalletContext();
  const { data: invitations } = useWalletInvitations();
  const pendingCount = invitations?.total ?? 0;

  if (!wallets || wallets.length === 0) return null;

  const personalWallets = wallets.filter((w) => w.wallet_type === "personal");
  const sharedWallets = wallets.filter((w) => w.wallet_type === "shared");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="relative gap-2 max-w-[220px]">
          {activeWallet ? (
            <>
              {getVariantIcon(activeWallet.variant)}
              <span className="truncate">{activeWallet.name}</span>
              <Badge variant="secondary" className="text-xs shrink-0">
                {CURRENCY_SYMBOLS[activeWallet.currency] || activeWallet.currency}
              </Badge>
            </>
          ) : (
            <>
              <Globe className="h-4 w-4 shrink-0" />
              <span className="truncate">{t("wallets.consolidated")}</span>
            </>
          )}
          {pendingCount > 0 && (
            <span className="absolute -end-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
              {pendingCount}
            </span>
          )}
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[260px]">
        <DropdownMenuItem onClick={() => setActiveWallet(null)}>
          <Globe className="h-4 w-4 me-2" />
          <span className="flex-1">{t("wallets.consolidated")}</span>
          <span className="text-xs text-muted-foreground">
            {wallets.length} {t("wallets.title").toLowerCase()}
          </span>
        </DropdownMenuItem>
        {pendingCount > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => navigate("/wallets")}
              className="text-orange-600 focus:text-orange-600"
            >
              <Mail className="h-4 w-4 me-2" />
              <span className="flex-1">{t("wallets.invitations")}</span>
              <Badge variant="destructive" className="text-xs">
                {pendingCount}
              </Badge>
            </DropdownMenuItem>
          </>
        )}
        <DropdownMenuSeparator />
        {personalWallets.length > 0 && (
          <>
            <DropdownMenuLabel>{t("wallets.personal")}</DropdownMenuLabel>
            {personalWallets.map((wallet) => (
              <WalletItem
                key={wallet.id}
                wallet={wallet}
                isActive={activeWallet?.id === wallet.id}
                onSelect={() => setActiveWallet(wallet)}
              />
            ))}
          </>
        )}
        {sharedWallets.length > 0 && (
          <>
            <DropdownMenuLabel>{t("wallets.shared")}</DropdownMenuLabel>
            {sharedWallets.map((wallet) => (
              <WalletItem
                key={wallet.id}
                wallet={wallet}
                isActive={activeWallet?.id === wallet.id}
                onSelect={() => setActiveWallet(wallet)}
              />
            ))}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
