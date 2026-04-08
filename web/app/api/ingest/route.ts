import { getCloudflareEnv, getDb } from "@/lib/db"
import { insertSiteSnapshot, upsertSiteStatus } from "@/lib/db/repositories"
import {
  buildSiteStatusRow,
  buildSnapshotInsertRow,
} from "@/lib/server/site-records"
import type { IngestPayload } from "@/lib/types"

export const runtime = "edge"

export async function POST(request: Request) {
  const apiKey = request.headers.get("x-api-key") ?? ""
  const env = await getCloudflareEnv()

  if (!env.API_KEY || apiKey !== env.API_KEY) {
    return Response.json({ error: "Unauthorized" }, { status: 401 })
  }

  const body = (await request.json()) as IngestPayload

  const db = await getDb()
  const now = Date.now()
  await upsertSiteStatus(db, buildSiteStatusRow(body, now))

  const snapshotRow = buildSnapshotInsertRow(body)
  if (snapshotRow) {
    await insertSiteSnapshot(db, snapshotRow)
  }

  return Response.json({ ok: true })
}
