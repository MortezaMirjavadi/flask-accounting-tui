import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { FinancialEvent, EventInstance } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { EventFormData } from "@/schemas/calendar";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

export function useCalendarEvents(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.calendar.events(pagination as Record<string, string>),
    queryFn: () => apiGet<ApiListResponse<FinancialEvent>>(`/calendar/events${qs ? "?" + qs : ""}`),
  });
}

export function useCalendarEvent(id: number) {
  return useQuery({
    queryKey: queryKeys.calendar.eventDetail(id),
    queryFn: () => apiGet<FinancialEvent>(`/calendar/events/${id}`),
    enabled: !!id,
  });
}

export function useCalendarInstances(startDate: string, endDate: string, walletId?: number) {
  const params = new URLSearchParams();
  params.set("start_date", startDate);
  params.set("end_date", endDate);
  if (walletId) params.set("wallet_id", String(walletId));
  return useQuery({
    queryKey: queryKeys.calendar.instances({ start_date: startDate, end_date: endDate, wallet_id: String(walletId || "") }),
    queryFn: () =>
      apiGet<EventInstance[]>(
        `/calendar/instances?${params.toString()}`,
      ),
    enabled: !!startDate && !!endDate,
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EventFormData) =>
      apiPost<{ event: FinancialEvent; instances: EventInstance[] }>(
        "/calendar/events",
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useUpdateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: EventFormData }) =>
      apiPut<FinancialEvent>(`/calendar/events/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useDeleteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/calendar/events/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useCancelEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiPost(`/calendar/events/${id}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function usePauseEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiPost(`/calendar/events/${id}/pause`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useResumeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiPost(`/calendar/events/${id}/resume`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useConfirmInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (instanceId: number) =>
      apiPost<{ transaction_id: number; instance_id: number }>(
        `/calendar/instances/${instanceId}/confirm`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all });
    },
  });
}

export function useSnoozeInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ instanceId, newDueDate }: { instanceId: number; newDueDate: string }) =>
      apiPost<EventInstance>(`/calendar/instances/${instanceId}/snooze`, {
        new_due_date: newDueDate,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}

export function useCancelInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (instanceId: number) =>
      apiPost(`/calendar/instances/${instanceId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
}
