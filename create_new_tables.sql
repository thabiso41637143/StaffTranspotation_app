-- Group Access Control, Driver Availability, and Schedule tables
-- Run this in the Supabase Dashboard SQL Editor
-- (Dashboard → SQL Editor → New query → paste → Run)

-- 1. GroupAccess — controls which groups each driver can access
CREATE TABLE "GroupAccess" (
    "id" BIGSERIAL PRIMARY KEY,
    "driverid" VARCHAR NOT NULL,
    "groupid" BIGINT NOT NULL REFERENCES "groups"("groupid") ON DELETE CASCADE,
    "created_at" TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE("driverid", "groupid")
);

-- 2. DriverAvailability — dates a driver is NOT available
CREATE TABLE "DriverAvailability" (
    "id" BIGSERIAL PRIMARY KEY,
    "driverid" VARCHAR NOT NULL,
    "unavailable_date" DATE NOT NULL,
    "reason" TEXT,
    "created_at" TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE("driverid", "unavailable_date")
);

-- 3. GroupSchedule — knock-off times per group per day of week (0=Mon … 6=Sun)
CREATE TABLE "GroupSchedule" (
    "id" BIGSERIAL PRIMARY KEY,
    "group_id" BIGINT NOT NULL REFERENCES "groups"("groupid") ON DELETE CASCADE,
    "day_of_week" INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    "knockoff_time" TIME NOT NULL,
    UNIQUE("group_id", "day_of_week")
);

-- 4. PassengerSchedule — individual knock-off times (overrides group default)
CREATE TABLE "PassengerSchedule" (
    "id" BIGSERIAL PRIMARY KEY,
    "user_id" VARCHAR NOT NULL,
    "day_of_week" INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    "knockoff_time" TIME NOT NULL,
    UNIQUE("user_id", "day_of_week")
);

-- 5. DriverWeeklyAvailability — driver's recurring weekly availability per day of week
CREATE TABLE "DriverWeeklyAvailability" (
    "id" BIGSERIAL PRIMARY KEY,
    "driverid" VARCHAR NOT NULL,
    "day_of_week" INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    "available" BOOLEAN NOT NULL DEFAULT TRUE,
    "created_at" TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE("driverid", "day_of_week")
);

-- Enable RLS + permissive policies (service-role key bypasses RLS anyway)
ALTER TABLE "GroupAccess" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all GroupAccess" ON "GroupAccess" FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE "DriverAvailability" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all DriverAvailability" ON "DriverAvailability" FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE "GroupSchedule" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all GroupSchedule" ON "GroupSchedule" FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE "PassengerSchedule" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all PassengerSchedule" ON "PassengerSchedule" FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE "DriverWeeklyAvailability" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all DriverWeeklyAvailability" ON "DriverWeeklyAvailability" FOR ALL USING (true) WITH CHECK (true);
