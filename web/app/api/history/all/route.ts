import { desc, gte } from "drizzle-orm"
import { getDb } from "@/lib/db"
import { siteSnapshots } from "@/lib/schema"

export const runtime = "edge"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const minutes = Number(searchParams.get("minutes") ?? "60")
  const limit = Math.min(Number(searchParams.get("limit") ?? "500"), 1000)

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
    snapshots: rows.map((r) => ({
      id: r.id,
      site_id: r.siteId,
      timestamp: r.timestamp,
      queue_length: r.queueLength,
      estimated_wait_seconds: r.estimatedWaitSeconds,
      busyness_level: r.busynessLevel,
      comfort_score: r.comfortScore,
      temperature_c: r.temperatureC,
      humidity_pct: r.humidityPct,
      pressure_hpa: r.pressureHpa,
    })),
  })
}
