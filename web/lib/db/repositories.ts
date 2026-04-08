import type { SiteSnapshotRow, SiteStatusRow } from "@/lib/db/types"

const LIST_SITE_STATUS = /* sql */ `
  SELECT
    site_id,
    display_name,
    latitude,
    longitude,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    updated_at,
    temperature_c,
    humidity_pct,
    pressure_hpa
  FROM site_status
`

const UPSERT_SITE_STATUS = /* sql */ `
  INSERT INTO site_status (
    site_id,
    display_name,
    latitude,
    longitude,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    updated_at,
    temperature_c,
    humidity_pct,
    pressure_hpa
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  ON CONFLICT (site_id) DO UPDATE SET
    display_name = excluded.display_name,
    latitude = excluded.latitude,
    longitude = excluded.longitude,
    queue_length = excluded.queue_length,
    estimated_wait_seconds = excluded.estimated_wait_seconds,
    busyness_level = excluded.busyness_level,
    comfort_score = excluded.comfort_score,
    updated_at = excluded.updated_at,
    temperature_c = excluded.temperature_c,
    humidity_pct = excluded.humidity_pct,
    pressure_hpa = excluded.pressure_hpa
`

const INSERT_SNAPSHOT = /* sql */ `
  INSERT INTO site_snapshots (
    site_id,
    timestamp,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    temperature_c,
    humidity_pct,
    pressure_hpa
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
`

const LIST_SNAPSHOTS_FOR_SITE = /* sql */ `
  SELECT
    id,
    site_id,
    timestamp,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    temperature_c,
    humidity_pct,
    pressure_hpa
  FROM site_snapshots
  WHERE site_id = ?
  ORDER BY timestamp DESC
  LIMIT ?
`

const LIST_SNAPSHOTS_FOR_SITE_SINCE = /* sql */ `
  SELECT
    id,
    site_id,
    timestamp,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    temperature_c,
    humidity_pct,
    pressure_hpa
  FROM site_snapshots
  WHERE site_id = ? AND timestamp >= ?
  ORDER BY timestamp DESC
  LIMIT ?
`

const LIST_ALL_SNAPSHOTS = /* sql */ `
  SELECT
    id,
    site_id,
    timestamp,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    temperature_c,
    humidity_pct,
    pressure_hpa
  FROM site_snapshots
  ORDER BY timestamp DESC
  LIMIT ?
`

const LIST_ALL_SNAPSHOTS_SINCE = /* sql */ `
  SELECT
    id,
    site_id,
    timestamp,
    queue_length,
    estimated_wait_seconds,
    busyness_level,
    comfort_score,
    temperature_c,
    humidity_pct,
    pressure_hpa
  FROM site_snapshots
  WHERE timestamp >= ?
  ORDER BY timestamp DESC
  LIMIT ?
`

export async function listAllSiteStatus(
  db: D1Database
): Promise<SiteStatusRow[]> {
  const { results } = await db.prepare(LIST_SITE_STATUS).all<SiteStatusRow>()
  return results ?? []
}

export async function upsertSiteStatus(
  db: D1Database,
  row: SiteStatusRow
): Promise<void> {
  await db
    .prepare(UPSERT_SITE_STATUS)
    .bind(
      row.site_id,
      row.display_name,
      row.latitude,
      row.longitude,
      row.queue_length,
      row.estimated_wait_seconds,
      row.busyness_level,
      row.comfort_score,
      row.updated_at,
      row.temperature_c,
      row.humidity_pct,
      row.pressure_hpa
    )
    .run()
}

export async function insertSiteSnapshot(
  db: D1Database,
  row: Omit<SiteSnapshotRow, "id">
): Promise<void> {
  await db
    .prepare(INSERT_SNAPSHOT)
    .bind(
      row.site_id,
      row.timestamp,
      row.queue_length,
      row.estimated_wait_seconds,
      row.busyness_level,
      row.comfort_score,
      row.temperature_c,
      row.humidity_pct,
      row.pressure_hpa
    )
    .run()
}

export async function listSnapshotsForSite(
  db: D1Database,
  siteId: string,
  options: { sinceTs?: number; limit: number }
): Promise<SiteSnapshotRow[]> {
  if (options.sinceTs !== undefined) {
    const { results } = await db
      .prepare(LIST_SNAPSHOTS_FOR_SITE_SINCE)
      .bind(siteId, options.sinceTs, options.limit)
      .all<SiteSnapshotRow>()
    return results ?? []
  }

  const { results } = await db
    .prepare(LIST_SNAPSHOTS_FOR_SITE)
    .bind(siteId, options.limit)
    .all<SiteSnapshotRow>()
  return results ?? []
}

export async function listAllSnapshots(
  db: D1Database,
  options: { sinceTs?: number; limit: number }
): Promise<SiteSnapshotRow[]> {
  if (options.sinceTs !== undefined) {
    const { results } = await db
      .prepare(LIST_ALL_SNAPSHOTS_SINCE)
      .bind(options.sinceTs, options.limit)
      .all<SiteSnapshotRow>()
    return results ?? []
  }

  const { results } = await db
    .prepare(LIST_ALL_SNAPSHOTS)
    .bind(options.limit)
    .all<SiteSnapshotRow>()
  return results ?? []
}
