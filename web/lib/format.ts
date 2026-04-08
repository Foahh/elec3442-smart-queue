function pad2(n: number) {
  return String(n).padStart(2, "0")
}

/** Local wall time, fixed shape (not browser-locale wording like "Apr … AM"). */
function localYmdHm(timestamp: number) {
  const d = new Date(timestamp)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

export function formatChartTime(timestamp: number) {
  const d = new Date(timestamp)
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

export function formatSnapshotTime(timestamp: number) {
  return localYmdHm(timestamp)
}

export function formatLastUpdated(timestamp: number) {
  const d = new Date(timestamp)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
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
