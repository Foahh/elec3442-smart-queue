import { CHART_BUCKET_MS } from "@/lib/dashboard"
import type { SiteStatus, Snapshot } from "@/lib/types"

const TEST_SITES: Omit<
  SiteStatus,
  "queue_length" | "estimated_wait_seconds" | "busyness_level" | "comfort_score" | "updated_at"
>[] = [
  {
    site_id: "test-north",
    display_name: "North Hall",
    latitude: 22.418,
    longitude: 114.207,
    stale: false,
    temperature_c: 23.2,
    humidity_pct: 58,
    pressure_hpa: 1011,
  },
  {
    site_id: "test-south",
    display_name: "South Wing",
    latitude: 22.415,
    longitude: 114.21,
    stale: false,
    temperature_c: 24.8,
    humidity_pct: 52,
    pressure_hpa: 1012,
  },
]

function busynessForQueue(n: number): string {
  if (n >= 16) {
    return "busy"
  }
  if (n >= 8) {
    return "moderate"
  }
  return "quiet"
}


const LIVE_PHASE_MS = 8_000

function buildBucketChartSnapshots(
  siteIds: string[],
  nowMs: number,
  bucketCount: number
): Snapshot[] {
  const out: Snapshot[] = []
  let id = 1
  const phase = nowMs / LIVE_PHASE_MS
  for (let b = bucketCount - 1; b >= 0; b--) {
    const t =
      Math.floor((nowMs - b * CHART_BUCKET_MS) / CHART_BUCKET_MS) *
      CHART_BUCKET_MS
    for (let i = 0; i < siteIds.length; i++) {
      const siteId = siteIds[i]
      const base = 6 + i * 4 + Math.sin((b + i) * 0.45 + phase) * 6
      const queueLength = Math.max(0, Math.round(base))
      out.push({
        id: id++,
        site_id: siteId,
        timestamp: t,
        queue_length: queueLength,
        estimated_wait_seconds: queueLength * 35,
        busyness_level: busynessForQueue(queueLength),
        comfort_score: Math.max(25, Math.min(95, Math.round(78 - queueLength * 1.8))),
        temperature_c: 22.5 + i * 0.6 + b * 0.02,
        humidity_pct: 48 + (b % 5) * 3,
        pressure_hpa: 1010 + i,
      })
    }
  }
  return out
}

function buildHistorySnapshots(
  siteIds: string[],
  nowMs: number,
  rowsPerSite: number
): Snapshot[] {
  const out: Snapshot[] = []
  let id = 1000
  const stepMs = 120_000
  const phase = nowMs / LIVE_PHASE_MS
  for (const siteId of siteIds) {
    const idx = siteIds.indexOf(siteId)
    for (let r = 0; r < rowsPerSite; r++) {
      const t = nowMs - r * stepMs - idx * 7_000
      const queueLength = Math.max(
        0,
        Math.round(4 + Math.sin(r * 0.31 + idx + phase) * 8 + idx * 2)
      )
      out.push({
        id: id++,
        site_id: siteId,
        timestamp: t,
        queue_length: queueLength,
        estimated_wait_seconds: queueLength * 40,
        busyness_level: busynessForQueue(queueLength),
        comfort_score:
          queueLength > 12 ? 42 : queueLength > 6 ? 58 : 72,
        temperature_c: 22 + idx * 0.4,
        humidity_pct: 50 + (r % 7) * 2,
        pressure_hpa: 1011,
      })
    }
  }
  return out
}

export interface TestDashboardPreview {
  sites: SiteStatus[]
  chartSnapshots: Snapshot[]
  historySnapshots: Snapshot[]
}

/** Default clock for stable snapshots when `nowMs` is omitted (e.g. tests). */
const TEST_EPOCH_MS = 1_704_067_200_000

export function getTestDashboardPreview(nowMs = TEST_EPOCH_MS): TestDashboardPreview {
  const siteIds = TEST_SITES.map((s) => s.site_id)
  const chartSnapshots = buildBucketChartSnapshots(siteIds, nowMs, 12)
  const historySnapshots = buildHistorySnapshots(siteIds, nowMs, 45)

  const latestBySite = new Map<string, Snapshot>()
  for (const s of chartSnapshots) {
    const prev = latestBySite.get(s.site_id)
    if (!prev || s.timestamp >= prev.timestamp) {
      latestBySite.set(s.site_id, s)
    }
  }

  const sites: SiteStatus[] = TEST_SITES.map((meta) => {
    const snap = latestBySite.get(meta.site_id)
    return {
      ...meta,
      queue_length: snap?.queue_length ?? 0,
      estimated_wait_seconds: snap?.estimated_wait_seconds ?? 0,
      busyness_level: snap?.busyness_level ?? "quiet",
      comfort_score: snap?.comfort_score ?? null,
      updated_at: nowMs,
    }
  })

  return { sites, chartSnapshots, historySnapshots }
}
