import { useTranslation } from "react-i18next";
import { useNavigate, useLocation } from "react-router-dom";
import { useDirection } from "@/i18n/hooks";
import {
  LayoutDashboard,
  ArrowLeftRight,
  ArrowRightLeft,
  Tags,
  Wallet,
  PiggyBank,
  BarChart3,
  CalendarClock,
  CalendarDays,
  FileCheck,
  HandCoins,
  Users,
  Bookmark,
  TagIcon,
  Settings,
  ChevronDown,
  X,
  UserCog,
  Layers,
  GitBranch,
  CreditCard,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/context/auth-context";

interface NavItem {
  titleKey: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
  items?: { titleKey: string; url: string }[];
}

const navGroups: { labelKey: string; items: NavItem[] }[] = [
  {
    labelKey: "nav.dashboard",
    items: [
      { titleKey: "nav.dashboard", url: "/dashboard", icon: LayoutDashboard },
    ],
  },
  {
    labelKey: "nav.transactions",
    items: [
      {
        titleKey: "nav.transactions",
        url: "/transactions",
        icon: ArrowLeftRight,
      },
      { titleKey: "nav.transfers", url: "/transfers", icon: ArrowRightLeft },
      { titleKey: "nav.categories", url: "/categories", icon: Tags },
      { titleKey: "nav.wallets", url: "/wallets", icon: Wallet },
      { titleKey: "nav.sources", url: "/wallets/sources", icon: CreditCard },
      { titleKey: "nav.byCategory", url: "/transactions/by-category", icon: Layers },
    ],
  },
  {
    labelKey: "nav.budget",
    items: [
      {
        titleKey: "nav.budget",
        url: "/budget",
        icon: PiggyBank,
        items: [
          { titleKey: "nav.budgetPeriods", url: "/budget/periods" },
          { titleKey: "nav.budgetReport", url: "/budget/report" },
          { titleKey: "nav.budgetTree", url: "/budget/tree" },
        ],
      },
      {
        titleKey: "nav.reports",
        url: "/reports",
        icon: BarChart3,
        items: [
          { titleKey: "nav.dailyReport", url: "/reports/daily" },
          { titleKey: "nav.weeklyReport", url: "/reports/weekly" },
          { titleKey: "nav.monthlyReport", url: "/reports/monthly" },
          { titleKey: "nav.categoryChart", url: "/reports/category-chart" },
          { titleKey: "nav.itemReports", url: "/reports/items" },
        ],
      },
      { titleKey: "nav.calendar", url: "/calendar", icon: CalendarDays },
    ],
  },
  {
    labelKey: "nav.installments",
    items: [
      {
        titleKey: "nav.installments",
        url: "/installments",
        icon: CalendarClock,
      },
      { titleKey: "nav.checks", url: "/checks", icon: FileCheck },
      { titleKey: "nav.debts", url: "/debts", icon: HandCoins },
    ],
  },
  {
    labelKey: "nav.metadata",
    items: [
      { titleKey: "nav.contacts", url: "/contacts", icon: Users },
      { titleKey: "nav.tags", url: "/tags", icon: Bookmark },
      { titleKey: "nav.labels", url: "/labels", icon: TagIcon },
    ],
  },
];

export function AppSidebar() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const direction = useDirection();
  const { isMobile, setOpenMobile } = useSidebar();

  const isActive = (url: string) =>
    location.pathname === url || location.pathname.startsWith(url + "/");
  const navigateAndClose = (url: string) => {
    navigate(url);
    if (isMobile) setOpenMobile(false);
  };

  return (
    <Sidebar side={direction === "rtl" ? "right" : "left"} collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground text-sm font-bold">
            TA
          </div>
          <span className="text-lg font-semibold text-sidebar-foreground group-data-[collapsible=icon]:hidden">
            {t("app.name")}
          </span>
          <button
            type="button"
            className="ms-auto inline-flex h-8 w-8 items-center justify-center rounded-md text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground md:hidden"
            onClick={() => setOpenMobile(false)}
            aria-label={t("common.close", { defaultValue: "Close sidebar" })}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {navGroups.map((group) => (
          <SidebarGroup key={group.labelKey}>
            <SidebarGroupLabel>{t(group.labelKey)}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <Collapsible key={item.url} className="group/collapsible" defaultOpen={isActive(item.url)}>
                    <SidebarMenuItem>
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton
                          onClick={() =>
                            !item.items && navigateAndClose(item.url)
                          }
                          isActive={isActive(item.url)}
                          tooltip={t(item.titleKey)}
                        >
                          <item.icon className="h-4 w-4" />
                          <span>{t(item.titleKey)}</span>
                          {item.items && (
                            <ChevronDown className="ms-auto h-4 w-4 transition-transform group-data-[state=open]/collapsible:rotate-180" />
                          )}
                        </SidebarMenuButton>
                      </CollapsibleTrigger>
                      {item.items && (
                        <CollapsibleContent>
                          <SidebarMenu className="ps-4">
                            {item.items.map((subItem) => (
                              <SidebarMenuItem key={subItem.url}>
                                <SidebarMenuButton
                                  onClick={() => navigateAndClose(subItem.url)}
                                  isActive={location.pathname === subItem.url}
                                  size="sm"
                                >
                                  <span>{t(subItem.titleKey)}</span>
                                </SidebarMenuButton>
                              </SidebarMenuItem>
                            ))}
                          </SidebarMenu>
                        </CollapsibleContent>
                      )}
                    </SidebarMenuItem>
                  </Collapsible>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
        {isAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel>{t("nav.admin")}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => navigateAndClose("/users")}
                    isActive={location.pathname.startsWith("/users")}
                    tooltip={t("nav.userManagement")}
                  >
                    <UserCog className="h-4 w-4" />
                    <span>{t("nav.userManagement")}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border p-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={() => navigateAndClose("/settings")}
              isActive={location.pathname === "/settings"}
              tooltip={t("nav.settings")}
            >
              <Settings className="h-4 w-4" />
              <span>{t("nav.settings")}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        {isAdmin && (
          <Badge
            variant="secondary"
            className="mt-2 group-data-[collapsible=icon]:hidden"
          >
            Admin
          </Badge>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
