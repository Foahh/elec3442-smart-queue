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

export interface SitesResponse {
  sites: SiteStatus[]
}

export interface HistoryResponse {
  snapshots: Snapshot[]
}

export interface IngestPayload {
  site_id: string
  display_name: string
  latitude?: number
  longitude?: number
  queue_length: number
  estimated_wait_seconds: number
  busyness_level: string
  comfort_score?: number
  sensors?: {
    temperature_c: number
    humidity_pct: number
    pressure_hpa: number
  }
  snapshot?: {
    timestamp: number
    queue_length: number
    estimated_wait_seconds: number
    busyness_level: string
    comfort_score?: number
  }
}
