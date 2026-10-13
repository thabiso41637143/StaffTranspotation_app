-- Migration: Add time_from, time_to, comments, group_id to DriverWeeklyAvailability
-- Run in Supabase Dashboard → SQL Editor

ALTER TABLE "DriverWeeklyAvailability"
    ADD COLUMN IF NOT EXISTS "time_from" TIME,
    ADD COLUMN IF NOT EXISTS "time_to"   TIME,
    ADD COLUMN IF NOT EXISTS "comments"  TEXT,
    ADD COLUMN IF NOT EXISTS "group_id"  BIGINT REFERENCES "groups"("groupid") ON DELETE CASCADE;

-- Drop the old unique constraint and replace with one that includes group_id.
-- NULL group_id means "applies to all groups" (PostgreSQL treats NULLs as
-- distinct in UNIQUE constraints, so we use a partial unique index instead).
ALTER TABLE "DriverWeeklyAvailability"
    DROP CONSTRAINT IF EXISTS "DriverWeeklyAvailability_driverid_day_of_week_key";

-- Unique index: one row per (driverid, day_of_week) when group_id IS NULL
CREATE UNIQUE INDEX IF NOT EXISTS "drv_avail_all_groups_udx"
    ON "DriverWeeklyAvailability" ("driverid", "day_of_week")
    WHERE "group_id" IS NULL;

-- Unique index: one row per (driverid, day_of_week, group_id) for specific groups
CREATE UNIQUE INDEX IF NOT EXISTS "drv_avail_per_group_udx"
    ON "DriverWeeklyAvailability" ("driverid", "day_of_week", "group_id")
    WHERE "group_id" IS NOT NULL;
