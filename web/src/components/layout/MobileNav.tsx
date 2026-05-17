import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { LayoutDashboard, ArrowLeftRight, Plus, HandCoins, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { icon: LayoutDashboard, labelKey: "nav.dashboard", url: "/dashboard" },
  { icon: ArrowLeftRight, labelKey: "nav.transactions", url: "/transactions" },
  { icon: HandCoins, labelKey: "nav.debts", url: "/debts" },
  { icon: Settings, labelKey: "nav.settings", url: "/settings" },
];

export function MobileNav() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (url: string) =>
    location.pathname === url || location.pathname.startsWith(url + "/");

  return (
    <motion.nav
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:hidden"
    >
      {navItems.slice(0, 2).map((item) => (
        <button
          key={item.url}
          onClick={() => navigate(item.url)}
          className={cn(
            "flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors",
            isActive(item.url)
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <item.icon className="h-5 w-5" />
          <span>{t(item.labelKey)}</span>
        </button>
      ))}

      {/* Center FAB */}
      <button
        onClick={() => navigate("/transactions/new")}
        className="relative -mt-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 active:scale-95"
      >
        <Plus className="h-6 w-6" />
      </button>

      {navItems.slice(2).map((item) => (
        <button
          key={item.url}
          onClick={() => navigate(item.url)}
          className={cn(
            "flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors",
            isActive(item.url)
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <item.icon className="h-5 w-5" />
          <span>{t(item.labelKey)}</span>
        </button>
      ))}
    </motion.nav>
  );
}
