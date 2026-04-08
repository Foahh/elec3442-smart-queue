import { DASHBOARD_CHART_MINUTES } from "@/lib/dashboard"
import type {
  HistoryResponse,
  SiteStatus,
  SitesResponse,
  Snapshot,
} from "@/lib/types"

interface DashboardData {
  sites: SiteStatus[]
  chartSnapshots: Snapshot[]
}

interface ErrorResponse {
  error?: string
}

async function fetchJson<T>(input: string, fallbackMessage: string) {
  const res = await fetch(input, { cache: "no-store" })

  if (!res.ok) {
    throw new Error(await getErrorMessage(res, fallbackMessage))
  }

  return (await res.json()) as T
}

async function getErrorMessage(res: Response, fallbackMessage: string) {
  try {
    const data = (await res.json()) as ErrorResponse
    return data.error ?? fallbackMessage
  } catch {
    return fallbackMessage
  }
}

export async function fetchSites(): Promise<SiteStatus[]> {
  const data = await fetchJson<SitesResponse>(
    "/api/sites",
    "Failed to fetch sites"
  )
  return data.sites
}

export async function fetchHistory(
  siteId: string,
  minutes = 60,
  limit = 500
): Promise<Snapshot[]> {
  const params = new URLSearchParams({
    site_id: siteId,
    minutes: String(minutes),
    limit: String(limit),
  })
  const data = await fetchJson<HistoryResponse>(
    `/api/history?${params}`,
    "Failed to fetch history"
  )
  return data.snapshots
}

export async function fetchHistoryAll(minutes = 60): Promise<Snapshot[]> {
  const data = await fetchJson<HistoryResponse>(
    `/api/history/all?minutes=${minutes}`,
    "Failed to fetch history"
  )
  return data.snapshots
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [sites, chartSnapshots] = await Promise.all([
    fetchSites(),
    fetchHistoryAll(DASHBOARD_CHART_MINUTES),
  ])

  return { sites, chartSnapshots }
}
