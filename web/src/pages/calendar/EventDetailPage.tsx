import { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { ArrowLeft, Pencil, Trash2, Pause, Play, XCircle } from "lucide-react";
import {
  useCalendarEvent,
  useDeleteEvent,
  usePauseEvent,
  useResumeEvent,
  useCancelEvent,
} from "@/hooks/calendar";
import { useCategories } from "@/hooks/categories";
import { useSources } from "@/hooks/sources";
import { formatToman, formatJalali } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";

export default function EventDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const eventId = Number(id);

  const { data: event, isLoading } = useCalendarEvent(eventId);
  const { data: categoriesResp } = useCategories();
  const categories = categoriesResp?.items;
  const { data: sourcesResp } = useSources();
  const sources = sourcesResp?.items;
  const deleteMutation = useDeleteEvent();
  const pauseMutation = usePauseEvent();
  const resumeMutation = useResumeEvent();
  const cancelMutation = useCancelEvent();

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  const category = categories?.find((c) => c.id === event?.category_id);
  const sourceName = sources?.find((s) => s.id === event?.source_id)?.name;

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync(eventId);
      toast.success(t("common.success"));
      navigate("/calendar");
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleCancel() {
    try {
      await cancelMutation.mutateAsync(eventId);
      toast.success(t("common.success"));
      setCancelOpen(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handlePause() {
    try {
      await pauseMutation.mutateAsync(eventId);
      toast.success(t("common.success"));
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleResume() {
    try {
      await resumeMutation.mutateAsync(eventId);
      toast.success(t("common.success"));
    } catch {
      toast.error(t("common.error"));
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-muted-foreground">{t("common.noData")}</p>
        <Button variant="link" asChild className="mt-2">
          <Link to="/calendar">{t("common.back")}</Link>
        </Button>
      </div>
    );
  }

  const statusColor =
    event.status === "active"
      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
      : event.status === "paused"
        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";

  const statusLabel =
    event.status === "active"
      ? t("common.active")
      : event.status === "paused"
        ? t("calendar.pause")
        : t("calendar.cancelInstance");

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/calendar">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">{event.title}</h1>
        </div>
        <Button variant="outline" asChild>
          <Link to={`/calendar/${eventId}/edit`}>
            <Pencil className="me-2 h-4 w-4" />
            {t("common.edit")}
          </Link>
        </Button>
      </div>

      {/* Event Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{event.title}</CardTitle>
            <Badge className={statusColor}>{statusLabel}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("common.amount")}
              </p>
              <p className="text-2xl font-bold">{formatToman(event.amount)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("transactions.category")}
              </p>
              <p className="font-medium">
                {category?.name || "-"}{" "}
                {category?.type === "income"
                  ? `(${t("common.income")})`
                  : `(${t("common.cost")})`}
              </p>
            </div>
          </div>

          <Separator />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("transactions.source")}
              </p>
              <p className="font-medium">{sourceName || "-"}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("calendar.frequency")}
              </p>
              <p className="font-medium">
                {t(`calendar.${event.frequency}`)}
                {event.frequency !== "once" && event.repeat_interval > 1 && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({t("calendar.repeatInterval")} {event.repeat_interval})
                  </span>
                )}
              </p>
            </div>
          </div>

          <Separator />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("calendar.startDate")}
              </p>
              <p className="font-medium">{formatJalali(event.start_date)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("calendar.endDate")}
              </p>
              <p className="font-medium">
                {event.end_date ? formatJalali(event.end_date) : "-"}
              </p>
            </div>
          </div>

          {event.occurrence_limit && (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  {t("calendar.occurrenceLimit")}
                </p>
                <p className="font-medium">{event.occurrence_limit}</p>
              </div>
            </>
          )}

          {event.description && (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  {t("common.description")}
                </p>
                <p>{event.description}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      {event.status !== "cancelled" && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-3">
              {event.status === "active" && (
                <Button variant="outline" onClick={handlePause} disabled={pauseMutation.isPending}>
                  <Pause className="me-2 h-4 w-4" />
                  {t("calendar.pause")}
                </Button>
              )}
              {event.status === "paused" && (
                <Button variant="outline" onClick={handleResume} disabled={resumeMutation.isPending}>
                  <Play className="me-2 h-4 w-4" />
                  {t("calendar.resume")}
                </Button>
              )}
              <Button
                variant="destructive"
                onClick={() => setCancelOpen(true)}
              >
                <XCircle className="me-2 h-4 w-4" />
                {t("calendar.cancelInstance")}
              </Button>
              <Button
                variant="destructive"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="me-2 h-4 w-4" />
                {t("common.delete")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirm Dialogs */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        confirmLabel={t("common.delete")}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
      />

      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        confirmLabel={t("calendar.cancelInstance")}
        onConfirm={handleCancel}
        loading={cancelMutation.isPending}
      />
    </motion.div>
  );
}
