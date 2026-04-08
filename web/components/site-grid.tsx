import { SiteCard } from "@/components/site-card"
import type { SiteStatus } from "@/lib/types"

interface SiteGridProps {
  sites: SiteStatus[]
  isPending: boolean
}

export function SiteGrid({ sites, isPending }: SiteGridProps) {
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
        No sites reporting yet. Configure `QE_HUB_URL` on a Pi to get started.
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
