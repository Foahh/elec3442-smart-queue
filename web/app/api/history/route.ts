import { getDb } from "@/lib/db"
import { listSnapshotsForSite } from "@/lib/db/repositories"
import { parseHistoryQuery } from "@/lib/server/history-query"
import { mapSnapshotRow } from "@/lib/server/site-records"

export async function GET(request: Request) {
  const { siteId, minutes, limit } = parseHistoryQuery(request)

  if (!siteId)
    return Response.json({ error: "site_id required" }, { status: 400 })

  const db = await getDb()
  const sinceTs = minutes > 0 ? Date.now() - minutes * 60_000 : undefined

  const rows = await listSnapshotsForSite(db, siteId, {
    sinceTs,
    limit,
  })

  return Response.json({
    snapshots: rows.map(mapSnapshotRow),
  })
}
