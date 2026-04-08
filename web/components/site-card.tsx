"use client"

import { Droplets, Gauge, Thermometer, Wifi, WifiOff } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getComfortLabel } from "@/lib/dashboard"
import { formatElapsedSeconds, formatWaitMinutes } from "@/lib/format"
import { busynessColor } from "@/lib/colors"
import { comfortColor } from "@/lib/comfort"
import type { SiteStatus } from "@/lib/types"

interface SiteCardProps {
  site: SiteStatus
}

export function SiteCard({ site }: SiteCardProps) {
  const color = busynessColor(site.busyness_level, site.stale)
  const comfortLabel =
    site.comfort_score != null ? getComfortLabel(site.comfort_score) : null

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            {site.display_name}
          </CardTitle>
          {site.stale ? (
            <WifiOff className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Wifi className="h-4 w-4 text-green-500" />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-2 text-sm">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold">{site.queue_length}</span>
          <span className="text-muted-foreground">in queue</span>
          <span className="ml-auto font-medium">
            {formatWaitMinutes(site.estimated_wait_seconds, {
              approximate: true,
            })}
          </span>
        </div>

        <div
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: color }}
        >
          {site.busyness_level.toUpperCase()}
        </div>

        {site.comfort_score != null && comfortLabel && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">Comfort:</span>
            <span
              className="font-semibold"
              style={{ color: comfortColor(comfortLabel) }}
            >
              {Math.round(site.comfort_score)}
            </span>
            <span className="text-muted-foreground">({comfortLabel})</span>
          </div>
        )}

        {(site.temperature_c != null ||
          site.humidity_pct != null ||
          site.pressure_hpa != null) && (
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {site.temperature_c != null && (
              <span className="flex items-center gap-1">
                <Thermometer className="h-3 w-3" />
                {site.temperature_c.toFixed(1)}°C
              </span>
            )}
            {site.humidity_pct != null && (
              <span className="flex items-center gap-1">
                <Droplets className="h-3 w-3" />
                {site.humidity_pct.toFixed(0)}%
              </span>
            )}
            {site.pressure_hpa != null && (
              <span className="flex items-center gap-1">
                <Gauge className="h-3 w-3" />
                {site.pressure_hpa.toFixed(0)} hPa
              </span>
            )}
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          {site.stale
            ? `Last seen ${formatElapsedSeconds(site.updated_at)}`
            : `Updated ${formatElapsedSeconds(site.updated_at)}`}
        </p>
      </CardContent>
    </Card>
  )
}
