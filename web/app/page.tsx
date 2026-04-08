"use client"

import { useEffect, useMemo, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { HistoryTable } from "@/components/history-table"
import { QueueChart } from "@/components/queue-chart"
import { SiteCard } from "@/components/site-card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useLiveDashboard, useSiteHistory } from "@/hooks/use-dashboard-queries"
import type { SiteStatus } from "@/lib/api"

function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme()

  const isDark = resolvedTheme === "dark"

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}

function DashboardHeader({
  lastUpdated,
  errorMessage,
}: {
  lastUpdated: Date | null
  errorMessage: string | null
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">Smart Queue Dashboard</h1>
        {lastUpdated && (
          <p className="text-sm text-muted-foreground">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}
        {errorMessage && (
          <p className="text-sm text-destructive">{errorMessage}</p>
        )}
      </div>
      <ThemeToggle />
    </div>
  )
}

function SiteGrid({
  sites,
  isPending,
}: {
  sites: SiteStatus[]
  isPending: boolean
}) {
  if (isPending && sites.length === 0) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        Loading sites…
      </p>
    )
  }

  if (sites.length === 0) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        No sites reporting yet. Configure QE_HUB_URL on a Pi to get started.
      </p>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sites.map((site) => (
        <SiteCard key={site.site_id} site={site} />
      ))}
    </div>
  )
}

function HistorySection({
  sites,
  selectedSite,
  onSelectSite,
}: {
  sites: SiteStatus[]
  selectedSite: string | null
  onSelectSite: (siteId: string) => void
}) {
  const historyQuery = useSiteHistory(selectedSite)
  const historySnapshots = historyQuery.data ?? []

  return (
    <div className="space-y-3 pt-2">
      <div className="flex flex-wrap gap-2">
        {sites.map((site) => (
          <Button
            key={site.site_id}
            variant={selectedSite === site.site_id ? "default" : "outline"}
            size="sm"
            onClick={() => onSelectSite(site.site_id)}
          >
            {site.display_name}
          </Button>
        ))}
      </div>

      {historyQuery.isError && (
        <p className="text-sm text-destructive">
          {historyQuery.error instanceof Error
            ? historyQuery.error.message
            : "Failed to load history"}
        </p>
      )}

      <HistoryTable snapshots={historySnapshots} />
    </div>
  )
}

export default function Page() {
  const [selectedSite, setSelectedSite] = useState<string | null>(null)

  const { data, isPending, isError, error, dataUpdatedAt } = useLiveDashboard()

  const sites = data?.sites ?? []
  const chartSnapshots = data?.chartSnapshots ?? []

  useEffect(() => {
    if (selectedSite || sites.length === 0) return
    setSelectedSite(sites[0].site_id)
  }, [selectedSite, sites])

  const lastUpdated = dataUpdatedAt > 0 ? new Date(dataUpdatedAt) : null

  const errorMessage =
    isError && error instanceof Error
      ? error.message
      : isError
        ? String(error)
        : null

  const siteNames = useMemo(
    () =>
      Object.fromEntries(
        sites.map((site) => [site.site_id, site.display_name])
      ),
    [sites]
  )

  const siteIds = useMemo(() => sites.map((site) => site.site_id), [sites])

  const hasSites = sites.length > 0

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <DashboardHeader lastUpdated={lastUpdated} errorMessage={errorMessage} />

      <SiteGrid sites={sites} isPending={isPending} />

      {hasSites && (
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

          <TabsContent value="history">
            <HistorySection
              sites={sites}
              selectedSite={selectedSite}
              onSelectSite={setSelectedSite}
            />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
