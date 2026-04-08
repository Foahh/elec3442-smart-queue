import { SITE_STALE_AFTER_MS } from "@/lib/dashboard"
import type { SiteSnapshotRow, SiteStatusRow } from "@/lib/db/types"
import type { IngestPayload, SiteStatus, Snapshot } from "@/lib/types"

export function mapSiteStatusRow(
  row: SiteStatusRow,
  now = Date.now()
): SiteStatus {
  return {
    site_id: row.site_id,
    display_name: row.display_name,
    latitude: row.latitude,
    longitude: row.longitude,
    queue_length: row.queue_length,
    estimated_wait_seconds: row.estimated_wait_seconds,
    busyness_level: row.busyness_level,
    comfort_score: row.comfort_score,
    updated_at: row.updated_at,
    stale: now - row.updated_at > SITE_STALE_AFTER_MS,
    temperature_c: row.temperature_c,
    humidity_pct: row.humidity_pct,
    pressure_hpa: row.pressure_hpa,
  }
}

export function mapSnapshotRow(row: SiteSnapshotRow): Snapshot {
  return {
    id: row.id,
    site_id: row.site_id,
    timestamp: row.timestamp,
    queue_length: row.queue_length,
    estimated_wait_seconds: row.estimated_wait_seconds,
    busyness_level: row.busyness_level,
    comfort_score: row.comfort_score,
    temperature_c: row.temperature_c,
    humidity_pct: row.humidity_pct,
    pressure_hpa: row.pressure_hpa,
  }
}

export function buildSiteStatusRow(
  payload: IngestPayload,
  updatedAt: number
): SiteStatusRow {
  return {
    site_id: payload.site_id,
    display_name: payload.display_name,
    latitude: payload.latitude ?? null,
    longitude: payload.longitude ?? null,
    queue_length: payload.queue_length,
    estimated_wait_seconds: payload.estimated_wait_seconds,
    busyness_level: payload.busyness_level,
    comfort_score: payload.comfort_score ?? null,
    updated_at: updatedAt,
    temperature_c: payload.sensors?.temperature_c ?? null,
    humidity_pct: payload.sensors?.humidity_pct ?? null,
    pressure_hpa: payload.sensors?.pressure_hpa ?? null,
  }
}

export function buildSnapshotInsertRow(
  payload: IngestPayload
): Omit<SiteSnapshotRow, "id"> | null {
  if (!payload.snapshot) {
    return null
  }

  return {
    site_id: payload.site_id,
    timestamp: payload.snapshot.timestamp,
    queue_length: payload.snapshot.queue_length,
    estimated_wait_seconds: payload.snapshot.estimated_wait_seconds,
    busyness_level: payload.snapshot.busyness_level,
    comfort_score: payload.snapshot.comfort_score ?? null,
    temperature_c: payload.sensors?.temperature_c ?? null,
    humidity_pct: payload.sensors?.humidity_pct ?? null,
    pressure_hpa: payload.sensors?.pressure_hpa ?? null,
  }
}
