"use client"

import { useQuery } from "@tanstack/react-query"
import { useTestDashboardMode } from "@/lib/test-dashboard-context"
import { fetchDashboardData, fetchHistory } from "@/lib/api"
import {
  DASHBOARD_POLL_INTERVAL_MS,
  HISTORY_LIMIT,
  SITE_HISTORY_MINUTES,
} from "@/lib/dashboard"
import { getTestDashboardPreview } from "@/lib/test-dashboard-data"

export function useLiveDashboard() {
  const mock = useTestDashboardMode()
  return useQuery({
    queryKey: ["dashboard", "live", mock ? "mock" : "live"] as const,
    queryFn: mock
      ? async () => {
          const p = getTestDashboardPreview(Date.now())
          return {
            sites: p.sites,
            chartSnapshots: p.chartSnapshots,
          }
        }
      : fetchDashboardData,
    refetchInterval: DASHBOARD_POLL_INTERVAL_MS,
  })
}

export function useSiteHistory(siteId: string | null) {
  const mock = useTestDashboardMode()
  return useQuery({
    queryKey: [
      "history",
      siteId,
      SITE_HISTORY_MINUTES,
      HISTORY_LIMIT,
      mock ? "mock" : "live",
    ] as const,
    queryFn: async () => {
      if (!siteId) {
        return []
      }

      if (mock) {
        const p = getTestDashboardPreview(Date.now())
        return p.historySnapshots.filter((s) => s.site_id === siteId)
      }

      return fetchHistory(siteId, SITE_HISTORY_MINUTES, HISTORY_LIMIT)
    },
    enabled: Boolean(siteId),
    refetchInterval: mock ? DASHBOARD_POLL_INTERVAL_MS : false,
  })
}
