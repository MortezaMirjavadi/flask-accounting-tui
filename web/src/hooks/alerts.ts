import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api";
import { queryKeys } from "@/keys";
import type { AlertsReport } from "@/types";

export function useAlerts() {
  return useQuery({
    queryKey: queryKeys.alerts.all,
    queryFn: () => apiGet<AlertsReport>("/alerts"),
  });
}
