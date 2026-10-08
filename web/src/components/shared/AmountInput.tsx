import { useState, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import i18n from "@/i18n";

interface AmountInputProps {
  value: number | string;
  onChange: (value: number) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

/**
 * A text input that displays amounts grouped per locale
 * (fa: "۱٬۰۰۰٬۰۰۰" / en: "1,000,000"). Accepts Persian and English digits;
 * the raw number in the form state is always an ASCII-digit number, so API
 * payloads never contain localized digits.
 */
export function AmountInput({
  value,
  onChange,
  onBlur,
  placeholder,
  className,
  disabled,
}: AmountInputProps) {
  const numericValue = Number(value);
  // Internal state: plain ASCII digit string (no separators).
  const [raw, setRaw] = useState(() =>
    numericValue > 0 ? String(Math.floor(numericValue)) : ""
  );

  // Sync state when the external value changes (e.g. form reset)
  useEffect(() => {
    const current = Number(value);
    const next = current > 0 ? String(Math.floor(current)) : "";
    setRaw((prev) => (prev === next ? prev : next));
  }, [value]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const digits = parseAmountInput(e.target.value);
      setRaw(digits);
      onChange(digits ? Number(digits) : 0);
    },
    [onChange]
  );

  const handleBlur = useCallback(() => {
    onChange(raw ? Number(raw) : 0);
    onBlur?.();
  }, [raw, onChange, onBlur]);

  return (
    <Input
      type="text"
      inputMode="numeric"
      dir="ltr"
      value={formatAmountInput(raw)}
      placeholder={placeholder ?? (i18n.language === "fa" ? "۰" : "0")}
      onChange={handleChange}
      onBlur={handleBlur}
      className={className}
      disabled={disabled}
    />
  );
}
