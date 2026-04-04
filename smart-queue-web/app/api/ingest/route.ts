import { eq, lt } from "drizzle-orm"
import { getDb } from "@/lib/db"
import { siteSnapshots, siteStatus } from "@/lib/schema"

export const runtime = "edge"

export async function POST(request: Request) {
  const apiKey = request.headers.get("x-api-key") ?? ""
  // getCloudflareContext is used inside getDb; access env for API_KEY separately
  const { getCloudflareContext } = await import("@opennextjs/cloudflare")
  const { env } = await getCloudflareContext({ async: true })

  if (!(env as any).API_KEY || apiKey !== (env as any).API_KEY) {
    return Response.json({ error: "Unauthorized" }, { status: 401 })
  }

  const body = await request.json() as {
    site_id: string
    display_name: string
    latitude?: number
    longitude?: number
    queue_length: number
    estimated_wait_seconds: number
    busyness_level: string
    comfort_score?: number
    sensors?: { temperature_c: number; humidity_pct: number; pressure_hpa: number }
    snapshot?: {
      timestamp: number
      queue_length: number
      estimated_wait_seconds: number
      busyness_level: string
      comfort_score?: number
    }
  }

  const db = await getDb()
  const now = Date.now()

  await db.insert(siteStatus).values({
    siteId: body.site_id,
    displayName: body.display_name,
    latitude: body.latitude ?? null,
    longitude: body.longitude ?? null,
    queueLength: body.queue_length,
    estimatedWaitSeconds: body.estimated_wait_seconds,
    busynessLevel: body.busyness_level,
    comfortScore: body.comfort_score ?? null,
    updatedAt: now,
    temperatureC: body.sensors?.temperature_c ?? null,
    humidityPct: body.sensors?.humidity_pct ?? null,
    pressureHpa: body.sensors?.pressure_hpa ?? null,
  }).onConflictDoUpdate({
    target: siteStatus.siteId,
    set: {
      displayName: body.display_name,
      latitude: body.latitude ?? null,
      longitude: body.longitude ?? null,
      queueLength: body.queue_length,
      estimatedWaitSeconds: body.estimated_wait_seconds,
      busynessLevel: body.busyness_level,
      comfortScore: body.comfort_score ?? null,
      updatedAt: now,
      temperatureC: body.sensors?.temperature_c ?? null,
      humidityPct: body.sensors?.humidity_pct ?? null,
      pressureHpa: body.sensors?.pressure_hpa ?? null,
    },
  })

  if (body.snapshot) {
    await db.insert(siteSnapshots).values({
      siteId: body.site_id,
      timestamp: body.snapshot.timestamp,
      queueLength: body.snapshot.queue_length,
      estimatedWaitSeconds: body.snapshot.estimated_wait_seconds,
      busynessLevel: body.snapshot.busyness_level,
      comfortScore: body.snapshot.comfort_score ?? null,
      temperatureC: body.sensors?.temperature_c ?? null,
      humidityPct: body.sensors?.humidity_pct ?? null,
      pressureHpa: body.sensors?.pressure_hpa ?? null,
    })
  }

  return Response.json({ ok: true })
}
