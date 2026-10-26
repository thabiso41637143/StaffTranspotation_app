"""
Supabase client module for the Staff Transport app.

Wraps the Supabase REST API (PostgREST) and Auth API for all database
operations used by the Streamlit front-end.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

REST_URL = f"{SUPABASE_URL}/rest/v1"
AUTH_URL = f"{SUPABASE_URL}/auth/v1"

# Standard headers for PostgREST calls (service role key bypasses RLS)
def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _auth_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_profile_by_username(username: str):
    """Look up the Profiles table by username and return the matching row."""
    resp = requests.get(
        f"{REST_URL}/Profiles",
        headers=_headers(),
        params={"username": f"eq.{username}", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def sign_in_with_password(email: str, password: str):
    """
    Authenticate a user via the Supabase Auth API.

    Returns a dict with access_token and user info on success, or None on failure.
    """
    resp = requests.post(
        f"{AUTH_URL}/token?grant_type=password",
        headers=_auth_headers(),
        json={"email": email, "password": password},
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def driver_login(username: str, password: str):
    """
    Full driver login flow:
      1. Look up Profiles table to find the email for the username.
      2. Sign in via Supabase Auth with that email + password.

    Returns (profile_dict, auth_info) on success, (None, error_message) on failure.
    """
    profile = get_profile_by_username(username)
    if not profile:
        return None, "Username not found. Please check with your administrator."

    email = profile.get("email")
    if not email:
        return None, "No email associated with this driver account."

    auth_info = sign_in_with_password(email, password)
    if not auth_info:
        return None, "Invalid password. Please try again."

    return profile, auth_info


# ---------------------------------------------------------------------------
# Users (staff / passengers)
# ---------------------------------------------------------------------------

def get_user_by_staff_id(staff_id: str):
    """Return the user row matching the given staff_id (user_id column)."""
    resp = requests.get(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"user_id": f"eq.{staff_id}", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def get_all_passengers():
    """Return all users whose type is not 'Driver' (i.e. passengers / staff)."""
    resp = requests.get(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"type": "neq.Driver", "order": "user_number.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_all_drivers():
    """Return all users whose type is 'Driver'."""
    resp = requests.get(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"type": "eq.Driver", "order": "user_number.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_all_users():
    """Return every row in the users table."""
    resp = requests.get(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"order": "user_number.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def add_user(user_data: dict):
    """Insert a new user (staff member) into the users table."""
    resp = requests.post(
        f"{REST_URL}/users",
        headers=_headers(),
        json=user_data,
    )
    resp.raise_for_status()
    return resp.json()


def update_user(staff_id: str, updates: dict):
    """Update an existing user by staff_id."""
    resp = requests.patch(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"user_id": f"eq.{staff_id}"},
        json=updates,
    )
    resp.raise_for_status()
    return resp.json()


def delete_user(staff_id: str):
    """Delete a user by staff_id."""
    resp = requests.delete(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"user_id": f"eq.{staff_id}"},
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

def get_all_groups():
    """Return all groups ordered by groupid."""
    resp = requests.get(
        f"{REST_URL}/groups",
        headers=_headers(),
        params={"order": "groupid.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_group(group_id: int):
    """Return a single group by groupid."""
    resp = requests.get(
        f"{REST_URL}/groups",
        headers=_headers(),
        params={"groupid": f"eq.{group_id}", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def add_group(groupname: str, groupamount: float, group_abbr: str, comments: str = None):
    """Create a new group and return the created row."""
    # Get next groupid (groups table uses manual IDs, not BIGSERIAL)
    resp = requests.get(
        f"{REST_URL}/groups",
        headers=_headers(),
        params={"order": "groupid.desc", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    next_id = int(rows[0]["groupid"]) + 1 if rows else 1

    resp = requests.post(
        f"{REST_URL}/groups",
        headers=_headers(),
        json={
            "groupid": next_id,
            "groupname": groupname,
            "groupamount": groupamount,
            "groupAbrivation": group_abbr,
            "Comments": comments,
        },
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Trips
# ---------------------------------------------------------------------------

def get_trips_for_passenger(passid: str):
    """Return all trips for a passenger, ordered by trip date descending."""
    resp = requests.get(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"passid": f"eq.{passid}", "order": "tripdate.desc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_trips_for_driver(driverid: str):
    """Return all trips captured by a driver, ordered by trip date descending."""
    resp = requests.get(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"driverid": f"eq.{driverid}", "order": "tripdate.desc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_all_trips():
    """Return all trips, ordered by trip date descending."""
    resp = requests.get(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"order": "tripdate.desc"},
    )
    resp.raise_for_status()
    return resp.json()


def add_trip(trip_data: dict):
    """Insert a new trip record."""
    resp = requests.post(
        f"{REST_URL}/trips",
        headers=_headers(),
        json=trip_data,
    )
    resp.raise_for_status()
    return resp.json()


def update_trip(trip_id: int, updates: dict):
    """Update an existing trip by tripid."""
    resp = requests.patch(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"tripid": f"eq.{trip_id}"},
        json=updates,
    )
    resp.raise_for_status()
    return resp.json()


def delete_trip(trip_id: int):
    """Delete a trip by tripid."""
    resp = requests.delete(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"tripid": f"eq.{trip_id}"},
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Trip Price (custom per-user rates)
# ---------------------------------------------------------------------------

def get_trip_price_for_user(user_id: str):
    """Return the custom trip price row for a user, if one exists."""
    resp = requests.get(
        f"{REST_URL}/TripPrice",
        headers=_headers(),
        params={"user_id": f"eq.{user_id}", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def add_trip_price(user_id: str, group_id: int, trip_rate: float):
    """Insert a trip price record for a user into the TripPrice table."""
    resp = requests.post(
        f"{REST_URL}/TripPrice",
        headers=_headers(),
        json={
            "user_id": user_id,
            "group_id": group_id,
            "trip_rate": trip_rate,
        },
    )
    resp.raise_for_status()
    return resp.json()


def upsert_trip_price(user_id: str, group_id: int, trip_rate: float):
    """Insert or update the trip price for a user."""
    existing = get_trip_price_for_user(user_id)
    if existing:
        resp = requests.patch(
            f"{REST_URL}/TripPrice",
            headers=_headers(),
            params={"user_id": f"eq.{user_id}"},
            json={"trip_rate": trip_rate, "group_id": group_id},
        )
        resp.raise_for_status()
        return resp.json()
    else:
        return add_trip_price(user_id, group_id, trip_rate)


def get_trip_rate(user_id: str, group_id: int = None):
    """
    Determine the trip rate for a user.

    Priority:
      1. Custom TripPrice row for the user.
      2. Group's groupamount (default rate for the group).
      3. Fallback 20.0 if nothing is found.
    """
    # 1. Check for a custom per-user rate
    custom = get_trip_price_for_user(user_id)
    if custom and custom.get("trip_rate") is not None:
        return float(custom["trip_rate"])

    # 2. Fall back to the group's default amount
    if group_id is not None:
        group = get_group(group_id)
        if group and group.get("groupamount") is not None:
            return float(group["groupamount"])

    # 3. Ultimate fallback
    return 20.0


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def get_payments_for_passenger(passid: str):
    """Return all payments for a passenger, ordered by payment date descending."""
    resp = requests.get(
        f"{REST_URL}/payment",
        headers=_headers(),
        params={"passid": f"eq.{passid}", "order": "paydate.desc"},
    )
    resp.raise_for_status()
    return resp.json()


def add_payment(payment_data: dict):
    """Insert a new payment record."""
    resp = requests.post(
        f"{REST_URL}/payment",
        headers=_headers(),
        json=payment_data,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calculate_amount_owed(passid: str):
    """
    Calculate the total amount owed by a passenger.

    Amount owed = (sum of tripamount for all trips) - (sum of amountpayed for all payments)
    """
    trips = get_trips_for_passenger(passid)
    total_trips_amount = sum(float(t.get("tripamount") or 0) for t in trips)

    payments = get_payments_for_passenger(passid)
    total_paid = sum(float(p.get("amountpayed") or 0) for p in payments)

    return total_trips_amount, total_paid, total_trips_amount - total_paid


def get_next_user_number():
    """Get the next available user_number by querying the max value."""
    resp = requests.get(
        f"{REST_URL}/users",
        headers=_headers(),
        params={"order": "user_number.desc", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows and rows[0].get("user_number") is not None:
        return int(rows[0]["user_number"]) + 1
    return 1


def generate_staff_id(abbreviation: str):
    """
    Generate the next staff ID for a group based on its abbreviation.

    Pattern: {abbreviation}{number} where the number starts at 1001
    and increments based on existing user_ids.
    e.g. ABS1001, ABS1002, ... or FB1001, FB1002, ...
    """
    all_users = get_all_users()

    max_num = 1000
    for user in all_users:
        uid = user.get("user_id", "")
        if uid.startswith(abbreviation):
            num_part = uid[len(abbreviation):]
            try:
                num = int(num_part)
                if num > max_num:
                    max_num = num
            except ValueError:
                continue

    return f"{abbreviation}{max_num + 1}"


# ---------------------------------------------------------------------------
# Bulk loaders (for caching in the app layer)
# ---------------------------------------------------------------------------

def get_all_trip_prices():
    """Return all TripPrice records."""
    resp = requests.get(
        f"{REST_URL}/TripPrice",
        headers=_headers(),
        params={"order": "id.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_all_accounts():
    """Return all account records."""
    resp = requests.get(
        f"{REST_URL}/account",
        headers=_headers(),
        params={"order": "account_number.asc"},
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# TripsPayment (per-trip payment transactions)
# ---------------------------------------------------------------------------

def add_trips_payment(data: dict):
    """Insert a TripsPayment record."""
    resp = requests.post(
        f"{REST_URL}/TripsPayment",
        headers=_headers(),
        json=data,
    )
    resp.raise_for_status()
    return resp.json()


def get_trips_payments_for_trip(trip_id: int):
    """Return all TripsPayment records for a specific trip."""
    resp = requests.get(
        f"{REST_URL}/TripsPayment",
        headers=_headers(),
        params={"TripId": f"eq.{trip_id}", "order": "TransId.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def get_trips_payments_for_passenger(passid: str):
    """Return all TripsPayment records for a passenger's trips."""
    trips = get_trips_for_passenger(passid)
    trip_ids = [t["tripid"] for t in trips]
    if not trip_ids:
        return []

    trip_id_filter = "(" + ",".join(str(tid) for tid in trip_ids) + ")"
    resp = requests.get(
        f"{REST_URL}/TripsPayment",
        headers=_headers(),
        params={"TripId": f"in.{trip_id_filter}", "order": "Paymentdate.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def delete_trips_payments_for_trip(trip_id: int):
    """Delete all TripsPayment records for a specific trip."""
    resp = requests.delete(
        f"{REST_URL}/TripsPayment",
        headers=_headers(),
        params={"TripId": f"eq.{trip_id}"},
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def get_account_for_user(user_id: str):
    """Return the account row for a user, or None."""
    resp = requests.get(
        f"{REST_URL}/account",
        headers=_headers(),
        params={"user_id": f"eq.{user_id}", "limit": "1"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def create_account(user_id: str):
    """Create a new account with balance 0 for a user."""
    # Try with comments field first; fall back without it if the column doesn't exist.
    for payload in [
        {"user_id": user_id, "balance": 0, "comments": None},
        {"user_id": user_id, "balance": 0},
    ]:
        resp = requests.post(
            f"{REST_URL}/account",
            headers=_headers(),
            json=payload,
        )
        if resp.status_code != 400:
            break
    resp.raise_for_status()
    return resp.json()


def get_or_create_account(user_id: str):
    """Get the account for a user, or create one if it doesn't exist."""
    account = get_account_for_user(user_id)
    if not account:
        account = create_account(user_id)
    return account


def update_account_balance(user_id: str, balance: float):
    """Update the account balance for a user."""
    resp = requests.patch(
        f"{REST_URL}/account",
        headers=_headers(),
        params={"user_id": f"eq.{user_id}"},
        json={"balance": balance},
    )
    resp.raise_for_status()
    return resp.json()


def update_account_balance_for_user(user_id: str):
    """Recalculate and update the account balance from trips and payments."""
    trips = get_trips_for_passenger(user_id)
    payments = get_payments_for_passenger(user_id)
    total_trips = sum(float(t.get("tripamount") or 0) for t in trips)
    total_paid = sum(float(p.get("amountpayed") or 0) for p in payments)
    new_balance = total_paid - total_trips
    update_account_balance(user_id, new_balance)
    return new_balance


# ---------------------------------------------------------------------------
# Payment management
# ---------------------------------------------------------------------------

def get_all_payments():
    """Return all payment records ordered by date descending."""
    resp = requests.get(
        f"{REST_URL}/payment",
        headers=_headers(),
        params={"order": "paydate.desc"},
    )
    resp.raise_for_status()
    return resp.json()


def update_payment_record(payid: int, updates: dict):
    """Update a payment record by payid."""
    resp = requests.patch(
        f"{REST_URL}/payment",
        headers=_headers(),
        params={"payid": f"eq.{payid}"},
        json=updates,
    )
    resp.raise_for_status()
    return resp.json()


def recalculate_trip_payments(passid: str):
    """
    Recalculate all trip payments for a passenger from scratch.

    1. Gets all trips (oldest first) and all payments (oldest first)
    2. Deletes all TripsPayment records for the passenger's trips
    3. Resets all trip statuses to "Unpaid"
    4. Distributes payments across trips (oldest payment to oldest trip)
    5. Creates TripsPayment records
    6. Updates trip statuses to "Paid" or "partially paid"
    7. Updates account balance
    """
    # Get trips ordered by date ASC (oldest first)
    resp = requests.get(
        f"{REST_URL}/trips",
        headers=_headers(),
        params={"passid": f"eq.{passid}", "order": "tripdate.asc,tripid.asc"},
    )
    resp.raise_for_status()
    trips = resp.json()

    # Get payments ordered by date ASC (oldest first)
    resp = requests.get(
        f"{REST_URL}/payment",
        headers=_headers(),
        params={"passid": f"eq.{passid}", "order": "paydate.asc,payid.asc"},
    )
    resp.raise_for_status()
    payments = resp.json()

    # Delete all TripsPayment records and reset trip statuses
    trip_outstanding = {}
    for trip in trips:
        trip_id = trip["tripid"]
        delete_trips_payments_for_trip(trip_id)
        update_trip(trip_id, {"tripstatus": "Unpaid"})
        trip_outstanding[trip_id] = float(trip.get("tripamount") or 0)

    # Distribute payments across trips
    for payment in payments:
        remaining = float(payment.get("amountpayed") or 0)
        paydate = payment.get("paydate")

        for trip in trips:
            if remaining <= 0:
                break

            trip_id = trip["tripid"]
            outstanding = trip_outstanding.get(trip_id, 0)

            if outstanding <= 0:
                continue  # This trip is fully paid

            pay_amount = min(remaining, outstanding)
            new_outstanding = outstanding - pay_amount
            trip_outstanding[trip_id] = new_outstanding

            trip_amount = float(trip.get("tripamount") or 0)
            add_trips_payment({
                "TripId": trip_id,
                "Paymentdate": str(paydate) if paydate else None,
                "Amountowed": trip_amount,
                "Amountpayed": pay_amount,
                "Outstandingamount": new_outstanding,
                "comments": None,
            })

            if new_outstanding <= 0:
                update_trip(trip_id, {"tripstatus": "Paid"})
            else:
                update_trip(trip_id, {"tripstatus": "partially paid"})

            remaining -= pay_amount

    # Update account balance
    total_trips = sum(float(t.get("tripamount") or 0) for t in trips)
    total_paid = sum(float(p.get("amountpayed") or 0) for p in payments)
    new_balance = total_paid - total_trips
    update_account_balance(passid, new_balance)


def capture_payment(passid: str, driverid: str, amount: float, paydate, comments: str = None):
    """Capture a payment for a passenger and recalculate trip payments."""
    payment_data = {
        "driverid": driverid,
        "passid": passid,
        "paydate": str(paydate),
        "amountpayed": amount,
        "Comments": comments,
    }
    add_payment(payment_data)
    recalculate_trip_payments(passid)


def edit_payment(payid: int, passid: str, amount: float, paydate, comments: str = None):
    """Edit a payment and recalculate trip payments."""
    updates = {
        "amountpayed": amount,
        "paydate": str(paydate),
        "Comments": comments,
    }
    update_payment_record(payid, updates)
    recalculate_trip_payments(passid)


# ---------------------------------------------------------------------------
# GroupAccess — controls which groups a driver can access
# ---------------------------------------------------------------------------

def get_all_group_access():
    """Return all GroupAccess records."""
    resp = requests.get(
        f"{REST_URL}/GroupAccess",
        headers=_headers(),
        params={"order": "id.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def add_group_access(driverid: str, groupid: int):
    """Assign a driver to a group."""
    resp = requests.post(
        f"{REST_URL}/GroupAccess",
        headers=_headers(),
        json={"driverid": driverid, "groupid": groupid},
    )
    resp.raise_for_status()
    return resp.json()


def remove_group_access(driverid: str, groupid: int):
    """Remove a driver's access to a group."""
    resp = requests.delete(
        f"{REST_URL}/GroupAccess",
        headers=_headers(),
        params={"driverid": f"eq.{driverid}", "groupid": f"eq.{groupid}"},
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# DriverAvailability — dates a driver is NOT available
# ---------------------------------------------------------------------------

def get_all_driver_availability():
    """Return all DriverAvailability records."""
    resp = requests.get(
        f"{REST_URL}/DriverAvailability",
        headers=_headers(),
        params={"order": "unavailable_date.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def add_driver_unavailable(driverid: str, unavailable_date, reason: str = None):
    """Mark a driver as unavailable on a specific date."""
    resp = requests.post(
        f"{REST_URL}/DriverAvailability",
        headers=_headers(),
        json={
            "driverid": driverid,
            "unavailable_date": str(unavailable_date),
            "reason": reason,
        },
    )
    resp.raise_for_status()
    return resp.json()


def remove_driver_unavailable(driverid: str, unavailable_date):
    """Remove a driver's unavailable date."""
    resp = requests.delete(
        f"{REST_URL}/DriverAvailability",
        headers=_headers(),
        params={
            "driverid": f"eq.{driverid}",
            "unavailable_date": f"eq.{str(unavailable_date)}",
        },
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# GroupSchedule — knock-off times per group per day of week
# ---------------------------------------------------------------------------

def get_all_group_schedules():
    """Return all GroupSchedule records."""
    resp = requests.get(
        f"{REST_URL}/GroupSchedule",
        headers=_headers(),
        params={"order": "group_id.asc,day_of_week.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def upsert_group_schedule(group_id: int, day_of_week: int, knockoff_time: str):
    """Insert or update a group's knock-off time for a specific day."""
    # Check if record exists
    resp = requests.get(
        f"{REST_URL}/GroupSchedule",
        headers=_headers(),
        params={
            "group_id": f"eq.{group_id}",
            "day_of_week": f"eq.{day_of_week}",
            "limit": "1",
        },
    )
    resp.raise_for_status()
    existing = resp.json()

    if existing:
        # Update
        resp = requests.patch(
            f"{REST_URL}/GroupSchedule",
            headers=_headers(),
            params={
                "group_id": f"eq.{group_id}",
                "day_of_week": f"eq.{day_of_week}",
            },
            json={"knockoff_time": knockoff_time},
        )
        resp.raise_for_status()
        return resp.json()
    else:
        # Insert
        resp = requests.post(
            f"{REST_URL}/GroupSchedule",
            headers=_headers(),
            json={
                "group_id": group_id,
                "day_of_week": day_of_week,
                "knockoff_time": knockoff_time,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# PassengerSchedule — individual knock-off times (overrides group default)
# ---------------------------------------------------------------------------

def get_all_passenger_schedules():
    """Return all PassengerSchedule records."""
    resp = requests.get(
        f"{REST_URL}/PassengerSchedule",
        headers=_headers(),
        params={"order": "user_id.asc,day_of_week.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def upsert_passenger_schedule(user_id: str, day_of_week: int, knockoff_time: str):
    """Insert or update a passenger's knock-off time for a specific day."""
    # Check if record exists
    resp = requests.get(
        f"{REST_URL}/PassengerSchedule",
        headers=_headers(),
        params={
            "user_id": f"eq.{user_id}",
            "day_of_week": f"eq.{day_of_week}",
            "limit": "1",
        },
    )
    resp.raise_for_status()
    existing = resp.json()

    if existing:
        resp = requests.patch(
            f"{REST_URL}/PassengerSchedule",
            headers=_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "day_of_week": f"eq.{day_of_week}",
            },
            json={"knockoff_time": knockoff_time},
        )
        resp.raise_for_status()
        return resp.json()
    else:
        resp = requests.post(
            f"{REST_URL}/PassengerSchedule",
            headers=_headers(),
            json={
                "user_id": user_id,
                "day_of_week": day_of_week,
                "knockoff_time": knockoff_time,
            },
        )
        resp.raise_for_status()
        return resp.json()


def delete_passenger_schedule(user_id: str, day_of_week: int):
    """Delete a passenger's knock-off time for a specific day (revert to group default)."""
    resp = requests.delete(
        f"{REST_URL}/PassengerSchedule",
        headers=_headers(),
        params={
            "user_id": f"eq.{user_id}",
            "day_of_week": f"eq.{day_of_week}",
        },
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# DriverWeeklyAvailability — driver's recurring weekly availability per day
# ---------------------------------------------------------------------------

def get_all_driver_weekly_availability():
    """Return all DriverWeeklyAvailability records."""
    resp = requests.get(
        f"{REST_URL}/DriverWeeklyAvailability",
        headers=_headers(),
        params={"order": "driverid.asc,day_of_week.asc"},
    )
    resp.raise_for_status()
    return resp.json()


def delete_driver_weekly_availability_for_driver(driverid: str):
    """Delete ALL DriverWeeklyAvailability rows for a driver (full schedule reset)."""
    resp = requests.delete(
        f"{REST_URL}/DriverWeeklyAvailability",
        headers=_headers(),
        params={"driverid": f"eq.{driverid}"},
    )
    resp.raise_for_status()


def upsert_driver_weekly_availability(
    driverid: str,
    day_of_week: int,
    available: bool,
    time_from: str = None,
    time_to: str = None,
    comments: str = None,
    group_id: int = None,
    week_start: str = None,
):
    """Insert or update a driver's weekly availability for a specific day.

    group_id=None means the record applies to ALL of the driver's groups.
    week_start (ISO date string, e.g. '2026-10-26') scopes the record to a
    specific calendar week so old weeks don't bleed into new ones.
    When available=True the time_from/time_to/comments fields are cleared.

    Falls back to a simpler payload if optional columns don't exist yet.
    """
    # Build the full payload
    full_payload = {
        "available": available,
        "time_from": time_from if not available else None,
        "time_to":   time_to   if not available else None,
        "comments":  comments  if not available else None,
        "group_id":  group_id,
    }
    if week_start is not None:
        full_payload["week_start"] = week_start

    # Minimal payload used as fallback when extra columns don't exist yet
    minimal_payload = {"available": available}

    # Build lookup params — match on (driverid, day_of_week, group_id)
    lookup_params = {
        "driverid":    f"eq.{driverid}",
        "day_of_week": f"eq.{day_of_week}",
        "limit": "1",
    }
    if group_id is not None:
        lookup_params["group_id"] = f"eq.{group_id}"
    else:
        lookup_params["group_id"] = "is.null"

    resp = requests.get(
        f"{REST_URL}/DriverWeeklyAvailability",
        headers=_headers(),
        params=lookup_params,
    )
    resp.raise_for_status()
    existing = resp.json()

    # Filter params for PATCH / DELETE
    filter_params = {
        "driverid":    f"eq.{driverid}",
        "day_of_week": f"eq.{day_of_week}",
        "group_id":    f"eq.{group_id}" if group_id is not None else "is.null",
    }

    def _do_write(payload):
        if existing:
            r = requests.patch(
                f"{REST_URL}/DriverWeeklyAvailability",
                headers=_headers(),
                params=filter_params,
                json=payload,
            )
        else:
            insert_body = {"driverid": driverid, "day_of_week": day_of_week, **payload}
            if group_id is not None:
                insert_body["group_id"] = group_id
            r = requests.post(
                f"{REST_URL}/DriverWeeklyAvailability",
                headers=_headers(),
                json=insert_body,
            )
        return r

    resp = _do_write(full_payload)
    if resp.status_code == 400:
        # Extra columns (time_from/time_to/comments/group_id/week_start) likely
        # don't exist yet — retry with a simple availability-only write.
        simple_params = {"driverid": f"eq.{driverid}", "day_of_week": f"eq.{day_of_week}"}
        if existing:
            resp = requests.patch(
                f"{REST_URL}/DriverWeeklyAvailability",
                headers=_headers(),
                params=simple_params,
                json=minimal_payload,
            )
        else:
            resp = requests.post(
                f"{REST_URL}/DriverWeeklyAvailability",
                headers=_headers(),
                json={"driverid": driverid, "day_of_week": day_of_week, **minimal_payload},
            )
    resp.raise_for_status()
    return resp.json()
    """Delete ALL PassengerSchedule rows for a passenger (full schedule reset)."""
    resp = requests.delete(
        f"{REST_URL}/PassengerSchedule",
        headers=_headers(),
        params={"user_id": f"eq.{user_id}"},
    )
    resp.raise_for_status()
