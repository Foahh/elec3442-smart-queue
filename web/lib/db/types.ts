export interface SiteStatusRow {
  site_id: string
  display_name: string
  latitude: number | null
  longitude: number | null
  queue_length: number
  estimated_wait_seconds: number
  busyness_level: string
  comfort_score: number | null
  updated_at: number
  temperature_c: number | null
  humidity_pct: number | null
  pressure_hpa: number | null
}

export interface SiteSnapshotRow {
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
