import { getDb } from "@/lib/db"
import { siteStatus } from "@/lib/schema"
import { mapSiteStatusRow } from "@/lib/server/site-records"

export const runtime = "edge"

export async function GET() {
  const db = await getDb()
  const rows = await db.select().from(siteStatus)
  const now = Date.now()
  const sites = rows.map((row) => mapSiteStatusRow(row, now))
  return Response.json({ sites })
}
