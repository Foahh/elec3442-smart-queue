import type { InferInsertModel, InferSelectModel } from "drizzle-orm"
import { SITE_STALE_AFTER_MS } from "@/lib/dashboard"
import { siteSnapshots, siteStatus } from "@/lib/schema"
import type { IngestPayload, SiteStatus, Snapshot } from "@/lib/types"

type SiteStatusRow = InferSelectModel<typeof siteStatus>
type SiteSnapshotRow = InferSelectModel<typeof siteSnapshots>

export function mapSiteStatusRow(
  row: SiteStatusRow,
  now = Date.now()
): SiteStatus {
  return {
    site_id: row.siteId,
    display_name: row.displayName,
    latitude: row.latitude,
    longitude: row.longitude,
    queue_length: row.queueLength,
    estimated_wait_seconds: row.estimatedWaitSeconds,
    busyness_level: row.busynessLevel,
    comfort_score: row.comfortScore,
    updated_at: row.updatedAt,
    stale: now - row.updatedAt > SITE_STALE_AFTER_MS,
    temperature_c: row.temperatureC,
    humidity_pct: row.humidityPct,
    pressure_hpa: row.pressureHpa,
  }
}

export function mapSnapshotRow(row: SiteSnapshotRow): Snapshot {
  return {
    id: row.id,
    site_id: row.siteId,
    timestamp: row.timestamp,
    queue_length: row.queueLength,
    estimated_wait_seconds: row.estimatedWaitSeconds,
    busyness_level: row.busynessLevel,
    comfort_score: row.comfortScore,
    temperature_c: row.temperatureC,
    humidity_pct: row.humidityPct,
    pressure_hpa: row.pressureHpa,
  }
}

export function buildSiteStatusValues(
  payload: IngestPayload,
  updatedAt: number
): InferInsertModel<typeof siteStatus> {
  return {
    siteId: payload.site_id,
    displayName: payload.display_name,
    latitude: payload.latitude ?? null,
    longitude: payload.longitude ?? null,
    queueLength: payload.queue_length,
    estimatedWaitSeconds: payload.estimated_wait_seconds,
    busynessLevel: payload.busyness_level,
    comfortScore: payload.comfort_score ?? null,
    updatedAt,
    temperatureC: payload.sensors?.temperature_c ?? null,
    humidityPct: payload.sensors?.humidity_pct ?? null,
    pressureHpa: payload.sensors?.pressure_hpa ?? null,
  }
}

export function buildSiteStatusUpdateValues(
  payload: IngestPayload,
  updatedAt: number
) {
  const { siteId: _siteId, ...updateValues } = buildSiteStatusValues(
    payload,
    updatedAt
  )

  return updateValues
}

export function buildSnapshotValues(
  payload: IngestPayload
): InferInsertModel<typeof siteSnapshots> | null {
  if (!payload.snapshot) {
    return null
  }

  return {
    siteId: payload.site_id,
    timestamp: payload.snapshot.timestamp,
    queueLength: payload.snapshot.queue_length,
    estimatedWaitSeconds: payload.snapshot.estimated_wait_seconds,
    busynessLevel: payload.snapshot.busyness_level,
    comfortScore: payload.snapshot.comfort_score ?? null,
    temperatureC: payload.sensors?.temperature_c ?? null,
    humidityPct: payload.sensors?.humidity_pct ?? null,
    pressureHpa: payload.sensors?.pressure_hpa ?? null,
  }
}
