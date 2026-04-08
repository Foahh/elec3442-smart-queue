"use client"

import { Droplets, Gauge, Thermometer, Wifi, WifiOff } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SiteStatus } from "@/lib/api"
import { busynessColor } from "@/lib/colors"
import { comfortColor } from "@/lib/comfort"

interface SiteCardProps {
  site: SiteStatus
  queueMaxDisplay?: number
}

export function SiteCard({ site, queueMaxDisplay = 16 }: SiteCardProps) {
  const color = busynessColor(site.busyness_level, site.stale)
  const filled = Math.min(
    8,
    Math.round((site.queue_length / queueMaxDisplay) * 8)
  )
  const lastSeen = Math.round((Date.now() - site.updated_at) / 1000)

  return (
    <Card className="overflow-hidden">
      {/* color band — same proportional fill as Sense HAT */}
      <div className="flex h-4 w-full">
        {Array.from({ length: 8 }, (_, i) => (
          <div
            key={i}
            className="flex-1"
            style={{ backgroundColor: i < filled ? color : color + "1a" }}
          />
        ))}
      </div>

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
            ~{Math.round(site.estimated_wait_seconds / 60)} min wait
          </span>
        </div>

        <div
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: color }}
        >
          {site.busyness_level.toUpperCase()}
        </div>

        {site.comfort_score != null && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">Comfort:</span>
            <span
              className="font-semibold"
              style={{
                color: comfortColor(
                  site.comfort_score >= 70
                    ? "comfortable"
                    : site.comfort_score >= 40
                      ? "moderate"
                      : "uncomfortable"
                ),
              }}
            >
              {Math.round(site.comfort_score)}
            </span>
            <span className="text-muted-foreground">
              (
              {site.comfort_score >= 70
                ? "comfortable"
                : site.comfort_score >= 40
                  ? "moderate"
                  : "uncomfortable"}
              )
            </span>
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
            ? `Last seen ${lastSeen}s ago`
            : `Updated ${lastSeen}s ago`}
        </p>
      </CardContent>
    </Card>
  )
}
