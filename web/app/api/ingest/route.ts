import { getCloudflareEnv, getDb } from "@/lib/db"
import { siteSnapshots, siteStatus } from "@/lib/schema"
import {
  buildSiteStatusValues,
  buildSiteStatusUpdateValues,
  buildSnapshotValues,
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
  const siteStatusValues = buildSiteStatusValues(body, now)
  const siteStatusUpdateValues = buildSiteStatusUpdateValues(body, now)

  await db.insert(siteStatus).values(siteStatusValues).onConflictDoUpdate({
    target: siteStatus.siteId,
    set: siteStatusUpdateValues,
  })

  const snapshotValues = buildSnapshotValues(body)
  if (snapshotValues) {
    await db.insert(siteSnapshots).values(snapshotValues)
  }

  return Response.json({ ok: true })
}
