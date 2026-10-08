import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Globe } from "lucide-react";

export function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const next = i18n.language === "en" ? "fa" : "en";
    i18n.changeLanguage(next);
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleLanguage}
      className="h-8 gap-1.5 px-2 text-xs"
    >
      <Globe className="h-3.5 w-3.5" />
      {i18n.language === "en" ? "فارسی" : "EN"}
    </Button>
  );
}
