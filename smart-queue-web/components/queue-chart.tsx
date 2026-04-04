"use client"

import { useMemo } from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { Snapshot } from "@/lib/api"
import { BUSYNESS_COLORS } from "@/lib/colors"

interface QueueChartProps {
  snapshots: Snapshot[]
  siteIds: string[]
  siteNames: Record<string, string>
}

const SITE_COLORS = ["#00C800", "#DC8C00", "#C80000", "#0088CC", "#AA00FF", "#FF6600", "#00AAAA", "#FF00AA"]

export function QueueChart({ snapshots, siteIds, siteNames }: QueueChartProps) {
  const chartConfig = useMemo(
    () =>
      Object.fromEntries(
        siteIds.map((id, i) => [
          id,
          { label: siteNames[id] ?? id, color: SITE_COLORS[i % SITE_COLORS.length] },
        ]),
      ),
    [siteIds, siteNames],
  )

  // Bucket snapshots into 5-min intervals, one key per site
  const data = useMemo(() => {
    const buckets: Record<number, Record<string, number>> = {}
    for (const s of snapshots) {
      const bucket = Math.floor(s.timestamp / 300_000) * 300_000
      buckets[bucket] ??= { timestamp: bucket }
      buckets[bucket][s.site_id] = s.queue_length
    }
    return Object.values(buckets)
      .sort((a, b) => (a.timestamp as number) - (b.timestamp as number))
      .map((b) => ({
        ...b,
        time: new Date(b.timestamp as number).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }))
  }, [snapshots])

  if (data.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No history data yet</p>
  }

  return (
    <ChartContainer config={chartConfig} className="h-64 w-full">
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        {siteIds.map((id, i) => (
          <Area
            key={id}
            type="monotone"
            dataKey={id}
            name={siteNames[id] ?? id}
            stroke={SITE_COLORS[i % SITE_COLORS.length]}
            fill={SITE_COLORS[i % SITE_COLORS.length] + "33"}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </AreaChart>
    </ChartContainer>
  )
}
