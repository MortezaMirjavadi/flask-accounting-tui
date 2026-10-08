"use client";

import * as React from "react";
import { Check, ChevronDown, Pipette } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// ─── Preset Colors ────────────────────────────────────────────────────────────
// 24 visually distinct colors covering the full hue spectrum + neutrals.
// Arranged in rows of 6 for a clean 6×4 grid layout.
const DEFAULT_PRESETS = [
  // Row 1: warm spectrum (red → green)
  "#ef4444", // red-500
  "#f97316", // orange-500
  "#f59e0b", // amber-500
  "#eab308", // yellow-500
  "#84cc16", // lime-500
  "#22c55e", // green-500
  // Row 2: cool spectrum (teal → violet)
  "#14b8a6", // teal-500
  "#06b6d4", // cyan-500
  "#0ea5e9", // sky-500
  "#3b82f6", // blue-500
  "#6366f1", // indigo-500
  "#8b5cf6", // violet-500
  // Row 3: accent + earthy tones
  "#a855f7", // purple-500
  "#d946ef", // fuchsia-500
  "#ec4899", // pink-500
  "#f43f5e", // rose-500
  "#78716c", // stone-500
  "#71717a", // zinc-500
  // Row 4: neutrals + deep accents
  "#6b7280", // gray-500
  "#525252", // neutral-600
  "#1e40af", // blue-800
  "#166534", // green-800
  "#000000", // black
  "#ffffff", // white
] as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Normalize a hex string: lowercase, ensure leading #, expand shorthand */
function normalizeHex(hex: string): string {
  let h = hex.trim().toLowerCase();
  if (!h.startsWith("#")) h = `#${h}`;

  // Expand 3-char shorthand (#abc → #aabbcc)
  if (/^#[0-9a-f]{3}$/i.test(h)) {
    h = `#${h[1]}${h[1]}${h[2]}${h[2]}${h[3]}${h[3]}`;
  }

  return h;
}

/** Validate a 6-digit hex color string */
function isValidHex(hex: string): boolean {
  return /^#[0-9a-f]{6}$/i.test(hex);
}

/**
 * Determine whether to render black or white text/icon
 * on top of a given background color for sufficient contrast.
 * Uses the relative luminance formula (WCAG 2.x).
 */
function getContrastColor(hex: string): "black" | "white" {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  // Perceived luminance (YIQ)
  const luminance = (r * 299 + g * 587 + b * 114) / 1000;
  return luminance > 128 ? "black" : "white";
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ColorPickerProps {
  /** Current hex color value (e.g. "#3b82f6") */
  value: string;
  /** Callback when color changes */
  onChange: (value: string) => void;
  /** Disable the picker */
  disabled?: boolean;
  /** Override the default preset colors */
  presets?: readonly string[];
  /** Additional class names for the trigger button */
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ColorPicker({
  value,
  onChange,
  disabled = false,
  presets = DEFAULT_PRESETS,
  className,
}: ColorPickerProps) {
  const [open, setOpen] = React.useState(false);

  // Local state for the hex text input — allows typing before committing
  const [hexInput, setHexInput] = React.useState(value);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) setHexInput(value);
      setOpen(nextOpen);
    },
    [value],
  );

  const handlePresetClick = React.useCallback(
    (color: string) => {
      onChange(color);
      setHexInput(color);
    },
    [onChange],
  );

  const handleHexInputChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      setHexInput(raw);

      // Live-update if the user has typed a valid hex
      const normalized = normalizeHex(raw);
      if (isValidHex(normalized)) {
        onChange(normalized);
      }
    },
    [onChange],
  );

  const handleHexInputBlur = React.useCallback(() => {
    // On blur, revert to the last valid value if current input is invalid
    const normalized = normalizeHex(hexInput);
    if (isValidHex(normalized)) {
      onChange(normalized);
      setHexInput(normalized);
    } else {
      setHexInput(value);
    }
  }, [hexInput, value, onChange]);

  const handleNativePickerChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newColor = e.target.value;
      onChange(newColor);
      setHexInput(newColor);
    },
    [onChange],
  );

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const normalized = normalizeHex(hexInput);
        if (isValidHex(normalized)) {
          onChange(normalized);
          setHexInput(normalized);
          setOpen(false);
        }
      }
    },
    [hexInput, onChange],
  );

  // ── Derived ───────────────────────────────────────────────────────────────

  const normalizedValue = normalizeHex(value);
  const displayColor = isValidHex(normalizedValue) ? normalizedValue : "#3b82f6";

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            // RTL-aware: icon on the start side, chevron on the end side
            "h-10 w-full justify-start gap-2 px-3 font-normal",
            // Subtle inner shadow to feel "inset"
            "shadow-sm",
            className,
          )}
        >
          {/* Color preview swatch */}
          <span
            className="h-5 w-5 shrink-0 rounded-sm border border-border shadow-sm"
            style={{ backgroundColor: displayColor }}
            aria-hidden="true"
          />
          {/* Hex value text */}
          <span className="flex-1 text-start text-sm uppercase tracking-wider text-foreground">
            {displayColor}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-64 p-3" align="start">
        {/* ── Preset Swatches Grid ──────────────────────────────────────── */}
        <div
          className="grid grid-cols-6 gap-1.5"
          role="radiogroup"
          aria-label="Preset colors"
        >
          {presets.map((color) => {
            const normalized = normalizeHex(color);
            const isSelected = normalized === normalizedValue;
            const contrast = getContrastColor(normalized);
            const isWhite = normalized === "#ffffff";

            return (
              <button
                key={color}
                type="button"
                role="radio"
                aria-checked={isSelected}
                aria-label={color}
                title={color}
                className={cn(
                  "group relative h-8 w-8 rounded-md border transition-all",
                  "hover:scale-110 hover:shadow-md",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                  isSelected
                    ? "border-foreground ring-2 ring-foreground/20 scale-105"
                    : "border-border",
                  // White swatch needs a visible border
                  isWhite && !isSelected && "border-border",
                )}
                style={{ backgroundColor: normalized }}
                onClick={() => handlePresetClick(normalized)}
              >
                {/* Checkmark for selected swatch */}
                {isSelected && (
                  <Check
                    className="absolute inset-0 m-auto h-4 w-4"
                    style={{ color: contrast }}
                    strokeWidth={3}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* ── Separator ─────────────────────────────────────────────────── */}
        <div className="my-3 h-px bg-border" />

        {/* ── Custom Color Section ──────────────────────────────────────── */}
        <div className="flex items-center gap-2">
          {/* Hex text input */}
          <div className="relative flex-1">
            <span className="pointer-events-none absolute inset-y-0 start-2 flex items-center text-xs text-muted-foreground">
              #
            </span>
            <Input
              value={hexInput.replace("#", "")}
              onChange={(e) =>
                handleHexInputChange({
                  ...e,
                  target: { ...e.target, value: `#${e.target.value}` },
                })
              }
              onBlur={handleHexInputBlur}
              onKeyDown={handleKeyDown}
              placeholder="3b82f6"
              maxLength={7}
              className="h-8 ps-6 text-xs uppercase tracking-wider"
              aria-label="Hex color code"
            />
          </div>

          {/* Native color picker (hidden input + visible button) */}
          <div className="relative">
            <input
              type="color"
              value={displayColor}
              onChange={handleNativePickerChange}
              className="absolute inset-0 cursor-pointer opacity-0"
              aria-label="Open native color picker"
              tabIndex={-1}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8"
              aria-hidden="true"
              tabIndex={-1}
            >
              <Pipette className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
