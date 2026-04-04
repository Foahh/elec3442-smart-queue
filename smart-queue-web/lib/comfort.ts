export type ComfortLabel = "comfortable" | "moderate" | "uncomfortable"

export const COMFORT_COLORS: Record<ComfortLabel, string> = {
  comfortable:   "#00C800",
  moderate:      "#DC8C00",
  uncomfortable: "#C80000",
}

export function comfortColor(label: string): string {
  return COMFORT_COLORS[label as ComfortLabel] ?? "#888888"
}
