import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useInstallmentPlans } from "@/hooks";
import { useWalletContext } from "@/context/wallet-context";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Eye } from "lucide-react";

export default function InstallmentPlansPage() {
  const { t } = useTranslation();
  const { activeWallet } = useWalletContext();
  const { data: plansResp, isLoading } = useInstallmentPlans(activeWallet?.id);
  const plans = plansResp?.items;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("installments.plans")}</h1>
        <Link to="/installments/new">
          <Button>
            <Plus className="me-2 h-4 w-4" />
            {t("installments.addPlan")}
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <TableHead key={i}>
                      <Skeleton className="h-4 w-20" />
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {[1, 2, 3, 4, 5].map((j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : plans && plans.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("installments.planTitle")}</TableHead>
                  <TableHead>{t("installments.totalAmount")}</TableHead>
                  <TableHead>{t("installments.installmentCount")}</TableHead>
                  <TableHead>{t("installments.installmentAmount")}</TableHead>
                  <TableHead>{t("installments.startDate")}</TableHead>
                  <TableHead>{t("common.status")}</TableHead>
                  <TableHead className="text-end">{t("common.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plans.map((plan) => (
                  <TableRow key={plan.id}>
                    <TableCell className="font-medium">{plan.title}</TableCell>
                    <TableCell>{formatToman(plan.total_amount)}</TableCell>
                    <TableCell>{plan.installment_count}</TableCell>
                    <TableCell>{formatToman(plan.installment_amount)}</TableCell>
                    <TableCell>{formatJalali(plan.start_date)}</TableCell>
                    <TableCell>
                      <StatusBadge status={plan.status} />
                    </TableCell>
                    <TableCell className="text-end">
                      <Link to={`/installments/${plan.id}`}>
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <EmptyState
              titleKey="common.noData"
              descriptionKey="installments.addPlan"
            />
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
