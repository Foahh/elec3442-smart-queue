"use client"

import {
  Activity,
  Clock3,
  Droplets,
  Gauge,
  Thermometer,
  Wifi,
  WifiOff,
} from "lucide-react"
import { BusynessBadge } from "@/components/busyness-badge"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getComfortLabel } from "@/lib/dashboard"
import { formatElapsedSeconds } from "@/lib/format"
import { busynessColor } from "@/lib/colors"
import { cn } from "@/lib/utils"
import { comfortColor } from "@/lib/comfort"
import type { SiteStatus } from "@/lib/types"

interface SiteCardProps {
  site: SiteStatus
}

function withAlpha(hex: string, opacity: number) {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return hex

  const alpha = Math.round(Math.min(Math.max(opacity, 0), 1) * 255)
    .toString(16)
    .padStart(2, "0")

  return `${hex}${alpha}`
}

function getComfortEmoji(label: ReturnType<typeof getComfortLabel> | null) {
  switch (label) {
    case "comfortable":
      return "🙂"
    case "moderate":
      return "😐"
    case "uncomfortable":
      return "🥵"
    default:
      return null
  }
}

function MetricPill({
  icon: Icon,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <Badge
      variant="ghost"
      className="h-auto min-h-6 gap-1.5 rounded-2xl px-2.5 py-1 font-normal text-muted-foreground [&>svg]:!size-3.5"
    >
      <Icon />
      {children}
    </Badge>
  )
}

const statVariants = {
  queue:
    "border-l-chart-3/80 bg-gradient-to-br from-chart-3/[0.07] to-card/40 dark:from-chart-3/[0.11]",
  wait:
    "border-l-chart-1/80 bg-gradient-to-br from-chart-1/[0.08] to-card/40 dark:from-chart-1/[0.12]",
} as const

function StatCard({
  icon: Icon,
  label,
  variant,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  variant: keyof typeof statVariants
  children: React.ReactNode
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border/60 p-3 shadow-[inset_0_1px_0_0_rgb(255_255_255/0.06)] backdrop-blur-sm dark:shadow-none",
        "border-l-[3px] pl-3",
        statVariants[variant]
      )}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase">
          <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {label}
        </div>
        <div className="mt-2">{children}</div>
      </div>
    </div>
  )
}

export function SiteCard({ site }: SiteCardProps) {
  const isStale = site.stale
  const accentColor = isStale
    ? null
    : busynessColor(site.busyness_level, isStale)

  const comfortLabel =
    site.comfort_score != null ? getComfortLabel(site.comfort_score) : null
  const comfortTone =
    site.comfort_score != null && comfortLabel
      ? comfortColor(comfortLabel)
      : null
  const comfortEmoji = getComfortEmoji(comfortLabel)

  const liveLabel = isStale ? "Offline" : "Live"
  const LiveIcon = isStale ? WifiOff : Wifi

  const liveBadgeClassName = isStale
    ? "inline-flex h-6 items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase"
    : "inline-flex h-6 items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 text-[11px] font-medium tracking-[0.18em] text-emerald-700 uppercase dark:text-emerald-300"

  const busynessCardClassName = isStale
    ? "flex h-6 items-center rounded-full border border-border bg-background/80 px-2.5 text-right"
    : "flex h-6 items-center rounded-full border px-2.5 text-right"

  const waitMinutes = Math.max(
    0,
    Math.round(site.estimated_wait_seconds / 60)
  )

  const hasEnvironmentMetrics =
    site.temperature_c != null ||
    site.humidity_pct != null ||
    site.pressure_hpa != null

  return (
    <Card className="relative h-full gap-3 border border-border/70 bg-gradient-to-br from-card via-card to-muted/35 pt-5 pb-0 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-xl">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-28 blur-3xl"
        style={{
          background: accentColor
            ? `linear-gradient(135deg, ${withAlpha(accentColor, 0.22)} 0%, transparent 72%)`
            : "none",
        }}
      />

      <CardHeader className="relative gap-2 pb-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1 space-y-2">
            <div className={liveBadgeClassName}>
              <LiveIcon className="h-3.5 w-3.5" />
              {liveLabel}
            </div>

            <div className="space-y-1">
              <CardTitle className="truncate text-lg font-semibold tracking-tight">
                {site.display_name}
              </CardTitle>
            </div>
          </div>

          <div className="flex shrink-0 items-center whitespace-nowrap">
            <div
              className={busynessCardClassName}
              style={
                accentColor
                  ? {
                      backgroundColor: withAlpha(accentColor, 0.1),
                      borderColor: withAlpha(accentColor, 0.22),
                    }
                  : undefined
              }
            >
              <BusynessBadge
                level={site.busyness_level}
                stale={isStale}
                appearance="inline"
              />
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative flex flex-col gap-2 text-sm">
        <div className="grid grid-cols-2 gap-2">
          <StatCard icon={Activity} label="Queue" variant="queue">
            <div className="flex min-w-0 items-baseline gap-1">
              <span className="truncate text-2xl leading-none font-semibold tabular-nums tracking-tight sm:text-3xl">
                {site.queue_length}
              </span>
              <span className="shrink-0 text-[12px] font-medium text-muted-foreground">
                people
              </span>
            </div>
          </StatCard>

          <StatCard icon={Clock3} label="Wait" variant="wait">
            <div className="flex min-w-0 items-baseline gap-1">
              <span className="sr-only">Approximately </span>
              <span className="inline-flex min-w-0 items-baseline gap-1">
                <span
                  className="shrink-0 text-lg font-medium text-muted-foreground"
                  aria-hidden
                >
                  ~
                </span>
                <span className="min-w-0 truncate text-2xl leading-none font-semibold tabular-nums tracking-tight sm:text-3xl">
                  {waitMinutes}
                </span>
              </span>
              <span className="shrink-0 text-[12px] font-medium text-muted-foreground">
                min
              </span>
            </div>
          </StatCard>
        </div>

        {site.comfort_score != null && comfortLabel && comfortTone && (
          <div className="flex w-full justify-center">
            <div
              className="flex min-w-0 w-[calc((100%-0.5rem)/2)] items-center justify-center gap-1.5 rounded-full bg-transparent px-2.5 py-1 text-xs font-medium transition-colors hover:bg-muted/50"
              style={{ color: comfortTone }}
            >
              {comfortEmoji ? (
                <span className="text-[15px] leading-none" aria-hidden>
                  {comfortEmoji}
                </span>
              ) : (
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: comfortTone }}
                />
              )}
              {`Comfort ${Math.round(site.comfort_score)}%`}
            </div>
          </div>
        )}

        {hasEnvironmentMetrics && (
          <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
            {site.temperature_c != null && (
              <MetricPill icon={Thermometer}>
                {site.temperature_c.toFixed(1)}°C
              </MetricPill>
            )}

            {site.humidity_pct != null && (
              <MetricPill icon={Droplets}>
                {site.humidity_pct.toFixed(0)}%
              </MetricPill>
            )}

            {site.pressure_hpa != null && (
              <MetricPill icon={Gauge}>
                {site.pressure_hpa.toFixed(0)} hPa
              </MetricPill>
            )}
          </div>
        )}

        <div className="flex min-h-10 items-center justify-center border-t border-border/60 py-2 text-center text-xs text-muted-foreground">
          <p>
            {isStale
              ? `Last seen ${formatElapsedSeconds(site.updated_at)}`
              : `Updated ${formatElapsedSeconds(site.updated_at)}`}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
