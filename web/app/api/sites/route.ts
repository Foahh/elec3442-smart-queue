import { getDb } from "@/lib/db"
import { siteStatus } from "@/lib/schema"

export const runtime = "edge"

export async function GET() {
  const db = await getDb()
  const rows = await db.select().from(siteStatus)
  const now = Date.now()
  const sites = rows.map((r) => ({
    site_id: r.siteId,
    display_name: r.displayName,
    latitude: r.latitude,
    longitude: r.longitude,
    queue_length: r.queueLength,
    estimated_wait_seconds: r.estimatedWaitSeconds,
    busyness_level: r.busynessLevel,
    comfort_score: r.comfortScore,
    updated_at: r.updatedAt,
    stale: now - r.updatedAt > 30_000,
    temperature_c: r.temperatureC,
    humidity_pct: r.humidityPct,
    pressure_hpa: r.pressureHpa,
  }))
  return Response.json({ sites })
}
