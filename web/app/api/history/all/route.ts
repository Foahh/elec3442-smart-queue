import { desc, gte } from "drizzle-orm"
import { getDb } from "@/lib/db"
import { siteSnapshots } from "@/lib/schema"
import { parseHistoryQuery } from "@/lib/server/history-query"
import { mapSnapshotRow } from "@/lib/server/site-records"

export const runtime = "edge"

export async function GET(request: Request) {
  const { minutes, limit } = parseHistoryQuery(request)

  const db = await getDb()

  const query = db
    .select()
    .from(siteSnapshots)
    .orderBy(desc(siteSnapshots.timestamp))
    .limit(limit)

  const rows =
    minutes > 0
      ? await query.where(
          gte(siteSnapshots.timestamp, Date.now() - minutes * 60_000)
        )
      : await query

  return Response.json({
    snapshots: rows.map(mapSnapshotRow),
  })
}
