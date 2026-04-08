import {
  index,
  integer,
  real,
  sqliteTable,
  text,
} from "drizzle-orm/sqlite-core"

export const siteStatus = sqliteTable("site_status", {
  siteId: text("site_id").primaryKey(),
  displayName: text("display_name").notNull(),
  latitude: real("latitude"),
  longitude: real("longitude"),
  queueLength: integer("queue_length").notNull(),
  estimatedWaitSeconds: real("estimated_wait_seconds").notNull(),
  busynessLevel: text("busyness_level").notNull(),
  comfortScore: real("comfort_score"),
  updatedAt: integer("updated_at").notNull(),
  temperatureC: real("temperature_c"),
  humidityPct: real("humidity_pct"),
  pressureHpa: real("pressure_hpa"),
})

export const siteSnapshots = sqliteTable(
  "site_snapshots",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    siteId: text("site_id").notNull(),
    timestamp: integer("timestamp").notNull(),
    queueLength: integer("queue_length").notNull(),
    estimatedWaitSeconds: real("estimated_wait_seconds").notNull(),
    busynessLevel: text("busyness_level").notNull(),
    comfortScore: real("comfort_score"),
    temperatureC: real("temperature_c"),
    humidityPct: real("humidity_pct"),
    pressureHpa: real("pressure_hpa"),
  },
  (t) => [index("idx_snapshots_site_time").on(t.siteId, t.timestamp)]
)
