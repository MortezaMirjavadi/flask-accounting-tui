import { useTranslation } from "react-i18next";

export function useDirection(): "ltr" | "rtl" {
  const { i18n } = useTranslation();
  // i18next.dir() handles regional codes (fa-IR, ar-EG, …) via its RTL language list
  return i18n.dir() === "rtl" ? "rtl" : "ltr";
}

export function useLocale(): string {
  const { i18n } = useTranslation();
  return i18n.language;
}
