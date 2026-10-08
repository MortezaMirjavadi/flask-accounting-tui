import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import * as jalaali from "jalaali-js";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { getJalaliMonthName, toJalali } from "@/lib/jalali";
import { toPersianDigits } from "@/lib/format";
import i18n from "@/i18n";

interface JalaliDatePickerProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  allowClear?: boolean;
}

type JalaliParts = { year: number; month: number; day: number };

const weekDays = ["ش", "ی", "د", "س", "چ", "پ", "ج"];

// Transliterated Jalali month names for non-fa locales.
const jalaliMonthsEn = [
  "Farvardin", "Ordibehesht", "Khordad",
  "Tir", "Mordad", "Shahrivar",
  "Mehr", "Aban", "Azar",
  "Dey", "Bahman", "Esfand",
];

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function todayJalali(): JalaliParts {
  const today = new Date();
  const j = jalaali.toJalaali(today.getFullYear(), today.getMonth() + 1, today.getDate());
  return { year: j.jy, month: j.jm, day: j.jd };
}

function parseGregorian(value?: string): JalaliParts | null {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  const j = jalaali.toJalaali(year, month, day);
  return { year: j.jy, month: j.jm, day: j.jd };
}

function toGregorianValue(date: JalaliParts) {
  const g = jalaali.toGregorian(date.year, date.month, date.day);
  return `${g.gy}-${pad(g.gm)}-${pad(g.gd)}`;
}

function sameDay(a: JalaliParts | null, b: JalaliParts | null) {
  return !!a && !!b && a.year === b.year && a.month === b.month && a.day === b.day;
}

function firstDayOffset(year: number, month: number) {
  const g = jalaali.toGregorian(year, month, 1);
  const day = new Date(g.gy, g.gm - 1, g.gd).getDay();
  return (day + 1) % 7; // Saturday-first calendar.
}

export function JalaliDatePicker({
  value,
  onChange,
  placeholder = "انتخاب تاریخ",
  disabled,
  className,
  allowClear = true,
}: JalaliDatePickerProps) {
  const { t } = useTranslation();
  const selected = useMemo(() => parseGregorian(value), [value]);
  const today = useMemo(() => todayJalali(), []);
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<JalaliParts>(selected ?? today);

  useEffect(() => {
    if (selected) setView(selected);
  }, [selected?.year, selected?.month, selected?.day]);

  const daysInMonth = jalaali.jalaaliMonthLength(view.year, view.month);
  const blanks = firstDayOffset(view.year, view.month);
  const rawDisplay = value ? toJalali(value) : "";
  const displayValue = i18n.language === "fa" ? toPersianDigits(rawDisplay) : rawDisplay;

  const isFa = i18n.language === "fa";
  const monthName = (month: number) =>
    isFa ? getJalaliMonthName(month) : jalaliMonthsEn[month - 1];
  const yearLabel = (year: number) =>
    isFa ? toPersianDigits(String(year)) : String(year);

  // 30 years back / 5 forward around today, always including the viewed year.
  const yearOptions = useMemo(() => {
    const min = Math.min(today.year - 30, view.year);
    const max = Math.max(today.year + 5, view.year);
    const years: number[] = [];
    for (let y = max; y >= min; y--) years.push(y);
    return years;
  }, [today.year, view.year]);

  const moveMonth = (amount: number) => {
    setView((current) => {
      let month = current.month + amount;
      let year = current.year;
      if (month < 1) {
        month = 12;
        year -= 1;
      }
      if (month > 12) {
        month = 1;
        year += 1;
      }
      return { year, month, day: 1 };
    });
  };

  const selectMonth = (month: number) => {
    setView((current) => ({ ...current, month, day: 1 }));
  };

  const selectYear = (year: number) => {
    setView((current) => ({ ...current, year, day: 1 }));
  };

  const selectDay = (day: number) => {
    onChange(toGregorianValue({ year: view.year, month: view.month, day }));
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn(
            "h-9 w-full justify-between bg-transparent px-3 text-start font-normal",
            !value && "text-muted-foreground",
            className,
          )}
        >
          <span>{displayValue || placeholder}</span>
          <CalendarDays className="h-4 w-4 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-72 p-3" align="start" dir="rtl">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <Button type="button" variant="ghost" size="icon" onClick={() => moveMonth(-1)}>
              <ChevronRight className="h-4 w-4" />
            </Button>
            <div className="flex flex-1 items-center justify-center gap-1">
              <Select
                value={String(view.month)}
                onValueChange={(v) => selectMonth(Number(v))}
              >
                <SelectTrigger className="h-8 w-auto gap-1 border-0 bg-transparent px-2 text-sm font-semibold shadow-none focus:ring-0">
                  {monthName(view.month)}
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                    <SelectItem key={month} value={String(month)}>
                      {monthName(month)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={String(view.year)}
                onValueChange={(v) => selectYear(Number(v))}
              >
                <SelectTrigger className="h-8 w-auto gap-1 border-0 bg-transparent px-2 text-sm font-semibold shadow-none focus:ring-0">
                  {yearLabel(view.year)}
                </SelectTrigger>
                <SelectContent>
                  {yearOptions.map((year) => (
                    <SelectItem key={year} value={String(year)}>
                      {yearLabel(year)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="ghost" size="icon" onClick={() => moveMonth(1)}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-7 text-center text-xs text-muted-foreground">
            {weekDays.map((day) => (
              <div key={day} className="py-1 font-medium">{day}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-0">
            {Array.from({ length: blanks }).map((_, index) => (
              <div key={`blank-${index}`} className="h-9" />
            ))}
            {Array.from({ length: daysInMonth }, (_, index) => index + 1).map((day) => {
              const date = { year: view.year, month: view.month, day };
              const isSelected = sameDay(selected, date);
              const isToday = sameDay(today, date);

              return (
                <button
                  key={day}
                  type="button"
                  className={cn(
                    "flex h-9 w-full items-center justify-center rounded-none border border-transparent p-0 text-sm transition-colors hover:bg-accent",
                    isSelected && "bg-primary text-primary-foreground hover:bg-primary",
                    isToday && !isSelected && "border-primary/50",
                  )}
                  onClick={() => selectDay(day)}
                >
                  {isFa ? toPersianDigits(String(day)) : day}
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between border-t pt-3">
            <Button type="button" variant="ghost" size="sm" onClick={() => setView(today)}>
              {t("common.today")}
            </Button>
            {allowClear && value && (
              <Button type="button" variant="ghost" size="sm" onClick={() => onChange("")}>
                {t("common.clear")}
              </Button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
