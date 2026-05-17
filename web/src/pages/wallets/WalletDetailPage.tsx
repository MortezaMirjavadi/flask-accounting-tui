import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  Wallet,
  Users,
  Activity,
  Settings,
  UserPlus,
  UserMinus,
  Shield,
  Pencil,
  ArrowRightLeft,
  Globe,
  Plus,
  CreditCard,
} from "lucide-react";
import {
  useWallet,
  useWalletBalance,
  useWalletMembers,
  useWalletActivity,
  useUpdateWallet,
  useInviteToWallet,
  useRemoveMember,
  useUpdateMemberRole,
} from "@/hooks/wallets";
import { useAccounts, useDeleteAccount } from "@/hooks/accounts";
import { walletSchema, type WalletFormData } from "@/schemas/wallet";
import { SUPPORTED_CURRENCIES, type Account } from "@/types";
import { formatToman, formatJalali, formatCurrency } from "@/lib/format";
import { getBankById } from "@/lib/bankConfig";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import { AccountCard, AccountCardSkeleton } from "@/components/wallets/AccountCard";
import { AccountFormDialog } from "@/components/wallets/AccountFormDialog";
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

const CURRENCY_LABELS: Record<string, string> = {
  IRR: "IRR (تومان)",
  USD: "USD ($)",
  EUR: "EUR (€)",
  GBP: "GBP (£)",
  AED: "AED (د.إ)",
};

function RoleBadge({ role }: { role: string }) {
  const variant =
    role === "owner"
      ? "default"
      : role === "editor"
        ? "secondary"
        : "outline";
  return (
    <Badge variant={variant} className="capitalize">
      {role}
    </Badge>
  );
}

function MembersTab({ walletId }: { walletId: number }) {
  const { t } = useTranslation();
  const { data: members, isLoading } = useWalletMembers(walletId);
  const removeMember = useRemoveMember(walletId);
  const updateRole = useUpdateMemberRole(walletId);
  const inviteMutation = useInviteToWallet(walletId);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviteRole, setInviteRole] = useState<"editor" | "viewer">("viewer");
  const [removingId, setRemovingId] = useState<number | null>(null);

  const { data: wallet } = useWallet(walletId);
  const isOwner = wallet?.role === "owner";

  async function handleInvite() {
    if (!inviteUsername.trim()) return;
    try {
      await inviteMutation.mutateAsync({
        username: inviteUsername.trim(),
        role: inviteRole,
      });
      toast.success(t("wallets.inviteSent"));
      setInviteOpen(false);
      setInviteUsername("");
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleRemove(userId: number) {
    try {
      await removeMember.mutateAsync(userId);
      toast.success(t("common.success"));
      setRemovingId(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleChangeRole(
    userId: number,
    newRole: "editor" | "viewer",
  ) {
    try {
      await updateRole.mutateAsync({ userId, role: newRole });
      toast.success(t("common.success"));
    } catch {
      toast.error(t("common.error"));
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {isOwner && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => setInviteOpen(true)}>
            <UserPlus className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.invite")}
          </Button>
        </div>
      )}

      {!members || members.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">
          {t("wallets.noMembers")}
        </p>
      ) : (
        <div className="space-y-2">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                  {member.display_name?.[0] ?? member.username[0]}
                </div>
                <div>
                  <p className="text-sm font-medium">
                    {member.display_name || member.username}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    @{member.username}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <RoleBadge role={member.role} />
                {isOwner && member.role !== "owner" && (
                  <>
                    <Select
                      value={member.role}
                      onValueChange={(val) =>
                        handleChangeRole(
                          member.user_id,
                          val as "editor" | "viewer",
                        )
                      }
                    >
                      <SelectTrigger className="h-8 w-[100px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="editor">
                          {t("wallets.editor")}
                        </SelectItem>
                        <SelectItem value="viewer">
                          {t("wallets.viewer")}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {removingId === member.user_id ? (
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRemove(member.user_id)}
                        >
                          {t("common.confirm")}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setRemovingId(null)}
                        >
                          {t("common.cancel")}
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setRemovingId(member.user_id)}
                      >
                        <UserMinus className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Invite Dialog */}
      <ResponsiveDialog
        open={inviteOpen}
        onOpenChange={setInviteOpen}
        title={t("wallets.invite")}
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("common.name")}
            </label>
            <Input
              placeholder="username"
              value={inviteUsername}
              onChange={(e) => setInviteUsername(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("wallets.yourRole")}
            </label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={inviteRole === "viewer" ? "default" : "outline"}
                size="sm"
                onClick={() => setInviteRole("viewer")}
                className="flex-1"
              >
                {t("wallets.viewer")}
              </Button>
              <Button
                type="button"
                variant={inviteRole === "editor" ? "default" : "outline"}
                size="sm"
                onClick={() => setInviteRole("editor")}
                className="flex-1"
              >
                {t("wallets.editor")}
              </Button>
            </div>
          </div>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              variant="outline"
              onClick={() => setInviteOpen(false)}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleInvite}
              disabled={inviteMutation.isPending || !inviteUsername.trim()}
            >
              {t("wallets.invite")}
            </Button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

function ActivityTab({ walletId }: { walletId: number }) {
  const { t } = useTranslation();
  const { data: activities, isLoading } = useWalletActivity(walletId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        {t("common.noData")}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {activities.map((activity) => (
        <div
          key={activity.id}
          className="flex items-start gap-3 rounded-lg border p-3"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
            <Activity className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm">
              <span className="font-medium">
                {activity.display_name || activity.username}
              </span>{" "}
              <span className="text-muted-foreground">
                {activity.action}
              </span>
            </p>
            <p className="text-xs text-muted-foreground">
              {formatJalali(activity.created_at)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function SettingsTab({ walletId }: { walletId: number }) {
  const { t } = useTranslation();
  const { data: wallet, isLoading } = useWallet(walletId);
  const updateMutation = useUpdateWallet();

  const form = useForm<WalletFormData>({
    resolver: zodResolver(walletSchema),
    defaultValues: {
      name: "",
      currency: "IRR",
      wallet_type: "personal",
    },
  });

  // Sync form with loaded wallet data
  if (wallet && !form.formState.isDirty && !form.formState.isSubmitted) {
    const current = form.getValues();
    if (current.name !== wallet.name) {
      form.reset({
        name: wallet.name,
        currency: wallet.currency,
        wallet_type: wallet.wallet_type,
      });
    }
  }

  const isOwner = wallet?.role === "owner";

  async function onSubmit(data: WalletFormData) {
    try {
      await updateMutation.mutateAsync({ id: walletId, data });
      toast.success(t("common.success"));
    } catch {
      toast.error(t("common.error"));
    }
  }

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!isOwner) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        {t("common.noData")}
      </p>
    );
  }

  return (
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
                  {t("wallets.personal")}
                </Button>
                <Button
                  type="button"
                  variant={
                    field.value === "shared" ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => field.onChange("shared")}
                  className="flex-1"
                >
                  {t("wallets.shared")}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={updateMutation.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Form>
  );
}

function AccountsTab({ walletId }: { walletId: number }) {
  const { t } = useTranslation();
  const { data: wallet } = useWallet(walletId);
  const { data: accounts, isLoading } = useAccounts(walletId);
  const deleteMutation = useDeleteAccount(walletId);
  const [formOpen, setFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const isOwner = wallet?.role === "owner";
  const canEdit = wallet?.role === "owner" || wallet?.role === "editor";

  function handleEdit(account: Account) {
    setEditingAccount(account);
    setFormOpen(true);
  }

  function handleDelete(account: Account) {
    if (account.is_default) {
      toast.error(t("wallets.cannotDeleteDefault"));
      return;
    }
    setDeletingId(account.id);
  }

  async function confirmDelete(accountId: number) {
    try {
      await deleteMutation.mutateAsync(accountId);
      toast.success(t("common.success"));
      setDeletingId(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  return (
    <div className="space-y-4">
      {canEdit && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => { setEditingAccount(null); setFormOpen(true); }}>
            <Plus className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.addAccount")}
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <AccountCardSkeleton key={i} />
          ))}
        </div>
      ) : !accounts || accounts.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">
          {t("common.noData")}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {accounts.map((account) =>
            deletingId === account.id ? (
              <div
                key={account.id}
                className="flex items-center justify-between rounded-xl border-2 border-destructive p-5"
              >
                <p className="text-sm">{t("wallets.deleteAccountConfirm")}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="destructive" onClick={() => confirmDelete(account.id)}>
                    {t("common.confirm")}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setDeletingId(null)}>
                    {t("common.cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <AccountCard
                key={account.id}
                account={account}
                walletCurrency={wallet?.currency ?? "IRR"}
                editable={canEdit && (isOwner || !account.is_default)}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            )
          )}
        </div>
      )}

      <AccountFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        walletId={walletId}
        account={editingAccount}
      />
    </div>
  );
}

export default function WalletDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const walletId = Number(id);

  const { data: wallet, isLoading: walletLoading } = useWallet(walletId);
  const { data: balance, isLoading: balanceLoading } =
    useWalletBalance(walletId);

  if (walletLoading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="space-y-6"
      >
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full" />
      </motion.div>
    );
  }

  if (!wallet) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        {t("common.noData")}
      </div>
    );
  }

  // Wallets don't have bank_type anymore; use default
  const bank = getBankById("cash");
  const balanceAmount = balance?.total_balance ?? wallet.total_balance ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/wallets")}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Wallet className="h-6 w-6" />
        <div>
          <h1 className="text-2xl font-bold">{wallet.name}</h1>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{wallet.currency}</Badge>
            <Badge variant="outline" className="capitalize">
              {wallet.wallet_type === "personal"
                ? t("wallets.personal")
                : t("wallets.shared")}
            </Badge>
            {wallet.role && <RoleBadge role={wallet.role} />}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="overview">
            <Wallet className="me-1.5 h-3.5 w-3.5" />
            {t("common.balance")}
          </TabsTrigger>
          <TabsTrigger value="accounts">
            <CreditCard className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.accounts")}
          </TabsTrigger>
          <TabsTrigger value="members">
            <Users className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.members")}
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.activity")}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="me-1.5 h-3.5 w-3.5" />
            {t("wallets.settings")}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="space-y-4">
            {/* Balance Card */}
            <div
              className="relative overflow-hidden rounded-xl p-6 shadow-md"
              style={{ background: bank.gradient }}
            >
              <div className="mb-2 flex items-center gap-2">
                <span
                  className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold backdrop-blur-sm"
                  style={{ color: bank.textColor }}
                >
                  {bank.name}
                </span>
                <Badge
                  variant="secondary"
                  className="bg-white/20 text-xs backdrop-blur-sm border-0"
                  style={{ color: bank.textColor }}
                >
                  {wallet.currency}
                </Badge>
              </div>
              <p
                className="mb-1 text-sm font-medium opacity-80"
                style={{ color: bank.textColor }}
              >
                {t("wallets.balance")}
              </p>
              {balanceLoading ? (
                <Skeleton className="h-10 w-48 bg-white/20" />
              ) : (
                <p
                  className="text-4xl font-bold tracking-wide"
                  style={{ color: bank.textColor }}
                >
                  {formatCurrency(balanceAmount, wallet.currency)}
                </p>
              )}
              <div
                className="absolute -bottom-6 -end-6 h-24 w-24 rounded-full opacity-10"
                style={{ backgroundColor: bank.textColor }}
              />
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Card
                className="cursor-pointer transition-colors hover:bg-muted/50"
                onClick={() => navigate(`/wallets/${walletId}/transfers`)}
              >
                <CardContent className="flex items-center gap-3 p-4">
                  <ArrowRightLeft className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">
                      {t("wallets.transfers")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("sources.transferReport")}
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="flex items-center gap-3 p-4">
                  <Shield className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">
                      {t("wallets.yourRole")}
                    </p>
                    <p className="text-xs capitalize text-muted-foreground">
                      {wallet.role ?? "—"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Accounts Tab */}
        <TabsContent value="accounts">
          <AccountsTab walletId={walletId} />
        </TabsContent>

        {/* Members Tab */}
        <TabsContent value="members">
          <MembersTab walletId={walletId} />
        </TabsContent>

        {/* Activity Tab */}
        <TabsContent value="activity">
          <ActivityTab walletId={walletId} />
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <SettingsTab walletId={walletId} />
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
