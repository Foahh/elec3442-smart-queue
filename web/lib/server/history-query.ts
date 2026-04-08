import {
  DEFAULT_HISTORY_LIMIT,
  DEFAULT_HISTORY_MINUTES,
  MAX_HISTORY_LIMIT,
} from "@/lib/dashboard"

export function parseHistoryQuery(request: Request) {
  const { searchParams } = new URL(request.url)

  return {
    siteId: searchParams.get("site_id"),
    minutes: parseNonNegativeNumber(
      searchParams.get("minutes"),
      DEFAULT_HISTORY_MINUTES
    ),
    limit: parseBoundedPositiveNumber(
      searchParams.get("limit"),
      DEFAULT_HISTORY_LIMIT,
      MAX_HISTORY_LIMIT
    ),
  }
}

function parseNonNegativeNumber(value: string | null, fallback: number) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback
  }
  return parsed
}

function parseBoundedPositiveNumber(
  value: string | null,
  fallback: number,
  maximum: number
) {
  const parsed = Number(value)

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback
  }

  return Math.min(parsed, maximum)
}
