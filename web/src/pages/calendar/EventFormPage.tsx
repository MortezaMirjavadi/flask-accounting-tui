import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import {
  useCalendarEvent,
  useCreateEvent,
  useUpdateEvent,
} from "@/hooks/calendar";
import { useCategories } from "@/hooks/categories";
import { useSources } from "@/hooks/sources";
import { eventSchema, type EventFormData, type EventFormInput } from "@/schemas/calendar";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { Textarea } from "@/components/ui/textarea";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";

const FREQUENCIES = ["once", "daily", "weekly", "monthly", "yearly"] as const;

export default function EventFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const isMobile = useIsMobile();

  const { data: event, isLoading: eventLoading } = useCalendarEvent(Number(id) || 0);
  const { data: categoriesResp, isLoading: categoriesLoading } = useCategories();
  const { data: sourcesResp, isLoading: sourcesLoading } = useSources();
  const categories = categoriesResp?.items;
  const sources = sourcesResp?.items;
  const createMutation = useCreateEvent();
  const updateMutation = useUpdateEvent();

  const form = useForm<EventFormInput, unknown, EventFormData>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      title: "",
      description: "",
      amount: 0,
      category_id: 0,
      source_id: null,
      frequency: "once",
      repeat_interval: 1,
      start_date: new Date().toISOString().split("T")[0],
      end_date: null,
      occurrence_limit: null,
    },
  });

  const frequency = useWatch({ control: form.control, name: "frequency" });

  useEffect(() => {
    if (isEdit && event) {
      form.reset({
        title: event.title,
        description: event.description || "",
        amount: event.amount,
        category_id: event.category_id,
        source_id: event.source_id,
        frequency: event.frequency,
        repeat_interval: event.repeat_interval,
        start_date: event.start_date,
        end_date: event.end_date,
        occurrence_limit: event.occurrence_limit,
      });
    }
  }, [isEdit, event, form]);

  async function onSubmit(data: EventFormData) {
    try {
      const payload = {
        ...data,
        source_id: data.source_id || null,
        end_date: data.end_date || null,
        occurrence_limit: data.occurrence_limit || null,
        description: frequency === "once" ? (data.description || "") : data.description,
      };

      if (isEdit) {
        await updateMutation.mutateAsync({ id: Number(id), data: payload });
        toast.success(t("common.success"));
        navigate("/calendar");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success(t("common.success"));
        navigate("/calendar");
      }
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isLoading = eventLoading || categoriesLoading || sourcesLoading;

  if (isEdit && isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {t("calendar.eventTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("calendar.eventTitle")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
              <FormField
                control={form.control}
                name="amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("common.amount")}</FormLabel>
                    <FormControl>
                      <AmountInput value={field.value} onChange={field.onChange} onBlur={field.onBlur} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("transactions.category")}</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder={t("common.select")} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categories?.map((cat) => (
                          <SelectItem key={cat.id} value={String(cat.id)}>
                            {cat.name}{" "}
                            {cat.type === "income"
                              ? `(${t("common.income")})`
                              : `(${t("common.cost")})`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="source_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.source")} ({t("common.select")})</FormLabel>
                  <Select
                    onValueChange={(val) => field.onChange(val === "none" ? null : Number(val))}
                    value={field.value ? String(field.value) : "none"}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {sources?.map((src) => (
                        <SelectItem key={src.id} value={String(src.id)}>
                          {src.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {t("calendar.frequency")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
              <FormField
                control={form.control}
                name="frequency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("calendar.frequency")}</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {FREQUENCIES.map((f) => (
                          <SelectItem key={f} value={f}>
                            {t(`calendar.${f}`)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {frequency !== "once" && (
                <FormField
                  control={form.control}
                  name="repeat_interval"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("calendar.repeatInterval")}</FormLabel>
                      <FormControl>
                        <Input type="number" min={1} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </div>

            <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
              <FormField
                control={form.control}
                name="start_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("calendar.startDate")}</FormLabel>
                    <FormControl>
                      <JalaliDatePicker value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {frequency !== "once" && (
                <FormField
                  control={form.control}
                  name="end_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("calendar.endDate")}</FormLabel>
                      <FormControl>
                        <JalaliDatePicker value={field.value || ""} onChange={(v) => field.onChange(v || null)} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </div>

            {frequency !== "once" && (
              <FormField
                control={form.control}
                name="occurrence_limit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("calendar.occurrenceLimit")}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        placeholder="∞"
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("common.description")}</FormLabel>
                  <FormControl>
                    <Textarea rows={4} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(-1)}
          >
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
            {isEdit ? t("common.update") : t("common.create")}
          </Button>
        </div>
      </form>
    </Form>
  );

  if (isMobile) {
    return (
      <Sheet open={true} onOpenChange={(open) => !open && navigate(-1)} direction="bottom">
        <SheetContent side="bottom" className="max-h-[90vh] overflow-y-auto px-4 pb-8">
          <SheetHeader className="text-start">
            <SheetTitle>
              {isEdit ? t("calendar.editTitle") : t("calendar.addTitle")}
            </SheetTitle>
          </SheetHeader>
          {formContent}
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-2xl font-bold">
        {isEdit ? t("calendar.editTitle") : t("calendar.addTitle")}
      </h1>

      {formContent}
    </motion.div>
  );
}
