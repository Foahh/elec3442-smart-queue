export type BusynessLevel = "low" | "medium" | "high"

export const BUSYNESS_COLORS: Record<
  BusynessLevel | "stale",
  { hex: string; label: string }
> = {
  low: { hex: "#00C800", label: "Low" },
  medium: { hex: "#DC8C00", label: "Medium" },
  high: { hex: "#C80000", label: "High" },
  stale: { hex: "#000050", label: "???" },
}

export function busynessColor(level: string, stale: boolean): string {
  if (stale) return BUSYNESS_COLORS.stale.hex
  return (
    BUSYNESS_COLORS[level as BusynessLevel]?.hex ?? BUSYNESS_COLORS.stale.hex
  )
}
