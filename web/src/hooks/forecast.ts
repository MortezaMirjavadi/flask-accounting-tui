import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api";
import { queryKeys } from "@/keys";
import type { ForecastReport } from "@/types";

export function useForecast(periodDays: number = 30) {
  return useQuery({
    queryKey: queryKeys.forecast.byPeriod(periodDays),
    queryFn: () => apiGet<ForecastReport>(`/reports/forecast?period_days=${periodDays}`),
  });
}
