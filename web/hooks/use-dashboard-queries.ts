import { useQuery } from "@tanstack/react-query"
import { fetchDashboardData, fetchHistory } from "@/lib/api"
import {
  DASHBOARD_POLL_INTERVAL_MS,
  HISTORY_LIMIT,
  SITE_HISTORY_MINUTES,
} from "@/lib/dashboard"

export function useLiveDashboard() {
  return useQuery({
    queryKey: ["dashboard", "live"] as const,
    queryFn: fetchDashboardData,
    refetchInterval: DASHBOARD_POLL_INTERVAL_MS,
  })
}

export function useSiteHistory(siteId: string | null) {
  return useQuery({
    queryKey: ["history", siteId, SITE_HISTORY_MINUTES, HISTORY_LIMIT] as const,
    queryFn: async () => {
      if (!siteId) {
        return []
      }

      return fetchHistory(siteId, SITE_HISTORY_MINUTES, HISTORY_LIMIT)
    },
    enabled: Boolean(siteId),
  })
}
