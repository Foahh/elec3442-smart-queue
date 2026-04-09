import { getDb } from "@/lib/db"
import { listAllSnapshots } from "@/lib/db/repositories"
import { parseHistoryQuery } from "@/lib/server/history-query"
import { mapSnapshotRow } from "@/lib/server/site-records"

export async function GET(request: Request) {
  const { minutes, limit } = parseHistoryQuery(request)

  const db = await getDb()
  const sinceTs = minutes > 0 ? Date.now() - minutes * 60_000 : undefined

  const rows = await listAllSnapshots(db, { sinceTs, limit })

  return Response.json({
    snapshots: rows.map(mapSnapshotRow),
  })
}
