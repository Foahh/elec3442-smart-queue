import { and, desc, eq, gte } from "drizzle-orm"
import { getDb } from "@/lib/db"
import { siteSnapshots } from "@/lib/schema"
import { parseHistoryQuery } from "@/lib/server/history-query"
import { mapSnapshotRow } from "@/lib/server/site-records"

export const runtime = "edge"

export async function GET(request: Request) {
  const { siteId, minutes, limit } = parseHistoryQuery(request)

  if (!siteId)
    return Response.json({ error: "site_id required" }, { status: 400 })

  const db = await getDb()

  const conditions = [eq(siteSnapshots.siteId, siteId)]
  if (minutes > 0) {
    conditions.push(gte(siteSnapshots.timestamp, Date.now() - minutes * 60_000))
  }

  const rows = await db
    .select()
    .from(siteSnapshots)
    .where(and(...conditions))
    .orderBy(desc(siteSnapshots.timestamp))
    .limit(limit)

  return Response.json({
    snapshots: rows.map(mapSnapshotRow),
  })
}
