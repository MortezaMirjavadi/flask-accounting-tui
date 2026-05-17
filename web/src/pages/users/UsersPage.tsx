import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  UserCog,
  UserPlus,
  Check,
  X,
  Shield,
  ShieldOff,
  Trash2,
  Pencil,
} from "lucide-react";
import {
  useUsers,
  usePendingUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useApproveUser,
  useRejectUser,
  useActivateUser,
  useDeactivateUser,
} from "@/hooks/users";
import { useAuth } from "@/context/auth-context";
import type { User } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import { toast } from "sonner";

function UserFormDialog({
  open,
  onOpenChange,
  user,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null;
}) {
  const { t } = useTranslation();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [username, setUsername] = useState(user?.username ?? "");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [role, setRole] = useState(user?.is_admin ? "admin" : "user");

  const loading = createUser.isPending || updateUser.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (user) {
        await updateUser.mutateAsync({
          id: user.id,
          data: {
            display_name: displayName,
            email,
            is_admin: role === "admin",
            ...(password ? { password } : {}),
          },
        });
      } else {
        await createUser.mutateAsync({
          username,
          password,
          display_name: displayName,
          email,
          role,
        });
      }
      toast.success(t("common.success"));
      onOpenChange(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange} title={user ? t("common.edit") : t("common.create")}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {!user && (
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("auth.username")}</label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
        )}
        <div className="space-y-2">
          <label className="text-sm font-medium">
            {user ? `${t("auth.password")} (${t("common.reset")})` : t("auth.password")}
          </label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!user}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">{t("auth.displayName")}</label>
          <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">{t("auth.email")}</label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">{t("users.role")}</label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={role === "user" ? "default" : "outline"}
              size="sm"
              onClick={() => setRole("user")}
            >
              {t("users.user")}
            </Button>
            <Button
              type="button"
              variant={role === "admin" ? "default" : "outline"}
              size="sm"
              onClick={() => setRole("admin")}
            >
              {t("users.admin")}
            </Button>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={loading}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}

export default function UsersPage() {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const { data: users, isLoading } = useUsers();
  const { data: pendingUsers } = usePendingUsers();

  const [tab, setTab] = useState<"all" | "pending">("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);

  const approveUser = useApproveUser();
  const rejectUser = useRejectUser();
  const activateUser = useActivateUser();
  const deactivateUser = useDeactivateUser();
  const deleteUser = useDeleteUser();

  if (!isAdmin) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">{t("common.error")}</p>
      </div>
    );
  }

  const displayedUsers = tab === "pending" ? pendingUsers ?? [] : users ?? [];

  async function handleAction(action: () => Promise<unknown>, successMsg: string) {
    try {
      await action();
      toast.success(successMsg);
    } catch {
      toast.error(t("common.error"));
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <UserCog className="h-6 w-6" />
          <h1 className="text-2xl font-bold">{t("users.title")}</h1>
        </div>
        <Button
          onClick={() => {
            setEditUser(null);
            setFormOpen(true);
          }}
        >
          <UserPlus className="h-4 w-4" />
          {t("users.addTitle")}
        </Button>
      </div>

      <div className="flex rounded-md border bg-muted/40 p-1">
        <Button
          variant={tab === "all" ? "default" : "ghost"}
          size="sm"
          onClick={() => setTab("all")}
        >
          {t("common.all")}
        </Button>
        <Button
          variant={tab === "pending" ? "default" : "ghost"}
          size="sm"
          onClick={() => setTab("pending")}
        >
          {t("users.pendingApproval")}
          {pendingUsers && pendingUsers.length > 0 && (
            <Badge variant="secondary" className="ms-1">
              {pendingUsers.length}
            </Badge>
          )}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : displayedUsers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("users.noUsers")}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {displayedUsers.map((user) => (
            <Card key={user.id}>
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{user.display_name}</p>
                    <Badge variant={user.is_admin ? "default" : "secondary"}>
                      {user.is_admin ? t("users.admin") : t("users.user")}
                    </Badge>
                    {!user.is_active && (
                      <Badge variant="destructive">{t("common.inactive")}</Badge>
                    )}
                    {!user.is_approved && (
                      <Badge variant="outline">{t("users.pending")}</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    @{user.username}
                    {user.email && ` · ${user.email}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  {!user.is_approved && (
                    <>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-green-600"
                        onClick={() =>
                          handleAction(
                            () => approveUser.mutateAsync(user.id),
                            t("common.success"),
                          )
                        }
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-red-600"
                        onClick={() =>
                          handleAction(
                            () => rejectUser.mutateAsync(user.id),
                            t("common.success"),
                          )
                        }
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                  {user.is_approved && (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() =>
                        handleAction(
                          user.is_active
                            ? () => deactivateUser.mutateAsync(user.id)
                            : () => activateUser.mutateAsync(user.id),
                          t("common.success"),
                        )
                      }
                    >
                      {user.is_active ? (
                        <ShieldOff className="h-4 w-4" />
                      ) : (
                        <Shield className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => {
                      setEditUser(user);
                      setFormOpen(true);
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive"
                    onClick={() =>
                      handleAction(
                        () => deleteUser.mutateAsync(user.id),
                        t("common.success"),
                      )
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <UserFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        user={editUser}
      />
    </motion.div>
  );
}
