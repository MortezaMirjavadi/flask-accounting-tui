import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { toast } from "sonner";
import { Loader2, Moon, Sun } from "lucide-react";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, verify2fa, requires2fa } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored as "light" | "dark";
    return "dark";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await login(username, password);
      if (result.requires_2fa) {
        toast.info(t("auth.verify2fa"));
      } else {
        toast.success(t("auth.loginSuccess"));
        navigate("/");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2fa = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await verify2fa(code);
      toast.success(t("auth.loginSuccess"));
      navigate("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background p-4">
      {/* Top bar with language and theme controls */}
      <div className="flex items-center justify-end gap-2">
        <LanguageSwitcher />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
          className="h-8 w-8"
        >
          {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </Button>
      </div>

      <div className="flex flex-1 items-center justify-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">
              {requires2fa ? t("auth.verify2fa") : t("auth.loginTitle")}
            </CardTitle>
            <CardDescription>
              {requires2fa ? t("auth.twoFaCode") : t("auth.loginDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {requires2fa ? (
              <form onSubmit={handleVerify2fa} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="code">{t("auth.twoFaCode")}</Label>
                  <Input
                    id="code"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="000000"
                    className="text-center text-2xl tracking-widest"
                    dir="ltr"
                    autoFocus
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                  {t("auth.verify")}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="username">{t("auth.username")}</Label>
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    dir="ltr"
                    autoFocus
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">{t("auth.password")}</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    dir="ltr"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                  {t("auth.login")}
                </Button>
              </form>
            )}
          </CardContent>
          {!requires2fa && (
            <CardFooter className="justify-center">
              <p className="text-sm text-muted-foreground">
                {t("auth.noAccount")}{" "}
                <Link
                  to="/register"
                  className="text-primary underline underline-offset-4 hover:text-primary/80"
                >
                  {t("auth.register")}
                </Link>
              </p>
            </CardFooter>
          )}
        </Card>
      </motion.div>
      </div>
    </div>
  );
}
