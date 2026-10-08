import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Plus,
  Pencil,
  Trash2,
  CreditCard,
  ChevronDown,
  Star,
  Wallet,
} from "lucide-react";
import { useWallets } from "@/hooks/wallets";
import {
  useAccounts,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
} from "@/hooks/accounts";
import { accountSchema, type AccountFormData, type AccountFormInput } from "@/schemas/wallet";
import type { Account } from "@/types";
import { BANK_TYPES, getBankById } from "@/lib/bankConfig";
import { formatToman, formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { useWalletContext } from "@/context/wallet-context";

const ACCOUNT_TYPES = [
  { value: "cash", labelKey: "wallets.cashAccount" },
  { value: "bank", labelKey: "wallets.bankAccount" },
  { value: "card", labelKey: "wallets.cardAccount" },
  { value: "savings", labelKey: "wallets.savingsAccount" },
  { value: "wallet", labelKey: "wallets.walletAccount" },
  { value: "other", labelKey: "wallets.otherAccount" },
] as const;

function AccountFormDialog({
  open,
  onOpenChange,
  walletId,
  account,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  walletId: number;
  account?: Account | null;
}) {
  const { t } = useTranslation();
  const isEdit = !!account;
  const createMutation = useCreateAccount(walletId);
  const updateMutation = useUpdateAccount(walletId);

  const form = useForm<AccountFormInput, unknown, AccountFormData>({
    resolver: zodResolver(accountSchema),
    defaultValues: {
      name: "",
      account_type: "cash",
      bank_type: "cash",
      amount: 0,
      description: "",
      sort_order: 0,
    },
  });

  // Reset form when dialog opens with account data
  useState(() => {
    if (account) {
      form.reset({
        name: account.name,
        account_type: account.account_type,
        bank_type: account.bank_type || "cash",
        amount: Number(account.amount) || 0,
        description: account.description || "",
        sort_order: account.sort_order || 0,
      });
    } else {
      form.reset({
        name: "",
        account_type: "cash",
        bank_type: "cash",
        amount: 0,
        description: "",
        sort_order: 0,
      });
    }
  });

  // Track previous account to reset when it changes
  const [prevAccount, setPrevAccount] = useState<Account | null>(null);
  if (account !== prevAccount) {
    setPrevAccount(account);
    if (account) {
      form.reset({
        name: account.name,
        account_type: account.account_type,
        bank_type: account.bank_type || "cash",
        amount: Number(account.amount) || 0,
        description: account.description || "",
        sort_order: account.sort_order || 0,
      });
    } else {
      form.reset({
        name: "",
        account_type: "cash",
        bank_type: "cash",
        amount: 0,
        description: "",
        sort_order: 0,
      });
    }
  }

  async function onSubmit(data: AccountFormData) {
    try {
      if (isEdit) {
        await updateMutation.mutateAsync({ accountId: account!.id, data });
        toast.success(t("common.success"));
      } else {
        await createMutation.mutateAsync(data);
        toast.success(t("common.success"));
      }
      onOpenChange(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={onOpenChange}
      title={isEdit ? t("wallets.editAccount") : t("wallets.addAccount")}
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("wallets.accountName")}</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="account_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("wallets.accountType")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {ACCOUNT_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {t(type.labelKey)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="bank_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("sources.bank")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {BANK_TYPES.map((bank) => (
                      <SelectItem key={bank.id} value={bank.id}>
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-block h-3 w-3 rounded-full"
                            style={{ backgroundColor: bank.color }}
                          />
                          {bank.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="amount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("sources.initialAmount")}</FormLabel>
                <FormControl>
                  <AmountInput
                    value={field.value ?? 0}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("wallets.description")}</FormLabel>
                <FormControl>
                  <Textarea
                    {...field}
                    value={field.value ?? ""}
                    rows={2}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? t("common.loading") : isEdit ? t("common.save") : t("common.create")}
            </Button>
          </div>
        </form>
      </Form>
    </ResponsiveDialog>
  );
}

export default function SourcesPage() {
  const { t } = useTranslation();
  const { activeWallet, wallets, setActiveWallet } = useWalletContext();

  // Use active wallet from header, or let user pick one
  const [selectedWalletId, setSelectedWalletId] = useState<number | null>(
    activeWallet?.id ?? null
  );

  const selectedWallet = wallets?.find((w) => w.id === selectedWalletId);
  const { data: accounts, isLoading: accountsLoading } = useAccounts(selectedWalletId ?? 0);
  const deleteMutation = useDeleteAccount(selectedWalletId ?? 0);

  const [formOpen, setFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function handleDelete(accountId: number) {
    try {
      await deleteMutation.mutateAsync(accountId);
      toast.success(t("common.success"));
      setDeletingId(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("wallets.accounts")}</h1>
        {selectedWalletId && (
          <Button
            size="sm"
            onClick={() => {
              setEditingAccount(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            {t("wallets.addAccount")}
          </Button>
        )}
      </div>

      {/* Wallet selector */}
      {!selectedWalletId || !activeWallet ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("wallets.selectWallet")}
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {wallets?.map((wallet) => {
              const bank = getBankById("cash");
              const walletBalance = wallet.total_balance ?? 0;
              return (
                <Card
                  key={wallet.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50"
                  onClick={() => {
                    setSelectedWalletId(wallet.id);
                    setActiveWallet(wallet);
                  }}
                >
                  <CardContent className="flex items-center gap-3 p-4">
                    <div
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                      style={{ background: bank.gradient }}
                    >
                      {wallet.wallet_type === "shared" ? (
                        <Wallet className="h-5 w-5" style={{ color: bank.textColor }} />
                      ) : (
                        <CreditCard className="h-5 w-5" style={{ color: bank.textColor }} />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{wallet.name}</p>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {wallet.currency}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatCurrency(walletBalance, wallet.currency)}
                        </span>
                      </div>
                    </div>
                    <ChevronDown className="h-4 w-4 shrink-0 rotate-[-90deg] text-muted-foreground" />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Selected wallet header */}
          <div className="flex items-center gap-3 rounded-lg border p-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedWalletId(null)}
            >
              {t("common.cancel")}
            </Button>
            <div className="flex-1">
              <p className="text-sm font-medium">{selectedWallet?.name}</p>
              <p className="text-xs text-muted-foreground">
                {selectedWallet?.wallet_type === "shared"
                  ? t("wallets.shared")
                  : t("wallets.personal")}{" "}
                · {selectedWallet?.currency}
              </p>
            </div>
          </div>

          {/* Accounts list */}
          {accountsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full rounded-lg" />
              ))}
            </div>
          ) : !accounts || accounts.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              {t("common.noData")}
            </p>
          ) : (
            <div className="space-y-3">
              {accounts.map((account) => {
                const bank = getBankById(account.bank_type);
                const numericAmount = Number(account.amount) || 0;

                if (deletingId === account.id) {
                  return (
                    <div
                      key={account.id}
                      className="flex items-center justify-between rounded-lg border-2 border-destructive p-4"
                    >
                      <p className="text-sm">{t("wallets.deleteAccountConfirm")}</p>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDelete(account.id)}
                          disabled={deleteMutation.isPending}
                        >
                          {t("common.confirm")}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setDeletingId(null)}
                        >
                          {t("common.cancel")}
                        </Button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={account.id}
                    className="flex items-center gap-4 rounded-lg border p-4"
                  >
                    {/* Bank color dot + icon */}
                    <div
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                      style={{ background: bank.gradient }}
                    >
                      <CreditCard
                        className="h-5 w-5"
                        style={{ color: bank.textColor }}
                      />
                    </div>

                    {/* Account info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-medium">
                          {account.name}
                        </p>
                        {account.is_default && (
                          <Badge variant="secondary" className="text-xs gap-1">
                            <Star className="h-3 w-3" />
                            {t("wallets.defaultAccount")}
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {t(`wallets.${account.account_type}Account`)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-lg font-bold">
                          {formatCurrency(numericAmount, selectedWallet?.currency ?? "IRR")}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {selectedWallet?.currency}
                        </Badge>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                          setEditingAccount(account);
                          setFormOpen(true);
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      {!account.is_default && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setDeletingId(account.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Account Form Dialog */}
      {selectedWalletId && (
        <AccountFormDialog
          open={formOpen}
          onOpenChange={(open) => {
            setFormOpen(open);
            if (!open) setEditingAccount(null);
          }}
          walletId={selectedWalletId}
          account={editingAccount}
        />
      )}
    </motion.div>
  );
}
