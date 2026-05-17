import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api";
import { queryKeys } from "@/keys";
import type { Contact, Tag, Label } from "@/types";
import type { ApiListResponse } from "@/types/api";
import type { ContactFormData, TagFormData, LabelFormData } from "@/schemas/metadata";

interface PaginationParams {
  page?: number;
  per_page?: number;
}

// Contacts
export function useContacts(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.metadata.contacts(),
    queryFn: () => apiGet<ApiListResponse<Contact>>(`/metadata/contacts${qs ? "?" + qs : ""}`),
  });
}

export function useContact(id: number) {
  return useQuery({
    queryKey: queryKeys.metadata.contactDetail(id),
    queryFn: () => apiGet<Contact>(`/metadata/contacts/${id}`),
    enabled: !!id,
  });
}

export function useCreateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ContactFormData) => apiPost<Contact>("/metadata/contacts", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.contacts() });
    },
  });
}

export function useUpdateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ContactFormData }) =>
      apiPut<Contact>(`/metadata/contacts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.contacts() });
    },
  });
}

export function useDeleteContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/metadata/contacts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.contacts() });
    },
  });
}

// Tags
export function useTags(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.metadata.tags(),
    queryFn: () => apiGet<ApiListResponse<Tag>>(`/metadata/tags${qs ? "?" + qs : ""}`),
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TagFormData) => apiPost<Tag>("/metadata/tags", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.tags() });
    },
  });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TagFormData }) =>
      apiPut<Tag>(`/metadata/tags/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.tags() });
    },
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/metadata/tags/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.tags() });
    },
  });
}

export function useTransactionTags(txId: number) {
  return useQuery({
    queryKey: queryKeys.metadata.transactionTags(txId),
    queryFn: () => apiGet<Tag[]>(`/metadata/transactions/${txId}/tags`),
    enabled: !!txId,
  });
}

export function useSetTransactionTags() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txId, tagIds }: { txId: number; tagIds: number[] }) =>
      apiPut(`/metadata/transactions/${txId}/tags`, { tag_ids: tagIds }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.transactionTags(variables.txId) });
    },
  });
}

// Labels
export function useLabels(pagination?: PaginationParams) {
  const params = new URLSearchParams();
  if (pagination?.page) params.set("page", String(pagination.page));
  if (pagination?.per_page) params.set("per_page", String(pagination.per_page));
  const qs = params.toString();
  return useQuery({
    queryKey: queryKeys.metadata.labels(),
    queryFn: () => apiGet<ApiListResponse<Label>>(`/metadata/labels${qs ? "?" + qs : ""}`),
  });
}

export function useCreateLabel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LabelFormData) => apiPost<Label>("/metadata/labels", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.labels() });
    },
  });
}

export function useUpdateLabel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: LabelFormData }) =>
      apiPut<Label>(`/metadata/labels/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.labels() });
    },
  });
}

export function useDeleteLabel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/metadata/labels/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.labels() });
    },
  });
}

export function useTransactionLabels(txId: number) {
  return useQuery({
    queryKey: queryKeys.metadata.transactionLabels(txId),
    queryFn: () => apiGet<Label[]>(`/metadata/transactions/${txId}/labels`),
    enabled: !!txId,
  });
}

export function useSetTransactionLabels() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txId, labelIds }: { txId: number; labelIds: number[] }) =>
      apiPut(`/metadata/transactions/${txId}/labels`, { label_ids: labelIds }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.transactionLabels(variables.txId) });
    },
  });
}

export function useSourceLabels(sourceId: number) {
  return useQuery({
    queryKey: queryKeys.metadata.sourceLabels(sourceId),
    queryFn: () => apiGet<Label[]>(`/metadata/sources/${sourceId}/labels`),
    enabled: !!sourceId,
  });
}

export function useSetSourceLabels() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceId, labelIds }: { sourceId: number; labelIds: number[] }) =>
      apiPut(`/metadata/sources/${sourceId}/labels`, { label_ids: labelIds }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.metadata.sourceLabels(variables.sourceId) });
    },
  });
}
