import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import * as jalaali from "jalaali-js";
import {
  Plus,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  XCircle,
  List,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import {
  useCalendarInstances,
  useConfirmInstance,
  useSnoozeInstance,
  useCancelInstance,
} from "@/hooks/calendar";
import { useForecast } from "@/hooks/forecast";
import { useAlerts } from "@/hooks/alerts";
import { useWalletContext } from "@/context/wallet-context";
import type { EventInstance } from "@/types";
import { formatToman, formatJalali } from "@/lib/format";
import { getJalaliMonthName, toGregorian } from "@/lib/jalali";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

const WEEKDAY_LABELS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
const VIEW_MODES = ["daily", "weekly", "monthly", "yearly"] as const;
type ViewMode = (typeof VIEW_MODES)[number];

interface JalaliDateParts {
  jy: number;
  jm: number;
  jd: number;
}

interface CalendarDay {
  key: string;
  label: string;
  weekdayLabel: string;
  gregorianDate: string;
  jalali: JalaliDateParts;
  isCurrentMonth: boolean;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function formatGregorianDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function jalaliToGregorianDate(jy: number, jm: number, jd: number): string {
  const g = jalaali.toGregorian(jy, jm, jd);
  return `${g.gy}-${pad(g.gm)}-${pad(g.gd)}`;
}

function gregorianStringToDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function getJalaliParts(gregDate: string): JalaliDateParts {
  const [gy, gm, gd] = gregDate.split("-").map(Number);
  return jalaali.toJalaali(gy, gm, gd);
}

function makeCalendarDay(gregDate: string, currentMonth: number): CalendarDay {
  const date = gregorianStringToDate(gregDate);
  const jalali = getJalaliParts(gregDate);
  return {
    key: gregDate,
    label: String(jalali.jd),
    weekdayLabel: WEEKDAY_LABELS[(date.getDay() + 1) % 7],
    gregorianDate: gregDate,
    jalali,
    isCurrentMonth: jalali.jm === currentMonth,
  };
}

function getWeekStart(date: Date): Date {
  // Persian weeks start on Saturday. JS getDay(): Sun=0 ... Sat=6.
  return addDays(date, -((date.getDay() + 1) % 7));
}

function getPeriodRange(selectedDate: JalaliDateParts, viewMode: ViewMode) {
  const selectedGregorian = jalaliToGregorianDate(selectedDate.jy, selectedDate.jm, selectedDate.jd);

  if (viewMode === "daily") {
    return { startDate: selectedGregorian, endDate: selectedGregorian };
  }

  if (viewMode === "weekly") {
    const weekStart = getWeekStart(gregorianStringToDate(selectedGregorian));
    return {
      startDate: formatGregorianDate(weekStart),
      endDate: formatGregorianDate(addDays(weekStart, 6)),
    };
  }

  if (viewMode === "yearly") {
    const gStart = jalaali.toGregorian(selectedDate.jy, 1, 1);
    const gEnd = jalaali.toGregorian(selectedDate.jy, 12, jalaali.jalaaliMonthLength(selectedDate.jy, 12));
    return {
      startDate: `${gStart.gy}-${pad(gStart.gm)}-${pad(gStart.gd)}`,
      endDate: `${gEnd.gy}-${pad(gEnd.gm)}-${pad(gEnd.gd)}`,
    };
  }

  const gStart = jalaali.toGregorian(selectedDate.jy, selectedDate.jm, 1);
  const daysInMonth = jalaali.jalaaliMonthLength(selectedDate.jy, selectedDate.jm);
  const gEnd = jalaali.toGregorian(selectedDate.jy, selectedDate.jm, daysInMonth);
  return {
    startDate: `${gStart.gy}-${pad(gStart.gm)}-${pad(gStart.gd)}`,
    endDate: `${gEnd.gy}-${pad(gEnd.gm)}-${pad(gEnd.gd)}`,
  };
}

function getCalendarDays(selectedDate: JalaliDateParts, viewMode: ViewMode): CalendarDay[] {
  const { startDate } = getPeriodRange(selectedDate, viewMode);

  if (viewMode === "daily") {
    return [makeCalendarDay(startDate, selectedDate.jm)];
  }

  if (viewMode === "weekly") {
    const start = gregorianStringToDate(startDate);
    return Array.from({ length: 7 }, (_, index) => {
      const gregDate = formatGregorianDate(addDays(start, index));
      return makeCalendarDay(gregDate, selectedDate.jm);
    });
  }

  const daysInMonth = jalaali.jalaaliMonthLength(selectedDate.jy, selectedDate.jm);
  const firstGregorian = jalaali.toGregorian(selectedDate.jy, selectedDate.jm, 1);
  const firstDate = new Date(firstGregorian.gy, firstGregorian.gm - 1, firstGregorian.gd);
  const startCol = (firstDate.getDay() + 1) % 7;
  const gridStart = addDays(firstDate, -startCol);
  const cellCount = Math.ceil((startCol + daysInMonth) / 7) * 7;

  return Array.from({ length: cellCount }, (_, index) => {
    const gregDate = formatGregorianDate(addDays(gridStart, index));
    return makeCalendarDay(gregDate, selectedDate.jm);
  });
}

function getPeriodTitle(selectedDate: JalaliDateParts, viewMode: ViewMode, startDate: string, endDate: string): string {
  if (viewMode === "yearly") {
    return `${selectedDate.jy}`;
  }

  if (viewMode === "monthly") {
    return `${getJalaliMonthName(selectedDate.jm)} ${selectedDate.jy}`;
  }

  if (viewMode === "daily") {
    const day = getJalaliParts(startDate);
    return `${day.jd} ${getJalaliMonthName(day.jm)} ${day.jy}`;
  }

  const start = getJalaliParts(startDate);
  const end = getJalaliParts(endDate);
  return `${start.jd} ${getJalaliMonthName(start.jm)} - ${end.jd} ${getJalaliMonthName(end.jm)} ${end.jy}`;
}

function shiftSelectedDate(selectedDate: JalaliDateParts, viewMode: ViewMode, direction: -1 | 1): JalaliDateParts {
  if (viewMode === "yearly") {
    return { ...selectedDate, jy: selectedDate.jy + direction, jm: 1, jd: 1 };
  }

  if (viewMode === "monthly") {
    const month = selectedDate.jm + direction;
    if (month < 1) return { jy: selectedDate.jy - 1, jm: 12, jd: 1 };
    if (month > 12) return { jy: selectedDate.jy + 1, jm: 1, jd: 1 };
    return { ...selectedDate, jm: month, jd: 1 };
  }

  const gregorian = gregorianStringToDate(jalaliToGregorianDate(selectedDate.jy, selectedDate.jm, selectedDate.jd));
  const shifted = addDays(gregorian, direction * (viewMode === "weekly" ? 7 : 1));
  const next = jalaali.toJalaali(shifted.getFullYear(), shifted.getMonth() + 1, shifted.getDate());
  return { jy: next.jy, jm: next.jm, jd: next.jd };
}

function gregorianToJalaliDay(gregDate: string): string {
  if (!gregDate) return "";
  const parts = gregDate.split("-");
  if (parts.length !== 3) return "";
  const j = jalaali.toJalaali(Number(parts[0]), Number(parts[1]), Number(parts[2]));
  return `${j.jy}/${pad(j.jm)}/${pad(j.jd)}`;
}

interface InstanceActionsProps {
  instance: EventInstance;
  onClose: () => void;
}

function InstanceActions({ instance, onClose }: InstanceActionsProps) {
  const { t } = useTranslation();
  const confirmMutation = useConfirmInstance();
  const snoozeMutation = useSnoozeInstance();
  const cancelMutation = useCancelInstance();
  const [snoozeDate, setSnoozeDate] = useState("");

  const isPending = instance.status === "pending" || instance.status === "snoozed";

  async function handleConfirm() {
    try {
      await confirmMutation.mutateAsync(instance.id);
      toast.success(t("common.success"));
      onClose();
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleSnooze() {
    if (!snoozeDate) return;
    try {
      const gregDate = toGregorian(snoozeDate);
      await snoozeMutation.mutateAsync({ instanceId: instance.id, newDueDate: gregDate });
      toast.success(t("common.success"));
      onClose();
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleCancel() {
    try {
      await cancelMutation.mutateAsync(instance.id);
      toast.success(t("common.success"));
      onClose();
    } catch {
      toast.error(t("common.error"));
    }
  }

  const loading = confirmMutation.isPending || snoozeMutation.isPending || cancelMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <p className="font-medium">{instance.title}</p>
        <p className="text-sm text-muted-foreground">{instance.category_name}</p>
        <p className={`text-lg font-bold ${instance.category_type === "income" ? "text-green-600" : "text-red-600"}`}>
          {formatToman(instance.amount)}
        </p>
        {instance.status === "snoozed" && instance.snoozed_from && (
          <p className="text-xs text-muted-foreground">
            {t("calendar.snooze")} {gregorianToJalaliDay(instance.snoozed_from)}
          </p>
        )}
      </div>

      <Separator />

      <Button variant="outline" className="w-full" asChild>
        <Link to={`/calendar/${instance.event_id}`}>{t("common.details")}</Link>
      </Button>

      {isPending && (
        <div className="space-y-3">
          <Button className="w-full" onClick={handleConfirm} disabled={loading}>
            <CheckCircle2 className="me-2 h-4 w-4" />
            {t("calendar.confirm")}
          </Button>

          <div className="flex gap-2">
            <div className="flex-1">
              <JalaliDatePicker value={snoozeDate} onChange={setSnoozeDate} placeholder={t("calendar.snooze")} />
            </div>
            <Button variant="outline" onClick={handleSnooze} disabled={loading || !snoozeDate}>
              {t("calendar.snooze")}
            </Button>
          </div>

          <Button variant="destructive" className="w-full" onClick={handleCancel} disabled={loading}>
            <XCircle className="me-2 h-4 w-4" />
            {t("calendar.cancelInstance")}
          </Button>
        </div>
      )}

      {instance.status === "confirmed" && (
        <p className="flex items-center gap-2 text-sm text-green-600">
          <CheckCircle2 className="h-4 w-4" />
          {t("calendar.confirm")}
        </p>
      )}

      {instance.status === "cancelled" && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <XCircle className="h-4 w-4" />
          {t("calendar.cancelInstance")}
        </p>
      )}
    </div>
  );
}

export default function CalendarPage() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const today = new Date();
  const todayJalali = jalaali.toJalaali(today.getFullYear(), today.getMonth() + 1, today.getDate());

  const [viewMode, setViewMode] = useState<ViewMode>("monthly");
  const [selectedDate, setSelectedDate] = useState<JalaliDateParts>(todayJalali);
  const [showPeriodList, setShowPeriodList] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<EventInstance | null>(null);

  const { activeWallet } = useWalletContext();

  const { startDate, endDate } = useMemo(
    () => getPeriodRange(selectedDate, viewMode),
    [selectedDate, viewMode]
  );

  const { data: instances, isLoading } = useCalendarInstances(startDate, endDate, activeWallet?.id);
  const { data: forecast } = useForecast();
  const { data: alerts } = useAlerts();

  const instancesByDate = useMemo(() => {
    const map = new Map<string, EventInstance[]>();
    if (!instances) return map;
    for (const inst of instances) {
      if (!map.has(inst.due_date)) map.set(inst.due_date, []);
      map.get(inst.due_date)!.push(inst);
    }
    return map;
  }, [instances]);

  const calendarDays = useMemo(
    () => getCalendarDays(selectedDate, viewMode),
    [selectedDate, viewMode]
  );

  const periodTitle = useMemo(
    () => getPeriodTitle(selectedDate, viewMode, startDate, endDate),
    [selectedDate, viewMode, startDate, endDate]
  );

  const periodInstances = useMemo(
    () => [...(instances || [])].sort((a, b) => a.due_date.localeCompare(b.due_date)),
    [instances]
  );

  function goToToday() {
    setSelectedDate(todayJalali);
  }

  const isToday = (day: CalendarDay) =>
    day.jalali.jd === todayJalali.jd &&
    day.jalali.jm === todayJalali.jm &&
    day.jalali.jy === todayJalali.jy;

  const actionsContent = selectedInstance && (
    <InstanceActions instance={selectedInstance} onClose={() => setSelectedInstance(null)} />
  );

  const gridColumnsClass = viewMode === "daily" ? "grid-cols-1" : "grid-cols-7";

  function renderMiniMonth(month: number) {
    const daysInMonth = jalaali.jalaaliMonthLength(selectedDate.jy, month);
    const firstGregorian = jalaali.toGregorian(selectedDate.jy, month, 1);
    const firstDate = new Date(firstGregorian.gy, firstGregorian.gm - 1, firstGregorian.gd);
    const startCol = (firstDate.getDay() + 1) % 7;
    const cellCount = Math.ceil((startCol + daysInMonth) / 7) * 7;
    const days = Array.from({ length: cellCount }, (_, index) => {
      const d = addDays(firstDate, index - startCol);
      const gregDate = formatGregorianDate(d);
      const jp = jalaali.toJalaali(d.getFullYear(), d.getMonth() + 1, d.getDate());
      const hasEvents = (instancesByDate.get(gregDate) || []).length > 0;
      return { day: jp.jd, inMonth: jp.jm === month, hasEvents, gregDate };
    });
    return (
      <button
        type="button"
        className="rounded-md border p-2 text-start transition-colors hover:bg-muted/50"
        onClick={() => {
          setSelectedDate({ jy: selectedDate.jy, jm: month, jd: 1 });
          setViewMode("monthly");
        }}
      >
        <p className="mb-1 text-xs font-semibold">{getJalaliMonthName(month)}</p>
        <div className="grid grid-cols-7 gap-0.5">
          {WEEKDAY_LABELS.map((l) => (
            <div key={l} className="text-center text-[8px] text-muted-foreground">{l}</div>
          ))}
          {days.map((d, i) => (
            <div
              key={i}
              className={`flex h-4 items-center justify-center text-[8px] ${d.inMonth ? "" : "text-muted-foreground/30"}`}
            >
              {d.day > 0 ? d.day : ""}
              {d.hasEvents && d.inMonth && <span className="absolute mt-2.5 h-1 w-1 rounded-full bg-primary" />}
            </div>
          ))}
        </div>
      </button>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="flex h-full min-h-0 flex-col gap-4"
    >
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("calendar.title")}</h1>
        <Button asChild>
          <Link to="/calendar/new">
            <Plus className="h-4 w-4" />
            {t("nav.addEvent")}
          </Link>
        </Button>
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-md border bg-muted/40 p-1">
          {VIEW_MODES.map((mode) => (
            <Button
              key={mode}
              type="button"
              variant={viewMode === mode ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode(mode)}
            >
              {t(`calendar.${mode}View`)}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => setSelectedDate((date) => shiftSelectedDate(date, viewMode, -1))}>
            <ChevronRight className="h-5 w-5" />
          </Button>
          <span className="min-w-44 text-center text-lg font-semibold">{periodTitle}</span>
          <Button variant="ghost" size="icon" onClick={() => setSelectedDate((date) => shiftSelectedDate(date, viewMode, 1))}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={goToToday}>
            {t("calendar.today")}
          </Button>
          <Button variant={showPeriodList ? "default" : "outline"} size="sm" onClick={() => setShowPeriodList((show) => !show)}>
            <List className="h-4 w-4" />
            {showPeriodList ? t("calendar.hideList") : t("calendar.showList")}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className={`grid min-h-0 flex-1 ${viewMode === "yearly" ? "grid-cols-3" : gridColumnsClass} gap-1`}>
          {Array.from({ length: viewMode === "yearly" ? 12 : viewMode === "daily" ? 1 : viewMode === "weekly" ? 7 : 35 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : viewMode === "yearly" ? (
        <div className="min-h-0 flex-1 overflow-auto">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
              <div key={month}>{renderMiniMonth(month)}</div>
            ))}
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto">
          {viewMode !== "daily" && (
            <div className="mb-1 grid grid-cols-7 gap-1">
              {WEEKDAY_LABELS.map((label) => (
                <div key={label} className="py-1 text-center text-xs font-medium text-muted-foreground">
                  {label}
                </div>
              ))}
            </div>
          )}

          <div className={`grid ${gridColumnsClass} gap-1`}>
            {calendarDays.map((day) => {
              const dayInstances = instancesByDate.get(day.gregorianDate) || [];
              const todayCell = isToday(day);
              const mutedMonth = viewMode === "monthly" && !day.isCurrentMonth;

              return (
                <div
                  key={day.key}
                  className={`min-h-[5rem] rounded-md border p-2 text-xs transition-colors ${
                    todayCell ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"
                  } ${mutedMonth ? "opacity-40" : ""} ${viewMode === "daily" ? "min-h-[18rem]" : ""}`}
                >
                  <div className={`mb-2 flex items-center justify-between font-medium ${todayCell ? "text-primary" : "text-foreground"}`}>
                    {viewMode === "daily" ? (
                      <span>{day.weekdayLabel}، {formatJalali(day.gregorianDate)}</span>
                    ) : (
                      <>
                        <span>{day.weekdayLabel}</span>
                        <span>{day.label}</span>
                      </>
                    )}
                  </div>
                  <div className="space-y-1">
                    {dayInstances.map((inst) => (
                      <button
                        key={inst.id}
                        type="button"
                        className={`flex w-full items-center gap-1 rounded px-2 py-1 text-start text-[11px] leading-tight transition-colors ${
                          inst.status === "confirmed"
                            ? "bg-green-100 text-green-700 line-through dark:bg-green-900/30 dark:text-green-400"
                            : inst.status === "cancelled"
                              ? "bg-muted text-muted-foreground line-through"
                              : inst.category_type === "income"
                                ? "bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400"
                        }`}
                        onClick={() => setSelectedInstance(inst)}
                      >
                        <span className="truncate">{inst.title}</span>
                        <span className="ms-auto shrink-0 font-semibold tabular-nums">
                          {formatToman(inst.amount)}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {showPeriodList && (
        <div className="shrink-0 space-y-3 rounded-lg border bg-card p-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t("calendar.periodEvents")}</h2>
            <span className="text-sm text-muted-foreground">{periodInstances.length}</span>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : periodInstances.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">{t("calendar.noPeriodEvents")}</p>
          ) : (
            <div className="max-h-72 space-y-2 overflow-y-auto">
              {periodInstances.map((inst) => (
                <button
                  key={inst.id}
                  type="button"
                  className="flex w-full items-center justify-between rounded-md border p-3 text-start transition-colors hover:bg-muted/50"
                  onClick={() => setSelectedInstance(inst)}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{inst.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatJalali(inst.due_date)} · {inst.category_name}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`font-semibold ${inst.category_type === "income" ? "text-green-600" : "text-red-600"}`}>
                      {formatToman(inst.amount)}
                    </span>
                    <div
                      className={`h-2 w-2 rounded-full ${
                        inst.status === "confirmed" ? "bg-green-500" : inst.status === "cancelled" ? "bg-red-500" : "bg-yellow-500"
                      }`}
                    />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Forecast & Alerts Panels */}
      {(forecast || alerts) && viewMode !== "yearly" && (
        <div className="shrink-0 grid gap-3 sm:grid-cols-2">
          {forecast && forecast.expected_income != null && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <TrendingUp className="h-4 w-4" />
                  {t("calendar.forecast")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t("calendar.expectedIncome")}</span>
                  <span className="font-semibold text-green-600">{formatToman(forecast.expected_income)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t("calendar.expectedExpenses")}</span>
                  <span className="font-semibold text-red-600">{formatToman(forecast.expected_expenses)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t("calendar.forecastBalance")}</span>
                  <span className={`font-bold ${(forecast.forecast_balance ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {formatToman(forecast.forecast_balance ?? 0)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
          {alerts && alerts.alerts.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  {t("calendar.alerts")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {alerts.alerts.slice(0, 5).map((alert, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <Badge variant={alert.severity === "high" ? "destructive" : alert.severity === "medium" ? "outline" : "secondary"} className="mt-0.5 shrink-0">
                        {alert.severity}
                      </Badge>
                      <span className="text-muted-foreground">{alert.message}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {isMobile ? (
        <Sheet open={!!selectedInstance} onOpenChange={(open) => !open && setSelectedInstance(null)}>
          <SheetContent side="bottom" className="max-h-[70vh] overflow-y-auto px-4 pb-8">
            <SheetHeader className="text-start">
              <SheetTitle>{selectedInstance?.title}</SheetTitle>
            </SheetHeader>
            <div className="mt-4">{actionsContent}</div>
          </SheetContent>
        </Sheet>
      ) : (
        selectedInstance && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSelectedInstance(null)}>
            <Card className="max-h-[80vh] w-[380px] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardContent className="pt-6">{actionsContent}</CardContent>
            </Card>
          </div>
        )
      )}
    </motion.div>
  );
}
