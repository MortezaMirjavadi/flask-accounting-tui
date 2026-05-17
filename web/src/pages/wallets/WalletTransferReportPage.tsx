import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRightLeft } from "lucide-react";
import { useWalletTransfers, useWallet } from "@/hooks/wallets";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatToman, formatJalali, formatCurrency } from "@/lib/format";

export default function WalletTransferReportPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const walletId = Number(id);

  const { data: wallet, isLoading: walletLoading } = useWallet(walletId);
  const { data, isLoading } = useWalletTransfers(walletId);
  const report = data;
  const list = report?.records ?? [];
  const totalIn = report?.summary?.total_transfer_in ?? 0;
  const totalOut = report?.summary?.total_transfer_out ?? 0;
  const net = report?.summary?.net_transfer ?? 0;

  const currency = wallet?.currency ?? "IRR";

  if (isLoading || walletLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate(`/wallets/${walletId}`)}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <ArrowRightLeft className="h-6 w-6" />
        <div>
          <h1 className="text-2xl font-bold">
            {t("sources.transferReport")}
          </h1>
          {wallet && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {wallet.name}
              </span>
              <Badge variant="secondary">{currency}</Badge>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">
              {t("sources.totalIn")}
            </p>
            <p className="text-2xl font-bold text-green-600">
              {formatCurrency(totalIn, currency)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">
              {t("sources.totalOut")}
            </p>
            <p className="text-2xl font-bold text-red-600">
              {formatCurrency(totalOut, currency)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">
              {t("common.balance")}
            </p>
            <p
              className={`text-2xl font-bold ${net >= 0 ? "text-green-600" : "text-red-600"}`}
            >
              {formatCurrency(net, currency)}
            </p>
          </CardContent>
        </Card>
      </div>

      {list.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("common.noData")}
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-start text-muted-foreground">
                <th className="pb-2 text-start">{t("common.date")}</th>
                <th className="pb-2 text-start">
                  {t("transfers.fromAccount")}
                </th>
                <th className="pb-2 text-start">
                  {t("transfers.toAccount")}
                </th>
                <th className="pb-2 text-end">{t("common.amount")}</th>
                <th className="pb-2 text-start">
                  {t("common.description")}
                </th>
              </tr>
            </thead>
            <tbody>
              {list.map((tx) => {
                const isIn = tx.to_wallet_id === walletId;
                return (
                  <tr key={tx.id} className="border-b">
                    <td className="py-2">{formatJalali(tx.date)}</td>
                    <td className="py-2">{tx.from_wallet_name}</td>
                    <td className="py-2">{tx.to_wallet_name}</td>
                    <td
                      className={`py-2 text-end font-semibold ${isIn ? "text-green-600" : "text-red-600"}`}
                    >
                      {isIn ? "+" : "-"}
                      {formatCurrency(tx.amount, currency)}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {tx.notes || tx.description || "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
