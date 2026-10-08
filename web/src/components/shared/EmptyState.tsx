import { useTranslation } from "react-i18next";
import { Inbox } from "lucide-react";
import type { TranslationKey } from "@/types/i18next";

interface EmptyStateProps {
  titleKey?: TranslationKey;
  descriptionKey?: TranslationKey;
  icon?: React.ReactNode;
}

export function EmptyState({ titleKey, descriptionKey, icon }: EmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        {icon || <Inbox className="h-8 w-8 text-muted-foreground" />}
      </div>
      <h3 className="text-lg font-medium">{titleKey ? t(titleKey) : t("common.noData")}</h3>
      {descriptionKey && (
        <p className="mt-1 text-sm text-muted-foreground">{t(descriptionKey)}</p>
      )}
    </div>
  );
}
