import { useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toPersianDigits } from "@/lib/format";
import { PERSIAN_MONTHS } from "@/lib/constants";

const currentJalaliYear = Number(
  new Date().toLocaleDateString("fa-IR-u-nu-latn", {
    calendar: "persian",
    year: "numeric",
  }),
);
const yearOptions = Array.from(
  { length: 11 },
  (_, i) => currentJalaliYear - 5 + i,
);

// Period 13 from the API: { year: 1405, month: 7 }
const PERIOD = { year: 1405, month: 7 };

function Test() {
  const [year, setYear] = useState(PERIOD.year);
  const [month, setMonth] = useState(PERIOD.month);

  return (
    <div dir="rtl" style={{ padding: 24, maxWidth: 320 }}>
      <p style={{ marginBottom: 8 }}>سال</p>
      <Select
        value={String(year)}
        onValueChange={(v) => setYear(Number(v))}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {yearOptions.map((y) => (
            <SelectItem key={y} value={String(y)}>
              {toPersianDigits(String(y))}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <p style={{ margin: "16px 0 8px" }}>ماه</p>
      <Select
        value={String(month)}
        onValueChange={(v) => setMonth(Number(v))}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PERSIAN_MONTHS.map((m, i) => (
            <SelectItem key={i + 1} value={String(i + 1)}>
              {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <pre style={{ marginTop: 16, direction: "ltr", fontSize: 12 }}>
        {JSON.stringify({ year, month })}
      </pre>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<Test />);
