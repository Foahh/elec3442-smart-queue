export interface SiteStatus {
  site_id: string
  display_name: string
  latitude: number | null
  longitude: number | null
  queue_length: number
  estimated_wait_seconds: number
  busyness_level: string
  comfort_score: number | null
  updated_at: number
  stale: boolean
  temperature_c: number | null
  humidity_pct: number | null
  pressure_hpa: number | null
}

export interface Snapshot {
  id: number
  site_id: string
  timestamp: number
  queue_length: number
  estimated_wait_seconds: number
  busyness_level: string
  comfort_score: number | null
  temperature_c: number | null
  humidity_pct: number | null
  pressure_hpa: number | null
}

export async function fetchSites(): Promise<SiteStatus[]> {
  const res = await fetch("/api/sites")
  if (!res.ok) throw new Error("Failed to fetch sites")
  const data = await res.json() as { sites: SiteStatus[] }
  return data.sites
}

export async function fetchHistory(siteId: string, minutes = 60, limit = 500): Promise<Snapshot[]> {
  const params = new URLSearchParams({ site_id: siteId, minutes: String(minutes), limit: String(limit) })
  const res = await fetch(`/api/history?${params}`)
  if (!res.ok) throw new Error("Failed to fetch history")
  const data = await res.json() as { snapshots: Snapshot[] }
  return data.snapshots
}

export async function fetchHistoryAll(minutes = 60): Promise<Snapshot[]> {
  const res = await fetch(`/api/history/all?minutes=${minutes}`)
  if (!res.ok) throw new Error("Failed to fetch history/all")
  const data = await res.json() as { snapshots: Snapshot[] }
  return data.snapshots
}
