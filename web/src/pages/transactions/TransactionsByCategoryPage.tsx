import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Layers, ChevronDown, ChevronRight } from "lucide-react";
import { useReportByCategory } from "@/hooks/reports";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatToman } from "@/lib/format";

interface CategoryGroup {
  category_name: string;
  category_type: string;
  total: number;
  expanded: boolean;
}

export default function TransactionsByCategoryPage() {
  const { t } = useTranslation();
  const { data: categories, isLoading } = useReportByCategory();

  const groups = useMemo((): CategoryGroup[] => {
    if (!categories) return [];
    return categories.map((c) => ({
      category_name: c.category_name,
      category_type: c.category_type,
      total: c.total,
      expanded: false,
    }));
  }, [categories]);

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  const totalIncome = groups.filter((g) => g.category_type === "income").reduce((s, g) => s + g.total, 0);
  const totalCost = groups.filter((g) => g.category_type === "cost").reduce((s, g) => s + g.total, 0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <Layers className="h-6 w-6" />
        <h1 className="text-2xl font-bold">{t("transactions.byCategoryTitle")}</h1>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">{t("common.income")}</p>
            <p className="text-2xl font-bold text-green-600">{formatToman(totalIncome)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">{t("common.cost")}</p>
            <p className="text-2xl font-bold text-red-600">{formatToman(totalCost)}</p>
          </CardContent>
        </Card>
      </div>

      {groups.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("common.noData")}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {groups.map((group) => {
            const isExpanded = expanded[group.category_name] ?? false;
            const isIncome = group.category_type === "income";
            return (
              <Card key={group.category_name}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between p-4 text-start transition-colors hover:bg-muted/50"
                  onClick={() => toggleExpand(group.category_name)}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="font-medium">{group.category_name}</span>
                    <Badge variant={isIncome ? "default" : "destructive"}>
                      {isIncome ? t("common.income") : t("common.cost")}
                    </Badge>
                  </div>
                  <span className={`font-semibold ${isIncome ? "text-green-600" : "text-red-600"}`}>
                    {formatToman(group.total)}
                  </span>
                </button>
                {isExpanded && (
                  <div className="border-t px-4 pb-4 pt-2">
                    <p className="text-sm text-muted-foreground">
                      {t("common.total")}: {formatToman(group.total)}
                    </p>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
