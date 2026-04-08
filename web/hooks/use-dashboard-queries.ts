import { useQuery } from "@tanstack/react-query"
import { fetchHistory, fetchHistoryAll, fetchSites } from "@/lib/api"

export function useLiveDashboard() {
  return useQuery({
    queryKey: ["dashboard", "live"] as const,
    queryFn: async () => {
      const [sites, chartSnapshots] = await Promise.all([
        fetchSites(),
        fetchHistoryAll(60),
      ])
      return { sites, chartSnapshots }
    },
    refetchInterval: 5000,
  })
}

export function useSiteHistory(siteId: string | null) {
  return useQuery({
    queryKey: ["history", siteId, 1440, 1000] as const,
    queryFn: () => fetchHistory(siteId!, 1440, 1000),
    enabled: Boolean(siteId),
  })
}
