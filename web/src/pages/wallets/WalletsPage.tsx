import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Plus,
  Pencil,
  Trash2,
  Wallet,
  ArrowRightLeft,
  Users,
  User,
  Globe,
  Mail,
  Check,
  X,
  Briefcase,
  Plane,
  PiggyBank,
  Shield,
  CreditCard,
} from "lucide-react";
import {
  useWallets,
  useCreateWallet,
  useUpdateWallet,
  useDeleteWallet,
  useWalletInvitations,
  useAcceptInvitation,
  useRejectInvitation,
} from "@/hooks/wallets";
import { walletSchema, type WalletFormData } from "@/schemas/wallet";
import type { Wallet as WalletType } from "@/types";
import { SUPPORTED_CURRENCIES } from "@/types";
import { formatToman, formatCurrency } from "@/lib/format";
import { getBankById } from "@/lib/bankConfig";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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
import { toast } from "sonner";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

const CURRENCY_LABELS: Record<string, string> = {
  IRR: "IRR (تومان)",
  USD: "USD ($)",
  EUR: "EUR (€)",
  GBP: "GBP (£)",
  AED: "AED (د.إ)",
};

function getVariantIcon(variant: string | null | undefined, size = "h-4 w-4") {
  const cls = size;
  switch (variant) {
    case "family": return <Users className={cls} />;
    case "team": return <Shield className={cls} />;
    case "travel": return <Plane className={cls} />;
    case "business": return <Briefcase className={cls} />;
    case "savings": return <PiggyBank className={cls} />;
    default: return null;
  }
}

const VARIANT_OPTIONS = [
  { value: "", label: "—" },
  { value: "family", label: "family" },
  { value: "team", label: "team" },
  { value: "travel", label: "travel" },
  { value: "business", label: "business" },
  { value: "savings", label: "savings" },
] as const;

function WalletCard({
  wallet,
  onEdit,
  onDelete,
}: {
  wallet: WalletType;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  // Wallets don't have bank_type anymore; use a default gradient
  const bank = getBankById("cash");
  const isShared = wallet.wallet_type === "shared";
  const variantIcon = getVariantIcon(wallet.variant);
  const displayBalance = wallet.total_balance ?? 0;

  return (
    <motion.div variants={fadeUp}>
      <Link to={`/wallets/${wallet.id}`}>
        <div
          className="relative overflow-hidden rounded-xl p-5 shadow-md transition-shadow hover:shadow-lg"
          style={{ background: bank.gradient }}
        >
          {/* Top badges */}
          <div className="mb-4 flex items-start justify-between">
            <div className="flex items-center gap-2">
              {variantIcon ? (
                <span
                  className="flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-xs font-semibold backdrop-blur-sm"
                  style={{ color: bank.textColor }}
                >
                  {variantIcon}
                  {t(`wallets.variant${wallet.variant?.charAt(0).toUpperCase()}${wallet.variant?.slice(1)}`)}
                </span>
              ) : (
                <span
                  className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold backdrop-blur-sm"
                  style={{ color: bank.textColor }}
                >
                  {bank.name}
                </span>
              )}
              <Badge
                variant="secondary"
                className="bg-white/20 text-xs backdrop-blur-sm border-0"
                style={{ color: bank.textColor }}
              >
                {wallet.currency}
              </Badge>
              {wallet.account_count != null && wallet.account_count > 1 && (
                <Badge
                  variant="secondary"
                  className="bg-white/20 text-xs backdrop-blur-sm border-0"
                  style={{ color: bank.textColor }}
                >
                  <CreditCard className="me-1 h-3 w-3" />
                  {wallet.account_count}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              {isShared ? (
                <Users className="h-4 w-4" style={{ color: bank.textColor }} />
              ) : (
                <User className="h-4 w-4" style={{ color: bank.textColor }} />
              )}
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onEdit();
                }}
                className="rounded-full p-1.5 transition-colors hover:bg-white/20"
              >
                <Pencil
                  className="h-3.5 w-3.5"
                  style={{ color: bank.textColor }}
                />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onDelete();
                }}
                className="rounded-full p-1.5 transition-colors hover:bg-white/20"
              >
                <Trash2
                  className="h-3.5 w-3.5"
                  style={{ color: bank.textColor }}
                />
              </button>
            </div>
          </div>

          {/* Wallet name */}
          <p
            className="mb-1 text-sm font-medium opacity-80"
            style={{ color: bank.textColor }}
          >
            {wallet.name}
          </p>

          {/* Balance */}
          <p
            className="text-2xl font-bold tracking-wide"
            style={{ color: bank.textColor }}
          >
            {formatCurrency(displayBalance, wallet.currency)}
          </p>

          {/* Decorative circle */}
          <div
            className="absolute -bottom-6 -end-6 h-24 w-24 rounded-full opacity-10"
            style={{ backgroundColor: bank.textColor }}
          />
        </div>
      </Link>
    </motion.div>
  );
}

export default function WalletsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: walletsResp, isLoading } = useWallets();
  const wallets = walletsResp?.items;
  const createMutation = useCreateWallet();
  const updateMutation = useUpdateWallet();
  const deleteMutation = useDeleteWallet();
  const { data: invitationsResp } = useWalletInvitations();
  const invitations = invitationsResp?.items ?? [];
  const acceptInvitation = useAcceptInvitation();
  const rejectInvitation = useRejectInvitation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWallet, setEditingWallet] = useState<WalletType | null>(null);
  const [deletingWallet, setDeletingWallet] = useState<WalletType | null>(null);

  const form = useForm<WalletFormData>({
    resolver: zodResolver(walletSchema),
    defaultValues: {
      name: "",
      currency: "IRR",
      wallet_type: "personal",
    },
  });

  function openCreate() {
    setEditingWallet(null);
    form.reset({
      name: "",
      currency: "IRR",
      wallet_type: "personal",
      variant: null,
    });
    setDialogOpen(true);
  }

  function openEdit(wallet: WalletType) {
    setEditingWallet(wallet);
    form.reset({
      name: wallet.name,
      currency: wallet.currency,
      wallet_type: wallet.wallet_type,
      variant: wallet.variant ?? null,
    });
    setDialogOpen(true);
  }

  async function onSubmit(data: WalletFormData) {
    try {
      if (editingWallet) {
        await updateMutation.mutateAsync({ id: editingWallet.id, data });
        toast.success(t("common.success"));
      } else {
        await createMutation.mutateAsync(data);
        toast.success(t("common.success"));
      }
      setDialogOpen(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleDelete() {
    if (!deletingWallet) return;
    try {
      await deleteMutation.mutateAsync(deletingWallet.id);
      toast.success(t("common.success"));
      setDeletingWallet(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  const personalWallets =
    wallets?.filter((w) => w.wallet_type === "personal") ?? [];
  const sharedWallets =
    wallets?.filter((w) => w.wallet_type === "shared") ?? [];

  const totalBalance =
    wallets?.reduce((sum, w) => {
      if (w.currency === "IRR") return sum + (w.total_balance ?? 0);
      return sum;
    }, 0) ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("wallets.title")}</h1>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          {t("wallets.addTitle")}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Total Balance Card — only when wallets exist */}
          {wallets && wallets.length > 0 && (
            <Card className="border-primary/20 bg-primary/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("dashboard.totalBalance")}
                </CardTitle>
                <Wallet className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {formatToman(totalBalance)}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {wallets.length}{" "}
                  {wallets.length === 1
                    ? t("wallets.title").toLowerCase()
                    : t("wallets.title").toLowerCase()}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Tabs — always visible */}
          <Tabs defaultValue="personal">
            <TabsList>
              <TabsTrigger value="personal">
                <User className="me-1.5 h-3.5 w-3.5" />
                {t("wallets.personal")} ({personalWallets.length})
              </TabsTrigger>
              <TabsTrigger value="shared">
                <Users className="me-1.5 h-3.5 w-3.5" />
                {t("wallets.shared")} ({sharedWallets.length})
              </TabsTrigger>
              <TabsTrigger value="invitations">
                <Mail className="me-1.5 h-3.5 w-3.5" />
                {t("wallets.invitations")}
                {invitations && invitations.length > 0 && (
                  <Badge
                    variant="destructive"
                    className="ms-1.5 h-5 min-w-5 px-1 text-xs"
                  >
                    {invitations.length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="personal">
              {personalWallets.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">
                  {t("common.noData")}
                </p>
              ) : (
                <motion.div
                  variants={stagger}
                  initial="hidden"
                  animate="show"
                  className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
                >
                  {personalWallets.map((wallet) => (
                    <WalletCard
                      key={wallet.id}
                      wallet={wallet}
                      onEdit={() => openEdit(wallet)}
                      onDelete={() => setDeletingWallet(wallet)}
                    />
                  ))}
                </motion.div>
              )}
            </TabsContent>

            <TabsContent value="shared">
              {sharedWallets.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">
                  {t("common.noData")}
                </p>
              ) : (
                <motion.div
                  variants={stagger}
                  initial="hidden"
                  animate="show"
                  className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
                >
                  {sharedWallets.map((wallet) => (
                    <WalletCard
                      key={wallet.id}
                      wallet={wallet}
                      onEdit={() => openEdit(wallet)}
                      onDelete={() => setDeletingWallet(wallet)}
                    />
                  ))}
                </motion.div>
              )}
            </TabsContent>

            <TabsContent value="invitations">
              {!invitations || invitations.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">
                  {t("wallets.noInvitations")}
                </p>
              ) : (
                <div className="space-y-3">
                  {invitations.map((inv) => (
                    <Card key={inv.id}>
                      <CardContent className="flex items-center justify-between p-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                            <Mail className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">
                              {inv.wallet_name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {t("wallets.invite")} {t("common.by")}{" "}
                              {inv.inviter_display_name || inv.inviter_name} ·{" "}
                              <Badge
                                variant="outline"
                                className="text-xs capitalize"
                              >
                                {inv.role}
                              </Badge>
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="default"
                            onClick={async () => {
                              try {
                                await acceptInvitation.mutateAsync(inv.id);
                                toast.success(t("wallets.invitationAccepted"));
                              } catch {
                                toast.error(t("common.error"));
                              }
                            }}
                            disabled={acceptInvitation.isPending}
                          >
                            <Check className="me-1 h-3.5 w-3.5" />
                            {t("wallets.accept")}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              try {
                                await rejectInvitation.mutateAsync(inv.id);
                                toast.success(t("wallets.invitationRejected"));
                              } catch {
                                toast.error(t("common.error"));
                              }
                            }}
                            disabled={rejectInvitation.isPending}
                          >
                            <X className="me-1 h-3.5 w-3.5" />
                            {t("wallets.reject")}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Create / Edit Dialog */}
      <ResponsiveDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={editingWallet ? t("wallets.editTitle") : t("wallets.addTitle")}
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("wallets.walletName")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="currency"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("wallets.currency")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {SUPPORTED_CURRENCIES.map((cur) => (
                        <SelectItem key={cur} value={cur}>
                          <div className="flex items-center gap-2">
                            <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                            {CURRENCY_LABELS[cur] ?? cur}
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
              name="wallet_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("wallets.walletType")}</FormLabel>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={
                        field.value === "personal" ? "default" : "outline"
                      }
                      size="sm"
                      onClick={() => field.onChange("personal")}
                      className="flex-1"
                    >
                      <User className="me-1.5 h-3.5 w-3.5" />
                      {t("wallets.personal")}
                    </Button>
                    <Button
                      type="button"
                      variant={field.value === "shared" ? "default" : "outline"}
                      size="sm"
                      onClick={() => field.onChange("shared")}
                      className="flex-1"
                    >
                      <Users className="me-1.5 h-3.5 w-3.5" />
                      {t("wallets.shared")}
                    </Button>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="variant"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("wallets.variant")}</FormLabel>
                  <div className="flex flex-wrap gap-2">
                    {VARIANT_OPTIONS.map((opt) => (
                      <Button
                        key={opt.value}
                        type="button"
                        variant={(field.value ?? "") === opt.value ? "default" : "outline"}
                        size="sm"
                        onClick={() => field.onChange(opt.value || null)}
                        className="gap-1.5"
                      >
                        {getVariantIcon(opt.value, "h-3.5 w-3.5")}
                        {opt.value ? t(`wallets.variant${opt.value.charAt(0).toUpperCase()}${opt.value.slice(1)}`) : opt.label}
                      </Button>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={isPending}>
                {t("common.save")}
              </Button>
            </div>
          </form>
        </Form>
      </ResponsiveDialog>

      {/* Delete Confirmation Dialog */}
      <ResponsiveDialog
        open={!!deletingWallet}
        onOpenChange={() => setDeletingWallet(null)}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
      >
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={() => setDeletingWallet(null)}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isPending}
          >
            {t("common.delete")}
          </Button>
        </div>
      </ResponsiveDialog>
    </motion.div>
  );
}
