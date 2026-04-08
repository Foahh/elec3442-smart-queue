CREATE TABLE `site_snapshots` (
	`id` integer PRIMARY KEY AUTOINCREMENT,
	`site_id` text NOT NULL,
	`timestamp` integer NOT NULL,
	`queue_length` integer NOT NULL,
	`estimated_wait_seconds` real NOT NULL,
	`busyness_level` text NOT NULL,
	`comfort_score` real,
	`temperature_c` real,
	`humidity_pct` real,
	`pressure_hpa` real
);
--> statement-breakpoint
CREATE TABLE `site_status` (
	`site_id` text PRIMARY KEY,
	`display_name` text NOT NULL,
	`latitude` real,
	`longitude` real,
	`queue_length` integer NOT NULL,
	`estimated_wait_seconds` real NOT NULL,
	`busyness_level` text NOT NULL,
	`comfort_score` real,
	`updated_at` integer NOT NULL,
	`temperature_c` real,
	`humidity_pct` real,
	`pressure_hpa` real
);
--> statement-breakpoint
CREATE INDEX `idx_snapshots_site_time` ON `site_snapshots` (`site_id`,`timestamp`);