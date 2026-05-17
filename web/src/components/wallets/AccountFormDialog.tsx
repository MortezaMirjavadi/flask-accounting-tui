import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useCreateAccount, useUpdateAccount } from "@/hooks/accounts";
import { accountSchema, type AccountFormData } from "@/schemas/wallet";
import type { Account } from "@/types";
import { BANK_TYPES } from "@/lib/bankConfig";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import { AmountInput } from "@/components/shared/AmountInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import { toast } from "sonner";

const ACCOUNT_TYPES = [
  "cash",
  "bank",
  "card",
  "savings",
  "wallet",
  "other",
] as const;

interface AccountFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  walletId: number;
  account?: Account | null;
}

export function AccountFormDialog({
  open,
  onOpenChange,
  walletId,
  account,
}: AccountFormDialogProps) {
  const { t } = useTranslation();
  const isEdit = !!account;

  const createMutation = useCreateAccount(walletId);
  const updateMutation = useUpdateAccount(walletId);

  const form = useForm<AccountFormData>({
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

  // Populate form when editing
  useEffect(() => {
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
  }, [account, form]);

  async function onSubmit(data: AccountFormData) {
    try {
      if (isEdit) {
        await updateMutation.mutateAsync({
          accountId: account!.id,
          data,
        });
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
      title={isEdit ? t("wallets.editAccount") : t("wallets.newAccount")}
      description={
        isEdit ? t("wallets.editAccountDesc") : t("wallets.newAccountDesc")
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* Name */}
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("common.name")}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder={t("wallets.accountNamePlaceholder")} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Account Type */}
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
                      <SelectItem key={type} value={type}>
                        {t(`wallets.${type}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Bank Type */}
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

          {/* Amount */}
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

          {/* Description */}
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
                    placeholder={t("wallets.descriptionPlaceholder")}
                    rows={3}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Actions */}
          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
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
