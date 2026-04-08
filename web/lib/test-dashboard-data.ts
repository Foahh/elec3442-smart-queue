import { CHART_BUCKET_MS } from "@/lib/dashboard"
import type { SiteStatus, Snapshot } from "@/lib/types"

const TEST_SITES: Omit<
  SiteStatus,
  | "queue_length"
  | "estimated_wait_seconds"
  | "busyness_level"
  | "comfort_score"
  | "updated_at"
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

function busynessForQueue(n: number): "low" | "medium" | "high" {
  if (n >= 16) {
    return "high"
  }
  if (n >= 8) {
    return "medium"
  }
  return "low"
}

const LIVE_PHASE_MS = 8_000

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n))
}

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomBetween(min, max + 1))
}

function jitter(center: number, spread: number): number {
  return center + randomBetween(-spread, spread)
}

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

      const siteQueueBias = i * 3 + randomBetween(-1.5, 2.5)
      const waveA = Math.sin(b * 0.55 + phase + i * 0.9) * 5.5
      const waveB = Math.cos(b * 0.2 + phase * 0.7 + i * 1.7) * 3.5
      const burst = Math.random() < 0.14 ? randomBetween(4, 11) : 0
      const dip = Math.random() < 0.08 ? randomBetween(-5, -2) : 0
      const noise = randomBetween(-4, 4)

      const queueLength = clamp(
        Math.round(7 + siteQueueBias + waveA + waveB + burst + dip + noise),
        0,
        28
      )

      const estimatedWaitSeconds = clamp(
        Math.round(
          queueLength * randomBetween(28, 55) + randomBetween(-45, 70)
        ),
        0,
        60 * 35
      )

      const temperatureC = Number(
        clamp(
          21.5 +
            i * 0.9 +
            Math.sin(phase * 0.35 + b * 0.22 + i) * 1.8 +
            randomBetween(-1.4, 1.4),
          18,
          31
        ).toFixed(1)
      )

      const humidityPct = Math.round(
        clamp(
          46 +
            i * 3 +
            Math.cos(phase * 0.22 + b * 0.45 + i * 0.4) * 10 +
            randomBetween(-8, 8),
          30,
          88
        )
      )

      const pressureHpa = Math.round(
        clamp(
          1009 +
            i +
            Math.sin(phase * 0.08 + b * 0.18) * 3 +
            randomBetween(-2.2, 2.2),
          1002,
          1022
        )
      )

      const comfortScore = Math.round(
        clamp(
          86 -
            queueLength * randomBetween(1.6, 2.5) -
            Math.abs(temperatureC - 23) * randomBetween(1.2, 2.4) -
            Math.abs(humidityPct - 55) * randomBetween(0.25, 0.7) +
            randomBetween(-8, 8),
          20,
          96
        )
      )

      out.push({
        id: id++,
        site_id: siteId,
        timestamp: t,
        queue_length: queueLength,
        estimated_wait_seconds: estimatedWaitSeconds,
        busyness_level: busynessForQueue(queueLength),
        comfort_score: comfortScore,
        temperature_c: temperatureC,
        humidity_pct: humidityPct,
        pressure_hpa: pressureHpa,
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

  for (let i = 0; i < siteIds.length; i++) {
    const siteId = siteIds[i]

    for (let r = 0; r < rowsPerSite; r++) {
      const t = nowMs - r * stepMs - i * 7_000

      const trend = Math.sin(r * 0.33 + i * 1.2 + phase) * 6
      const secondary = Math.cos(r * 0.11 + phase * 0.6 + i) * 4
      const spike = Math.random() < 0.12 ? randomBetween(3, 10) : 0
      const drop = Math.random() < 0.07 ? randomBetween(-6, -2) : 0
      const noise = randomBetween(-5, 5)

      const queueLength = clamp(
        Math.round(6 + i * 2.5 + trend + secondary + spike + drop + noise),
        0,
        30
      )

      const estimatedWaitSeconds = clamp(
        Math.round(
          queueLength * randomBetween(30, 60) + randomBetween(-60, 90)
        ),
        0,
        60 * 40
      )

      const temperatureC = Number(
        clamp(
          22 +
            i * 0.7 +
            Math.sin(r * 0.14 + phase * 0.3 + i) * 2.2 +
            randomBetween(-1.8, 1.8),
          18,
          31
        ).toFixed(1)
      )

      const humidityPct = Math.round(
        clamp(
          48 +
            i * 2 +
            Math.cos(r * 0.27 + phase * 0.15) * 11 +
            randomBetween(-9, 9),
          30,
          90
        )
      )

      const pressureHpa = Math.round(
        clamp(
          1010 +
            i +
            Math.sin(r * 0.09 + phase * 0.05) * 4 +
            randomBetween(-2.5, 2.5),
          1001,
          1023
        )
      )

      const comfortScore = Math.round(
        clamp(
          84 -
            queueLength * randomBetween(1.7, 2.6) -
            Math.abs(temperatureC - 23.5) * randomBetween(1.1, 2.2) -
            Math.abs(humidityPct - 55) * randomBetween(0.25, 0.75) +
            randomBetween(-10, 10),
          18,
          95
        )
      )

      out.push({
        id: id++,
        site_id: siteId,
        timestamp: t,
        queue_length: queueLength,
        estimated_wait_seconds: estimatedWaitSeconds,
        busyness_level: busynessForQueue(queueLength),
        comfort_score: comfortScore,
        temperature_c: temperatureC,
        humidity_pct: humidityPct,
        pressure_hpa: pressureHpa,
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

export function getTestDashboardPreview(
  nowMs = TEST_EPOCH_MS
): TestDashboardPreview {
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

  const sites: SiteStatus[] = TEST_SITES.map((meta, i) => {
    const snap = latestBySite.get(meta.site_id)

    return {
      ...meta,
      stale: Math.random() < 0.06,
      temperature_c:
        snap?.temperature_c ??
        Number(jitter(meta.temperature_c ?? 23, 1.2).toFixed(1)),
      humidity_pct:
        snap?.humidity_pct ??
        Math.round(clamp(jitter(meta.humidity_pct ?? 55, 8), 30, 90)),
      pressure_hpa:
        snap?.pressure_hpa ??
        Math.round(clamp(jitter(meta.pressure_hpa ?? 1013, 3), 1000, 1024)),
      queue_length: snap?.queue_length ?? randomInt(0, 12),
      estimated_wait_seconds:
        snap?.estimated_wait_seconds ?? randomInt(0, 12) * 40,
      busyness_level: snap?.busyness_level ?? (i % 2 === 0 ? "low" : "medium"),
      comfort_score: snap?.comfort_score ?? randomInt(35, 90),
      updated_at: nowMs - randomInt(0, 45_000),
    }
  })

  return { sites, chartSnapshots, historySnapshots }
}
