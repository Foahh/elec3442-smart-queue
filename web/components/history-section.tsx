"use client"

import { HistoryTable } from "@/components/history-table"
import { Button } from "@/components/ui/button"
import { useSiteHistory } from "@/hooks/use-dashboard-queries"
import type { SiteStatus } from "@/lib/types"

interface HistorySectionProps {
  sites: SiteStatus[]
  selectedSite: string | null
  onSelectSite: (siteId: string) => void
}

export function HistorySection({
  sites,
  selectedSite,
  onSelectSite,
}: HistorySectionProps) {
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
