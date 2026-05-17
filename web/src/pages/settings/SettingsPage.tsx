import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { apiPost } from "@/api";
import type { Setup2FAResponse } from "@/types";
import { useAuth } from "@/context/auth-context";
import { useWalletContext } from "@/context/wallet-context";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/keys";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import { toast } from "sonner";
import { Loader2, Trash2, Moon, Sun, Languages, Shield, ShieldOff, ShieldCheck, Check, Wallet } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { wallets, activeWallet, setActiveWallet } = useWalletContext();
  const queryClient = useQueryClient();
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [twoFaSetupOpen, setTwoFaSetupOpen] = useState(false);
  const [twoFaDisableOpen, setTwoFaDisableOpen] = useState(false);
  const [setupStep, setSetupStep] = useState<"init" | "verify">("init");
  const [otpauthUrl, setOtpauthUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [twoFaLoading, setTwoFaLoading] = useState(false);

  const isDark = document.documentElement.classList.contains("dark");

  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark");
    const theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    localStorage.setItem("theme", theme);
  };

  const toggleLanguage = () => {
    const next = i18n.language === "fa" ? "en" : "fa";
    i18n.changeLanguage(next);
  };

  const handleReset = async () => {
    setResetting(true);
    try {
      await apiPost("/settings/reset");
      toast.success(t("common.success"));
      setResetOpen(false);
    } catch {
      toast.error(t("common.error"));
    } finally {
      setResetting(false);
    }
  };

  const handleSetup2fa = async () => {
    setTwoFaLoading(true);
    try {
      const result = await apiPost<Setup2FAResponse>("/auth/setup-2fa", { username: user?.username });
      setSecret(result.secret);
      setOtpauthUrl(result.otpauth_url || result.secret);
      setSetupStep("verify");
    } catch {
      toast.error(t("common.error"));
    } finally {
      setTwoFaLoading(false);
    }
  };

  const handleEnable2fa = async () => {
    if (!code || code.length !== 6) return;
    setTwoFaLoading(true);
    try {
      await apiPost("/auth/enable-2fa", { username: user?.username, secret, code });
      toast.success(t("common.success"));
      setTwoFaSetupOpen(false);
      setSetupStep("init");
      setCode("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.me() });
    } catch {
      toast.error(t("common.error"));
    } finally {
      setTwoFaLoading(false);
    }
  };

  const handleDisable2fa = async () => {
    setTwoFaLoading(true);
    try {
      await apiPost("/auth/disable-2fa", { username: user?.username });
      toast.success(t("common.success"));
      setTwoFaDisableOpen(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.me() });
    } catch {
      toast.error(t("common.error"));
    } finally {
      setTwoFaLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.appearance")}</CardTitle>
          <CardDescription>{t("settings.darkMode")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDark ? (
                <Moon className="h-5 w-5 text-muted-foreground" />
              ) : (
                <Sun className="h-5 w-5 text-muted-foreground" />
              )}
              <Label htmlFor="theme-toggle">{t("settings.darkMode")}</Label>
            </div>
            <Switch id="theme-toggle" checked={isDark} onCheckedChange={toggleTheme} />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Languages className="h-5 w-5 text-muted-foreground" />
              <Label>{t("settings.language")}</Label>
            </div>
            <Button variant="outline" size="sm" onClick={toggleLanguage}>
              {i18n.language === "fa" ? t("common.english") : t("common.persian")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Active Wallet */}
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.activeWallet")}</CardTitle>
          <CardDescription>{t("settings.activeWalletDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {wallets.map((wallet) => (
              <button
                key={wallet.id}
                onClick={() => setActiveWallet(wallet)}
                className={`flex w-full items-center justify-between rounded-lg border p-3 text-start transition-colors hover:bg-muted/50 ${
                  activeWallet?.id === wallet.id ? "border-primary bg-primary/5" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <Wallet className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{wallet.name}</p>
                    <p className="text-xs text-muted-foreground">{wallet.currency}</p>
                  </div>
                </div>
                {activeWallet?.id === wallet.id && (
                  <Check className="h-4 w-4 text-primary" />
                )}
              </button>
            ))}
            {wallets.length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">{t("common.noData")}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Security */}
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.security")}</CardTitle>
          <CardDescription>{t("settings.twoFa")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {user?.totp_enabled ? (
                <ShieldCheck className="h-5 w-5 text-green-600" />
              ) : (
                <ShieldOff className="h-5 w-5 text-muted-foreground" />
              )}
              <div>
                <Label>{t("settings.twoFa")}</Label>
                <p className="text-sm text-muted-foreground">
                  {user?.totp_enabled ? t("settings.twoFaEnabled") : t("settings.twoFaDisabled")}
                </p>
              </div>
            </div>
            {user?.totp_enabled ? (
              <Button variant="destructive" size="sm" onClick={() => setTwoFaDisableOpen(true)}>
                <ShieldOff className="h-4 w-4" />
                {t("settings.disable2fa")}
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSetupStep("init");
                  setCode("");
                  setTwoFaSetupOpen(true);
                }}
              >
                <Shield className="h-4 w-4" />
                {t("settings.enable2fa")}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">{t("settings.dangerZone")}</CardTitle>
          <CardDescription>{t("settings.resetDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={() => setResetOpen(true)}>
            <Trash2 className="h-4 w-4" />
            {t("settings.resetData")}
          </Button>
        </CardContent>
      </Card>

      {/* Reset Confirmation */}
      <ConfirmDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        title={t("settings.resetData")}
        description={t("common.resetConfirm")}
        confirmLabel={t("settings.resetData")}
        onConfirm={handleReset}
        loading={resetting}
      />

      {/* 2FA Setup Dialog */}
      <ResponsiveDialog
        open={twoFaSetupOpen}
        onOpenChange={(open) => {
          setTwoFaSetupOpen(open);
          if (!open) setSetupStep("init");
        }}
        title={t("settings.setup2fa")}
      >
        {setupStep === "init" ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {t("settings.setup2fa")}
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setTwoFaSetupOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button onClick={handleSetup2fa} disabled={twoFaLoading}>
                {twoFaLoading && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                {t("common.next")}
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-md border bg-white p-3">
                <QRCodeSVG value={otpauthUrl} size={200} />
              </div>
              <p className="text-sm text-muted-foreground">{t("settings.authenticatorUrl")}</p>
            </div>
            <div className="space-y-2">
              <Label>{t("settings.enterCode")}</Label>
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="text-center text-lg tracking-[0.5em]"
                dir="ltr"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setTwoFaSetupOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button
                onClick={handleEnable2fa}
                disabled={twoFaLoading || code.length !== 6}
              >
                {twoFaLoading && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                {t("settings.verifyAndEnable")}
              </Button>
            </div>
          </div>
        )}
      </ResponsiveDialog>

      {/* 2FA Disable Confirmation */}
      <ConfirmDialog
        open={twoFaDisableOpen}
        onOpenChange={setTwoFaDisableOpen}
        title={t("settings.disable2fa")}
        description={t("common.areYouSure")}
        confirmLabel={t("settings.disable2fa")}
        onConfirm={handleDisable2fa}
        loading={twoFaLoading}
      />
    </motion.div>
  );
}
