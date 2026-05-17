import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useCreateWallet } from "@/hooks/wallets";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { toast } from "sonner";
import { Loader2, Wallet } from "lucide-react";

export default function SetupPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const createWallet = useCreateWallet();
  const [walletName, setWalletName] = useState("کیف پول شخصی");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!walletName.trim()) return;

    setLoading(true);
    try {
      await createWallet.mutateAsync({
        name: walletName.trim(),
        currency: "IRR",
        wallet_type: "personal",
      });
      toast.success(t("setup.success"));
      navigate("/", { replace: true });
    } catch {
      toast.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <div className="absolute end-4 top-4">
        <LanguageSwitcher />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Wallet className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">{t("setup.title")}</CardTitle>
            <CardDescription>{t("setup.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="walletName">{t("setup.walletName")}</Label>
                <Input
                  id="walletName"
                  value={walletName}
                  onChange={(e) => setWalletName(e.target.value)}
                  placeholder={t("setup.walletNamePlaceholder")}
                  autoFocus
                  required
                />
              </div>

              <div className="space-y-2">
                <Label>{t("setup.currency")}</Label>
                <div className="flex h-10 w-full items-center rounded-md border bg-muted px-3 text-sm">
                  IRR - تومان
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="me-2 h-4 w-4 animate-spin" />
                    {t("setup.creating")}
                  </>
                ) : (
                  t("setup.createWallet")
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
