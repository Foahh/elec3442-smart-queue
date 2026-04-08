declare global {
  interface CloudflareEnv {
    API_KEY?: string
    DB: D1Database
  }
}

export {}
