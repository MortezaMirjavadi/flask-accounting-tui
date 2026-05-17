import { useTranslation } from "react-i18next";
import { useLocation, Link } from "react-router-dom";
import { useAuth } from "@/context/auth-context";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, Moon, Sun, Settings, Languages } from "lucide-react";
import { useState, useEffect } from "react";

function Breadcrumbs() {
  const { t } = useTranslation();
  const location = useLocation();
  const segments = location.pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <div className="hidden items-center gap-1 text-sm text-muted-foreground md:flex">
      {segments.map((segment, index) => (
        <span key={index} className="flex items-center gap-1">
          {index > 0 && <span>/</span>}
          <span className={index === segments.length - 1 ? "text-foreground font-medium" : ""}>
            {t(`nav.${segment}`, { defaultValue: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ") })}
          </span>
        </span>
      ))}
    </div>
  );
}

export function TopBar() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme");
      if (stored) return stored as "light" | "dark";
    }
    return "dark";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const toggleLanguage = () => {
    const next = i18n.language === "fa" ? "en" : "fa";
    i18n.changeLanguage(next);
  };

  const initials = user?.display_name
    ? user.display_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() ?? "U";

  return (
    <header className="flex h-14 items-center gap-2 border-b bg-background px-4 md:gap-3 md:px-6">
      {/* Toggle button + App title */}
      <div className="flex items-center gap-2">
        <SidebarTrigger />
        <Separator orientation="vertical" className="h-6" />
        <h1 className="text-sm font-bold tracking-tight md:text-base">
          {t("app.name")}
        </h1>
      </div>

      {/* Breadcrumbs */}
      <Breadcrumbs />

      {/* User menu */}
      <div className="ms-auto flex items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              <Avatar className="h-9 w-9">
                <AvatarFallback className="text-xs">{initials}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium">{user?.display_name || user?.username}</p>
                <p className="text-xs text-muted-foreground">{user?.email || `@${user?.username}`}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={toggleLanguage}>
              <Languages className="me-2 h-4 w-4" />
              {i18n.language === "fa" ? "English" : "فارسی"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={toggleTheme}>
              {theme === "light" ? <Moon className="me-2 h-4 w-4" /> : <Sun className="me-2 h-4 w-4" />}
              {theme === "light" ? t("settings.darkMode") : t("settings.lightMode")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/settings">
                <Settings className="me-2 h-4 w-4" />
                {t("nav.settings")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout}>
              <LogOut className="me-2 h-4 w-4" />
              {t("auth.logout")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
