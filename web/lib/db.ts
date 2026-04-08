import { getCloudflareContext } from "@opennextjs/cloudflare"

export async function getCloudflareEnv() {
  const { env } = await getCloudflareContext({ async: true })
  return env
}

export async function getDb(): Promise<D1Database> {
  const env = await getCloudflareEnv()
  return env.DB
}
