"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { HistoryTable } from "@/components/history-table"
import { QueueChart } from "@/components/queue-chart"
import { SiteCard } from "@/components/site-card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { Snapshot, SiteStatus } from "@/lib/api"
import { fetchHistory, fetchHistoryAll, fetchSites } from "@/lib/api"

export default function Page() {
  const { setTheme, resolvedTheme } = useTheme()
  const [sites, setSites] = useState<SiteStatus[]>([])
  const [chartSnapshots, setChartSnapshots] = useState<Snapshot[]>([])
  const [historySnapshots, setHistorySnapshots] = useState<Snapshot[]>([])
  const [selectedSite, setSelectedSite] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const historyFetchedFor = useRef<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [freshSites, freshChart] = await Promise.all([
        fetchSites(),
        fetchHistoryAll(60),
      ])
      setSites(freshSites)
      setChartSnapshots(freshChart)
      setLastUpdated(new Date())
      setError(null)
      if (!selectedSite && freshSites.length > 0) {
        setSelectedSite(freshSites[0].site_id)
      }
    } catch (e) {
      setError(String(e))
    }
  }, [selectedSite])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), 5000)
    return () => clearInterval(id)
  }, [refresh])

  useEffect(() => {
    if (!selectedSite || historyFetchedFor.current === selectedSite) return
    historyFetchedFor.current = selectedSite
    fetchHistory(selectedSite, 1440, 1000)
      .then(setHistorySnapshots)
      .catch(() => setHistorySnapshots([]))
  }, [selectedSite])

  const siteNames = Object.fromEntries(
    sites.map((s) => [s.site_id, s.display_name])
  )
  const siteIds = sites.map((s) => s.site_id)

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Smart Queue Dashboard</h1>
          {lastUpdated && (
            <p className="text-sm text-muted-foreground">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
        >
          {resolvedTheme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Live site cards */}
      {sites.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground">
          No sites reporting yet. Configure QE_HUB_URL on a Pi to get started.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sites.map((site) => (
            <SiteCard key={site.site_id} site={site} />
          ))}
        </div>
      )}

      {/* Chart + history */}
      {sites.length > 0 && (
        <Tabs defaultValue="chart">
          <TabsList>
            <TabsTrigger value="chart">Queue trend (60 min)</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="chart" className="pt-2">
            <QueueChart
              snapshots={chartSnapshots}
              siteIds={siteIds}
              siteNames={siteNames}
            />
          </TabsContent>

          <TabsContent value="history" className="space-y-3 pt-2">
            {/* Site selector */}
            <div className="flex flex-wrap gap-2">
              {sites.map((s) => (
                <Button
                  key={s.site_id}
                  variant={selectedSite === s.site_id ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    historyFetchedFor.current = null
                    setSelectedSite(s.site_id)
                  }}
                >
                  {s.display_name}
                </Button>
              ))}
            </div>
            <HistoryTable snapshots={historySnapshots} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
