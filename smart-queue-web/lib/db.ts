import { drizzle } from "drizzle-orm/d1"
import { getCloudflareContext } from "@opennextjs/cloudflare"

export async function getDb() {
  const { env } = await getCloudflareContext({ async: true })
  return drizzle((env as any).DB)
}
