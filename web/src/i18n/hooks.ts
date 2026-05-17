import { useTranslation } from "react-i18next";

export function useDirection(): "ltr" | "rtl" {
  const { i18n } = useTranslation();
  return i18n.language === "fa" ? "rtl" : "ltr";
}

export function useLocale(): string {
  const { i18n } = useTranslation();
  return i18n.language;
}
