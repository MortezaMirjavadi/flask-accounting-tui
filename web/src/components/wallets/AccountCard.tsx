import { useTranslation } from "react-i18next";
import { Pencil, Trash2, Star } from "lucide-react";
import type { Account } from "@/types";
import { formatToman, formatCurrency } from "@/lib/format";
import { getBankById } from "@/lib/bankConfig";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface AccountCardProps {
  account: Account;
  walletCurrency: string;
  editable?: boolean;
  onEdit?: (account: Account) => void;
  onDelete?: (account: Account) => void;
}

const CURRENCY_LABELS: Record<string, string> = {
  IRR: "IRR",
  USD: "USD",
  EUR: "EUR",
  GBP: "GBP",
  AED: "AED",
};

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: "wallets.cash",
  bank: "wallets.bank",
  card: "wallets.card",
  savings: "wallets.savings",
  wallet: "wallets.wallet",
  other: "wallets.other",
};

export function AccountCard({
  account,
  walletCurrency,
  editable = false,
  onEdit,
  onDelete,
}: AccountCardProps) {
  const { t } = useTranslation();
  const bank = getBankById(account.bank_type);
  const numericAmount = Number(account.amount) || 0;

  return (
    <div
      className="relative overflow-hidden rounded-xl p-5 shadow-md"
      style={{ background: bank.gradient }}
    >
      {/* Decorative circle */}
      <div
        className="absolute -bottom-6 -end-6 h-24 w-24 rounded-full opacity-10"
        style={{ backgroundColor: bank.textColor }}
      />

      {/* Header row: bank name + actions */}
      <div className="relative mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold backdrop-blur-sm"
            style={{ color: bank.textColor }}
          >
            {bank.name}
          </span>
          {account.is_default && (
            <span
              className="flex items-center gap-1 rounded-full bg-white/20 px-2 py-1 text-xs backdrop-blur-sm"
              style={{ color: bank.textColor }}
            >
              <Star className="h-3 w-3 fill-current" />
              {t("wallets.default")}
            </span>
          )}
        </div>

        {editable && (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 bg-white/10 hover:bg-white/25"
              onClick={() => onEdit?.(account)}
            >
              <Pencil className="h-3.5 w-3.5" style={{ color: bank.textColor }} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 bg-white/10 hover:bg-white/25"
              onClick={() => onDelete?.(account)}
            >
              <Trash2 className="h-3.5 w-3.5" style={{ color: bank.textColor }} />
            </Button>
          </div>
        )}
      </div>

      {/* Account name */}
      <p
        className="mb-1 truncate text-sm font-medium opacity-80"
        style={{ color: bank.textColor }}
      >
        {account.name}
      </p>

      {/* Balance */}
      <p
        className="text-3xl font-bold tracking-wide"
        style={{ color: bank.textColor }}
      >
        {formatCurrency(numericAmount, walletCurrency)}
      </p>

      {/* Footer badges */}
      <div className="mt-3 flex items-center gap-2">
        <Badge
          variant="secondary"
          className="bg-white/20 text-xs backdrop-blur-sm border-0"
          style={{ color: bank.textColor }}
        >
          {CURRENCY_LABELS[walletCurrency] ?? walletCurrency}
        </Badge>
        <Badge
          variant="secondary"
          className="bg-white/20 text-xs capitalize backdrop-blur-sm border-0"
          style={{ color: bank.textColor }}
        >
          {t(ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type)}
        </Badge>
      </div>
    </div>
  );
}

export function AccountCardSkeleton() {
  return <Skeleton className="h-44 w-full rounded-xl" />;
}
