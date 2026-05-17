import { useState, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";

/** Format a number string with commas: "1000000" -> "1,000,000" */
export function addCommas(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (!digits) return "";
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Remove commas and return the raw number string */
export function removeCommas(value: string): string {
  return value.replace(/,/g, "");
}

interface AmountInputProps {
  value: number | string;
  onChange: (value: number) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

/**
 * A text input that displays amounts with comma formatting (e.g., 1,000,000).
 * Only allows digit input. Stores the raw number in the form state.
 */
export function AmountInput({
  value,
  onChange,
  onBlur,
  placeholder = "0",
  className,
  disabled,
}: AmountInputProps) {
  const numericValue = Number(value);
  const [display, setDisplay] = useState(() =>
    numericValue > 0 ? addCommas(String(Math.floor(numericValue))) : ""
  );

  // Sync display when external value changes (e.g., form reset)
  useEffect(() => {
    const current = Number(value);
    const formatted = current > 0 ? addCommas(String(Math.floor(current))) : "";
    setDisplay((prev) => (prev === formatted ? prev : formatted));
  }, [value]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = removeCommas(e.target.value);
      if (!/^\d*$/.test(raw)) return;
      setDisplay(addCommas(raw));
      onChange(raw ? Number(raw) : 0);
    },
    [onChange]
  );

  const handleBlur = useCallback(() => {
    const raw = removeCommas(display);
    onChange(raw ? Number(raw) : 0);
    onBlur?.();
  }, [display, onChange, onBlur]);

  return (
    <Input
      type="text"
      inputMode="numeric"
      dir="ltr"
      value={display}
      placeholder={placeholder}
      onChange={handleChange}
      onBlur={handleBlur}
      className={className}
      disabled={disabled}
    />
  );
}
