const chartTimeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
})

const snapshotTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
})

const lastUpdatedFormatter = new Intl.DateTimeFormat(undefined, {
  timeStyle: "medium",
})

export function formatChartTime(timestamp: number) {
  return chartTimeFormatter.format(timestamp)
}

export function formatSnapshotTime(timestamp: number) {
  return snapshotTimeFormatter.format(timestamp)
}

export function formatLastUpdated(timestamp: number) {
  return lastUpdatedFormatter.format(timestamp)
}

export function formatWaitMinutes(
  seconds: number,
  options: { approximate?: boolean } = {}
) {
  const minutes = Math.max(0, Math.round(seconds / 60))
  return options.approximate ? `~${minutes} min wait` : `${minutes} min`
}

export function formatElapsedSeconds(timestamp: number, now = Date.now()) {
  const seconds = Math.max(0, Math.round((now - timestamp) / 1000))
  return `${seconds}s ago`
}
