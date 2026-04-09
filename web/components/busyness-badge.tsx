import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface BusynessBadgeProps {
  level: string
  stale?: boolean
  className?: string
  appearance?: "pill" | "inline"
}

const KNOWN_BUSYNESS_LEVELS = new Set(["low", "medium", "high"])

function formatBusynessLabel(value: string, stale: boolean) {
  if (stale) return "Unknown"

  switch (value.toLowerCase()) {
    case "low":
      return "Fast"
    case "medium":
      return "Moderate"
    case "high":
      return "Slow"
    default:
      return value
  }
}

export function BusynessBadge({
  level,
  stale = false,
  className,
  appearance = "pill",
}: BusynessBadgeProps) {
  const normalizedLevel = level.toLowerCase()
  const isKnownLevel = KNOWN_BUSYNESS_LEVELS.has(normalizedLevel)

  const variant =
    stale || !isKnownLevel
      ? "outline"
      : (normalizedLevel as "low" | "medium" | "high")

  const label = formatBusynessLabel(level, stale)

  if (appearance === "inline") {
    const toneClass =
      stale || !isKnownLevel
        ? "text-foreground"
        : normalizedLevel === "low"
          ? "text-[#00C800]"
          : normalizedLevel === "medium"
            ? "text-[#DC8C00]"
            : "text-[#C80000]"

    return (
      <span
        className={cn(
          "inline-flex w-full min-w-0 max-w-full items-center gap-1.5 text-[11px] leading-none font-medium tracking-[0.18em] uppercase",
          toneClass,
          className
        )}
      >
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" />
        <span className="min-w-0 truncate">{label}</span>
      </span>
    )
  }

  return (
    <Badge
      variant={variant}
      className={cn("h-auto px-2 py-0.5 text-xs font-medium", className)}
    >
      {label}
    </Badge>
  )
}
