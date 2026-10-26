-- Migration: add week_start column to DriverWeeklyAvailability
-- Run this once in the Supabase SQL editor.
--
-- The column stores the Monday date of the week the schedule applies to.
-- Existing rows get NULL (treated as "legacy / current week" by the app
-- until the driver next saves their schedule).

ALTER TABLE "DriverWeeklyAvailability"
    ADD COLUMN IF NOT EXISTS week_start DATE;

-- Optional index to speed up week-scoped lookups
CREATE INDEX IF NOT EXISTS idx_drv_avail_week
    ON "DriverWeeklyAvailability" (driverid, week_start);
