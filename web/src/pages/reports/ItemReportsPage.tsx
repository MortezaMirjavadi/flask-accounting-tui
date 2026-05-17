import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { BarChart3, TrendingUp, TrendingDown, Minus, Store, AlertTriangle, ShoppingCart, Flame } from "lucide-react";
import { useTopItems, useItemVelocity, usePersonalInflation, usePriceSpikes, usePriceComparison, useMonthlyBasket, useBestStores } from "@/hooks/reports";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatToman } from "@/lib/format";
import type { BestStoreItem, InflationReport, InflationSpike, MonthlyBasketItem, SourcePrice, TopItem, VelocityItem } from "@/types";

const TABS = [
  "topItems",
  "velocity",
  "inflation",
  "priceComparison",
  "spikes",
  "monthlyBasket",
  "bestStores",
] as const;

type Tab = (typeof TABS)[number];

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "increasing") return <TrendingUp className="h-4 w-4 text-red-500" />;
  if (trend === "decreasing") return <TrendingDown className="h-4 w-4 text-green-500" />;
  return <Minus className="h-4 w-4 text-muted-foreground" />;
}

function TopItemsTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = useTopItems(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-start text-muted-foreground">
            <th className="pb-2 text-start">#</th>
            <th className="pb-2 text-start">{t("common.name")}</th>
            <th className="pb-2 text-end">{t("common.total")}</th>
            <th className="pb-2 text-end">{t("reports.velocity")}</th>
            <th className="pb-2 text-end">{t("common.amount")}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item: TopItem, i: number) => (
            <tr key={item.name} className="border-b">
              <td className="py-2 text-muted-foreground">{i + 1}</td>
              <td className="py-2 font-medium">{item.name}</td>
              <td className="py-2 text-end font-semibold">{formatToman(item.total_spent)}</td>
              <td className="py-2 text-end text-muted-foreground">{item.purchase_count}</td>
              <td className="py-2 text-end text-muted-foreground">{formatToman(item.avg_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function VelocityTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = useItemVelocity(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-start text-muted-foreground">
            <th className="pb-2 text-start">{t("common.name")}</th>
            <th className="pb-2 text-end">{t("dashboard.monthlyExpense")}</th>
            <th className="pb-2 text-end">{t("transactions.quantity")}</th>
            <th className="pb-2 text-center">{t("common.status")}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item: VelocityItem) => (
            <tr key={item.name} className="border-b">
              <td className="py-2 font-medium">{item.name}</td>
              <td className="py-2 text-end">{formatToman(item.avg_monthly_spend)}</td>
              <td className="py-2 text-end">{item.avg_monthly_quantity?.toFixed(1)}</td>
              <td className="py-2 text-center"><TrendIcon trend={item.trend} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InflationTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = usePersonalInflation(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  const report: InflationReport = data;
  return (
    <div className="space-y-4">
      {report.overall_inflation_pct != null && (
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Flame className="h-5 w-5 text-orange-500" />
            <div>
              <p className="text-sm text-muted-foreground">{t("reports.inflation")}</p>
              <p className="text-2xl font-bold">{report.overall_inflation_pct?.toFixed(1)}%</p>
            </div>
          </CardContent>
        </Card>
      )}
      {report.items && report.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-start text-muted-foreground">
                <th className="pb-2 text-start">{t("common.name")}</th>
                <th className="pb-2 text-end">اولین قیمت</th>
                <th className="pb-2 text-end">آخرین قیمت</th>
                <th className="pb-2 text-end">تغییر %</th>
                <th className="pb-2 text-end">ماه‌ها</th>
              </tr>
            </thead>
            <tbody>
              {report.items.map((item: InflationReport["items"][number]) => (
                <tr key={item.name} className="border-b">
                  <td className="py-2 font-medium">{item.name}</td>
                  <td className="py-2 text-end">{formatToman(item.first_price)}</td>
                  <td className="py-2 text-end">{formatToman(item.last_price)}</td>
                  <td className={`py-2 text-end font-semibold ${item.change_pct > 0 ? "text-red-600" : item.change_pct < 0 ? "text-green-600" : ""}`}>
                    {item.change_pct > 0 ? "+" : ""}{item.change_pct?.toFixed(1)}%
                  </td>
                  <td className="py-2 text-end text-muted-foreground">{item.months_tracked}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PriceComparisonTab({ walletFilter: _walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = usePriceComparison();
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  const grouped: Record<string, SourcePrice[]> = {};
  for (const item of data) {
    if (!grouped[item.name]) grouped[item.name] = [];
    grouped[item.name].push(item);
  }
  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([name, stores]) => (
        <Card key={name}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <ShoppingCart className="h-4 w-4" /> {name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {stores.sort((a: SourcePrice, b: SourcePrice) => a.avg_price - b.avg_price).map((s: SourcePrice, i: number) => (
                <div key={s.source_name} className="flex items-center justify-between text-sm">
                  <span className={i === 0 ? "font-semibold text-green-600" : ""}>
                    {s.source_name}
                    {i === 0 && " ★"}
                  </span>
                  <span className="text-muted-foreground">
                    {formatToman(s.avg_price)} ({s.purchase_count}x)
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SpikesTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = usePriceSpikes(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  return (
    <div className="space-y-2">
      {data.map((item: InflationSpike) => (
        <Card key={item.name} className="border-orange-200">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              <div>
                <p className="font-medium">{item.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatToman(item.first_price)} → {formatToman(item.last_price)}
                </p>
              </div>
            </div>
            <Badge variant="destructive">+{item.change_pct?.toFixed(1)}%</Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function MonthlyBasketTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = useMonthlyBasket(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  return (
    <div className="space-y-4">
      {data.map((month: MonthlyBasketItem) => (
        <Card key={`${month.year}-${month.month}`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{month.year}/{month.month}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {month.items?.map((item: MonthlyBasketItem["items"][number]) => (
                <div key={item.name} className="flex justify-between text-sm">
                  <span>{item.name} × {item.quantity}</span>
                  <span className="text-muted-foreground">{formatToman(item.total)}</span>
                </div>
              ))}
              <div className="flex justify-between border-t pt-1 font-semibold">
                <span>{t("common.total")}</span>
                <span>{formatToman(month.total)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function BestStoresTab({ walletFilter }: { walletFilter?: Record<string, string> }) {
  const { t } = useTranslation();
  const { data, isLoading } = useBestStores(walletFilter);
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.length === 0) return <p className="py-8 text-center text-muted-foreground">{t("common.noData")}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-start text-muted-foreground">
            <th className="pb-2 text-start">{t("common.name")}</th>
            <th className="pb-2 text-start">{t("sources.title")}</th>
            <th className="pb-2 text-end">{t("common.amount")}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item: BestStoreItem) => (
            <tr key={item.name} className="border-b">
              <td className="py-2 font-medium">{item.name}</td>
              <td className="py-2">
                <span className="flex items-center gap-1 text-green-600">
                  <Store className="h-3 w-3" /> {item.best_source}
                </span>
              </td>
              <td className="py-2 text-end">{formatToman(item.avg_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TAB_COMPONENTS: Record<Tab, React.ComponentType<{ walletFilter?: Record<string, string> }>> = {
  topItems: TopItemsTab,
  velocity: VelocityTab,
  inflation: InflationTab,
  priceComparison: PriceComparisonTab,
  spikes: SpikesTab,
  monthlyBasket: MonthlyBasketTab,
  bestStores: BestStoresTab,
};

export default function ItemReportsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>("topItems");
  const walletFilter = useActiveWalletFilter();
  const TabComponent = TAB_COMPONENTS[activeTab];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <BarChart3 className="h-6 w-6" />
        <h1 className="text-2xl font-bold">{t("reports.title")}</h1>
      </div>

      <div className="flex flex-wrap gap-1 rounded-md border bg-muted/40 p-1">
        {TABS.map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab(tab)}
          >
            {t(`reports.${tab}`)}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="p-4">
          <TabComponent walletFilter={walletFilter} />
        </CardContent>
      </Card>
    </motion.div>
  );
}
