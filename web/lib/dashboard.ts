import type { SiteStatus } from "@/lib/types"
import type { ComfortLabel } from "@/lib/comfort"

export const DASHBOARD_POLL_INTERVAL_MS = 5_000
export const DEFAULT_HISTORY_MINUTES = 60
export const DEFAULT_HISTORY_LIMIT = 500
export const MAX_HISTORY_LIMIT = 1_000
export const HISTORY_LIMIT = MAX_HISTORY_LIMIT
export const SITE_HISTORY_MINUTES = 1_440
export const DASHBOARD_CHART_MINUTES = 60
export const CHART_BUCKET_MS = 300_000
export const SITE_STALE_AFTER_MS = 30_000

const SITE_FILL_SEGMENTS = 8

export function getSiteIds(sites: SiteStatus[]) {
  return sites.map((site) => site.site_id)
}

export function getSiteNameMap(sites: SiteStatus[]) {
  return Object.fromEntries(
    sites.map((site) => [site.site_id, site.display_name])
  )
}

export function getQueueFillSegments(
  queueLength: number,
  queueMaxDisplay: number,
  segmentCount = SITE_FILL_SEGMENTS
) {
  if (queueMaxDisplay <= 0) {
    return 0
  }

  return Math.min(
    segmentCount,
    Math.round((queueLength / queueMaxDisplay) * segmentCount)
  )
}

export function getComfortLabel(score: number): ComfortLabel {
  if (score >= 70) {
    return "comfortable"
  }

  if (score >= 40) {
    return "moderate"
  }

  return "uncomfortable"
}
