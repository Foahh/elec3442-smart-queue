"use client"

import { useEffect, useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { busynessColor } from "@/lib/colors"
import { formatSnapshotTime, formatWaitMinutes } from "@/lib/format"
import type { Snapshot } from "@/lib/types"

interface HistoryTableProps {
  snapshots: Snapshot[]
  pageSize?: number
}

export function HistoryTable({ snapshots, pageSize = 20 }: HistoryTableProps) {
  const [page, setPage] = useState(0)

  const sorted = useMemo(
    () => [...snapshots].sort((a, b) => b.timestamp - a.timestamp),
    [snapshots]
  )
  const total = sorted.length

  useEffect(() => {
    const lastPage = Math.max(Math.ceil(total / pageSize) - 1, 0)
    setPage((current) => Math.min(current, lastPage))
  }, [pageSize, total])

  const slice = sorted.slice(page * pageSize, (page + 1) * pageSize)

  if (total === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No history records
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead className="text-right">Queue</TableHead>
              <TableHead className="text-right">Wait</TableHead>
              <TableHead>Level</TableHead>
              <TableHead className="text-right">Comfortness</TableHead>
              <TableHead className="text-right">Temp</TableHead>
              <TableHead className="text-right">Humidity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {slice.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="tabular-nums">
                  {formatSnapshotTime(row.timestamp)}
                </TableCell>
                <TableCell className="text-right">{row.queue_length}</TableCell>
                <TableCell className="text-right">
                  {formatWaitMinutes(row.estimated_wait_seconds)}
                </TableCell>
                <TableCell>
                  <Badge
                    className="h-auto border-0 px-2 py-0.5 text-xs font-medium text-white"
                    style={{
                      backgroundColor: busynessColor(row.busyness_level, false),
                    }}
                  >
                    {row.busyness_level}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {row.comfort_score != null
                    ? `${Math.round(row.comfort_score)}%`
                    : "—"}
                </TableCell>
                <TableCell className="text-right">
                  {row.temperature_c != null
                    ? `${row.temperature_c.toFixed(1)}°C`
                    : "—"}
                </TableCell>
                <TableCell className="text-right">
                  {row.humidity_pct != null
                    ? `${row.humidity_pct.toFixed(0)}%`
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{total} records</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="px-2 py-1">
            {page + 1} / {Math.ceil(total / pageSize)}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={(page + 1) * pageSize >= total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
