"use client"

import dynamic from "next/dynamic"
import { useEffect, useMemo, useState } from "react"
import { DashboardHeader } from "@/components/dashboard-header"
import { SiteGrid } from "@/components/site-grid"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useLiveDashboard } from "@/hooks/use-dashboard-queries"
import { getSiteIds, getSiteNameMap } from "@/lib/dashboard"
import type { SiteStatus, Snapshot } from "@/lib/types"

const EMPTY_SITES: SiteStatus[] = []
const EMPTY_SNAPSHOTS: Snapshot[] = []

const TabPanelFallback = () => (
  <div className="py-10 text-center text-sm text-muted-foreground">
    Loading…
  </div>
)

const QueueChart = dynamic(
  () =>
    import("@/components/queue-chart").then((m) => ({ default: m.QueueChart })),
  { loading: () => <TabPanelFallback /> }
)

const HistorySection = dynamic(
  () =>
    import("@/components/history-section").then((m) => ({
      default: m.HistorySection,
    })),
  { loading: () => <TabPanelFallback /> }
)

export function DashboardShell() {
  const [selectedSite, setSelectedSite] = useState<string | null>(null)

  const { data, isPending, isError, error, dataUpdatedAt } = useLiveDashboard()

  const sites = data?.sites ?? EMPTY_SITES
  const chartSnapshots = data?.chartSnapshots ?? EMPTY_SNAPSHOTS

  useEffect(() => {
    if (selectedSite && sites.some((site) => site.site_id === selectedSite)) {
      return
    }

    setSelectedSite(sites[0]?.site_id ?? null)
  }, [selectedSite, sites])

  const errorMessage =
    isError && error instanceof Error
      ? error.message
      : isError
        ? String(error)
        : null

  const siteNames = useMemo(() => getSiteNameMap(sites), [sites])
  const siteIds = useMemo(() => getSiteIds(sites), [sites])

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <DashboardHeader
        lastUpdatedAt={dataUpdatedAt > 0 ? dataUpdatedAt : null}
        errorMessage={errorMessage}
      />

      <SiteGrid sites={sites} isPending={isPending} />

      {sites.length > 0 && (
        <Tabs defaultValue="chart">
          <TabsList>
            <TabsTrigger value="chart">Trend</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="chart" className="mt-2">
            <QueueChart
              snapshots={chartSnapshots}
              siteIds={siteIds}
              siteNames={siteNames}
            />
          </TabsContent>

          <TabsContent value="history" className="mt-2">
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
