import { drizzle } from "drizzle-orm/d1"
import { getCloudflareContext } from "@opennextjs/cloudflare"

export async function getCloudflareEnv() {
  const { env } = await getCloudflareContext({ async: true })
  return env
}

export async function getDb() {
  const env = await getCloudflareEnv()
  return drizzle(env.DB)
}
