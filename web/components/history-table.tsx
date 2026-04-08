"use client"

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { BusynessBadge } from "@/components/busyness-badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatSnapshotTime, formatWaitMinutes } from "@/lib/format"
import type { Snapshot } from "@/lib/types"

interface HistoryTableProps {
  snapshots: Snapshot[]
  pageSize?: number
}

type HistorySortKey =
  | "timestamp"
  | "queue_length"
  | "estimated_wait_seconds"
  | "busyness_level"
  | "comfort_score"
  | "temperature_c"
  | "humidity_pct"

type SortDir = "asc" | "desc"

function busynessRank(level: string): number {
  switch (level.toLowerCase()) {
    case "low":
      return 0
    case "medium":
      return 1
    case "high":
      return 2
    default:
      return 3
  }
}

function compareSnapshots(
  a: Snapshot,
  b: Snapshot,
  key: HistorySortKey,
  dir: SortDir
): number {
  const mul = dir === "asc" ? 1 : -1

  const cmpNullableNum = (x: number | null, y: number | null) => {
    if (x == null && y == null) return 0
    if (x == null) return 1
    if (y == null) return -1
    return Math.sign(x - y) * mul
  }

  switch (key) {
    case "timestamp":
    case "queue_length":
    case "estimated_wait_seconds":
      return Math.sign((a[key] - b[key]) * mul)
    case "comfort_score":
      return cmpNullableNum(a.comfort_score, b.comfort_score)
    case "temperature_c":
      return cmpNullableNum(a.temperature_c, b.temperature_c)
    case "humidity_pct":
      return cmpNullableNum(a.humidity_pct, b.humidity_pct)
    case "busyness_level":
      return (
        Math.sign(
          (busynessRank(a.busyness_level) - busynessRank(b.busyness_level)) *
            mul
        ) || a.busyness_level.localeCompare(b.busyness_level) * mul
      )
    default:
      return 0
  }
}

function SortableHead({
  label,
  columnKey,
  currentKey,
  dir,
  onSort,
}: {
  label: string
  columnKey: HistorySortKey
  currentKey: HistorySortKey
  dir: SortDir
  onSort: (key: HistorySortKey) => void
}) {
  const active = currentKey === columnKey
  return (
    <TableHead
      aria-sort={
        active ? (dir === "asc" ? "ascending" : "descending") : undefined
      }
    >
      <button
        type="button"
        onClick={() => onSort(columnKey)}
        className="-mx-1 -my-0.5 inline-flex items-center gap-1 rounded-md px-1 py-0.5 text-left transition-colors hover:bg-muted/60"
      >
        <span>{label}</span>
        {active ? (
          dir === "asc" ? (
            <ArrowUp className="size-3.5 shrink-0 opacity-70" aria-hidden />
          ) : (
            <ArrowDown className="size-3.5 shrink-0 opacity-70" aria-hidden />
          )
        ) : (
          <ArrowUpDown className="size-3.5 shrink-0 opacity-40" aria-hidden />
        )}
      </button>
    </TableHead>
  )
}

export function HistoryTable({ snapshots, pageSize = 20 }: HistoryTableProps) {
  const [page, setPage] = useState(0)
  const [sortKey, setSortKey] = useState<HistorySortKey>("timestamp")
  const [sortDir, setSortDir] = useState<SortDir>("desc")

  const sorted = useMemo(
    () =>
      [...snapshots].sort((a, b) => {
        const primary = compareSnapshots(a, b, sortKey, sortDir)
        if (primary !== 0) return primary
        return b.timestamp - a.timestamp
      }),
    [snapshots, sortDir, sortKey]
  )
  const total = sorted.length

  useEffect(() => {
    setPage(0)
  }, [sortDir, sortKey])

  useEffect(() => {
    const lastPage = Math.max(Math.ceil(total / pageSize) - 1, 0)
    setPage((current) => Math.min(current, lastPage))
  }, [pageSize, total])

  const slice = sorted.slice(page * pageSize, (page + 1) * pageSize)

  const toggleSort = (key: HistorySortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("desc")
    }
  }

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
              <SortableHead
                label="Time"
                columnKey="timestamp"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Queue"
                columnKey="queue_length"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Wait"
                columnKey="estimated_wait_seconds"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Level"
                columnKey="busyness_level"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Comfortness"
                columnKey="comfort_score"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Temp"
                columnKey="temperature_c"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
              <SortableHead
                label="Humidity"
                columnKey="humidity_pct"
                currentKey={sortKey}
                dir={sortDir}
                onSort={toggleSort}
              />
            </TableRow>
          </TableHeader>
          <TableBody>
            {slice.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="tabular-nums">
                  {formatSnapshotTime(row.timestamp)}
                </TableCell>
                <TableCell className="tabular-nums">
                  {row.queue_length}
                </TableCell>
                <TableCell className="tabular-nums">
                  {formatWaitMinutes(row.estimated_wait_seconds)}
                </TableCell>
                <TableCell>
                  <BusynessBadge level={row.busyness_level} />
                </TableCell>
                <TableCell className="tabular-nums">
                  {row.comfort_score != null
                    ? `${Math.round(row.comfort_score)}%`
                    : "—"}
                </TableCell>
                <TableCell className="tabular-nums">
                  {row.temperature_c != null
                    ? `${row.temperature_c.toFixed(1)}°C`
                    : "—"}
                </TableCell>
                <TableCell className="tabular-nums">
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
