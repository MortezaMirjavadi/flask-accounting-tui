import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Loader2 } from "lucide-react";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  loading?: boolean;
  variant?: "default" | "destructive";
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  loading,
  variant = "destructive",
}: ConfirmDialogProps) {
  const { t } = useTranslation();

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <div className="flex items-start gap-3 text-start">
        {variant === "destructive" && (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
        )}
        <div className="flex-1">
          <h2 className="text-lg font-semibold">
            {title || t("common.areYouSure")}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {description || t("common.deleteConfirm")}
          </p>
        </div>
      </div>
      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button
          variant="outline"
          onClick={() => onOpenChange(false)}
          disabled={loading}
        >
          {t("common.cancel")}
        </Button>
        <Button
          variant={variant === "destructive" ? "destructive" : "default"}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
          {confirmLabel || t("common.confirm")}
        </Button>
      </div>
    </ResponsiveDialog>
  );
}
