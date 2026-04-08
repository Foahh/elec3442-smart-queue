import { getDb } from "@/lib/db"
import { listAllSiteStatus } from "@/lib/db/repositories"
import { mapSiteStatusRow } from "@/lib/server/site-records"

export const runtime = "edge"

export async function GET() {
  const db = await getDb()
  const rows = await listAllSiteStatus(db)
  const now = Date.now()
  const sites = rows.map((row) => mapSiteStatusRow(row, now))
  return Response.json({ sites })
}
