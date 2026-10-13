-- TripsPayment table
-- Run this in the Supabase Dashboard SQL Editor
-- (Dashboard → SQL Editor → New query → paste → Run)

CREATE TABLE "TripsPayment" (
    "TransId" BIGSERIAL PRIMARY KEY,
    "TripId" INTEGER NOT NULL REFERENCES "trips"("tripid") ON DELETE CASCADE,
    "Paymentdate" DATE NOT NULL,
    "Amountowed" NUMERIC(10,2) NOT NULL,
    "Amountpayed" NUMERIC(10,2) NOT NULL,
    "Outstandingamount" NUMERIC(10,2) NOT NULL,
    "comments" TEXT
);

-- Allow access via the service role key (RLS is bypassed by service key,
-- but add a permissive policy so anon/publishable keys work too if needed)
ALTER TABLE "TripsPayment" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to TripsPayment" ON "TripsPayment"
    FOR ALL USING (true) WITH CHECK (true);
