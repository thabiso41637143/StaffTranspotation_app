"""
Staff Transport Register - Streamlit App
=========================================

A staff transportation register that tracks trips between home and work.

  * Passengers look up their travel history and amount owed using their Staff ID.
  * Drivers log in with username + password, then manage passengers and trips.

Database: Supabase (PostgreSQL via REST API)
"""

import streamlit as st
from datetime import date, datetime, timedelta

import supabase_client as db


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Staff Transport Register",
    page_icon="🚐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
if "role" not in st.session_state:
    st.session_state.role = None        # "passenger" or "driver"
if "driver_logged_in" not in st.session_state:
    st.session_state.driver_logged_in = False
if "driver_profile" not in st.session_state:
    st.session_state.driver_profile = None
if "driver_user" not in st.session_state:
    st.session_state.driver_user = None
if "passenger_lookup_id" not in st.session_state:
    st.session_state.passenger_lookup_id = None  # staff_id of looked-up passenger


def reset_session():
    """Clear all session state and return to the landing page."""
    st.session_state.role = None
    st.session_state.driver_logged_in = False
    st.session_state.driver_profile = None
    st.session_state.driver_user = None
    st.session_state.passenger_lookup_id = None
    st.rerun()


def render_table(rows, empty_msg="No data to display."):
    """
    Render a list of dicts as a markdown table.

    Uses st.markdown() instead of st.dataframe() to avoid importing
    pandas/pyarrow, which can fail on systems with Application Control
    policies that block native DLLs.
    """
    if not rows:
        st.info(empty_msg)
        return

    headers = list(rows[0].keys())
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    md_lines = [header_row, separator]
    for row in rows:
        cells = []
        for h in headers:
            val = str(row.get(h, ""))
            val = val.replace("|", "\\|")  # escape pipe chars
            cells.append(val)
        md_lines.append("| " + " | ".join(cells) + " |")

    st.markdown("\n".join(md_lines))


# ---------------------------------------------------------------------------
# Cached data layer — pre-loads bulk data to minimize API calls.
# Uses st.cache_data (TTL 60s). After any write operation, call
# clear_data_cache() to force a fresh load on the next rerun.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _load_passengers():
    return db.get_all_passengers()

@st.cache_data(ttl=60, show_spinner=False)
def _load_groups():
    return db.get_all_groups()

@st.cache_data(ttl=60, show_spinner=False)
def _load_all_users():
    return db.get_all_users()

@st.cache_data(ttl=60, show_spinner=False)
def _load_all_trips():
    return db.get_all_trips()

@st.cache_data(ttl=60, show_spinner=False)
def _load_all_payments():
    return db.get_all_payments()

@st.cache_data(ttl=60, show_spinner=False)
def _load_all_trip_prices():
    return db.get_all_trip_prices()

@st.cache_data(ttl=60, show_spinner=False)
def _load_all_accounts():
    return db.get_all_accounts()

@st.cache_data(ttl=60, show_spinner=False)
def _load_group_access():
    return db.get_all_group_access()

@st.cache_data(ttl=60, show_spinner=False)
def _load_driver_availability():
    return db.get_all_driver_availability()

@st.cache_data(ttl=60, show_spinner=False)
def _load_group_schedules():
    return db.get_all_group_schedules()

@st.cache_data(ttl=60, show_spinner=False)
def _load_passenger_schedules():
    return db.get_all_passenger_schedules()

@st.cache_data(ttl=60, show_spinner=False)
def _load_driver_weekly_availability():
    return db.get_all_driver_weekly_availability()


def clear_data_cache():
    """Clear all cached data. Call after any write operation."""
    _load_passengers.clear()
    _load_groups.clear()
    _load_all_users.clear()
    _load_all_trips.clear()
    _load_all_payments.clear()
    _load_all_trip_prices.clear()
    _load_all_accounts.clear()
    _load_group_access.clear()
    _load_driver_availability.clear()
    _load_group_schedules.clear()
    _load_passenger_schedules.clear()
    _load_driver_weekly_availability.clear()


# --- Helper functions that read from cached bulk data (no API calls) ---

def get_passengers():
    return _load_passengers()

def get_groups():
    return _load_groups()

def get_group_by_id(group_id):
    if group_id is None:
        return None
    return next((g for g in _load_groups() if g["groupid"] == group_id), None)

def get_user_by_id(staff_id):
    return next((u for u in _load_all_users() if u.get("user_id") == staff_id), None)

def get_trips_for_pass(passid):
    return [t for t in _load_all_trips() if t.get("passid") == passid]

def get_all_trips_cached():
    return _load_all_trips()

def get_payments_for_pass(passid):
    return [p for p in _load_all_payments() if p.get("passid") == passid]

def get_amount_owed(passid):
    """Return (total_trips, total_paid, amount_owed) from cached data."""
    trips = get_trips_for_pass(passid)
    payments = get_payments_for_pass(passid)
    total_trips = sum(float(t.get("tripamount") or 0) for t in trips)
    total_paid = sum(float(p.get("amountpayed") or 0) for p in payments)
    return total_trips, total_paid, total_trips - total_paid

def get_account_for_user_cached(user_id):
    return next((a for a in _load_all_accounts() if a.get("user_id") == user_id), None)

def get_account_balance(user_id):
    account = get_account_for_user_cached(user_id)
    if account:
        return float(account.get("balance") or 0)
    total_trips, total_paid, _ = get_amount_owed(user_id)
    return total_paid - total_trips

def get_trip_rate_cached(user_id, group_id):
    """Determine trip rate from cached TripPrice + groups data."""
    custom = next((p for p in _load_all_trip_prices() if p.get("user_id") == user_id), None)
    if custom and custom.get("trip_rate") is not None:
        return float(custom["trip_rate"])
    group = get_group_by_id(group_id)
    if group and group.get("groupamount") is not None:
        return float(group["groupamount"])
    return 20.0

def cached_generate_staff_id(abbreviation):
    users = _load_all_users()
    max_num = 1000
    for user in users:
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

def cached_get_next_user_number():
    users = _load_all_users()
    if users:
        return max((u.get("user_number") or 0) for u in users) + 1
    return 1


# --- Driver-filtered helpers (group access control) ---

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_week_start(default_to_today=True):
    """Return the Monday of the week containing today (for default week selection)."""
    today = date.today()
    return today - timedelta(days=today.weekday())  # 0=Monday

def week_dates(week_start):
    """Return a list of 7 date objects (Mon-Sun) for the given week start."""
    return [week_start + timedelta(days=i) for i in range(7)]

def get_driver_group_ids(driverid):
    """Return a set of group IDs the driver has access to."""
    access = _load_group_access()
    return set(a["groupid"] for a in access if a.get("driverid") == driverid)

def get_groups_for_driver(driverid):
    """Return only the groups the driver has access to."""
    group_ids = get_driver_group_ids(driverid)
    return [g for g in _load_groups() if g["groupid"] in group_ids]

def get_passengers_for_driver(driverid):
    """Return only passengers in groups the driver has access to."""
    group_ids = get_driver_group_ids(driverid)
    return [p for p in _load_passengers() if p.get("group_id") in group_ids]

def get_trips_for_driver(driverid):
    """Return only trips for passengers in the driver's accessible groups."""
    passenger_ids = set(p["user_id"] for p in get_passengers_for_driver(driverid))
    return [t for t in _load_all_trips() if t.get("passid") in passenger_ids]

def get_driver_unavailable_dates(driverid):
    """Return list of unavailable date strings for a driver."""
    avail = _load_driver_availability()
    return sorted([a["unavailable_date"] for a in avail if a.get("driverid") == driverid])

def get_driver_weekly_availability(driverid, group_id=None):
    """Return a dict {day_of_week: row_dict} for a driver filtered by group.

    group_id=None  → return rows where group_id IS NULL (applies to all groups).
    group_id=<int> → return rows for that specific group.

    Each row contains at minimum {'available': bool} plus optional
    'time_from', 'time_to', 'comments'.  Days not in the DB default to
    {'available': True, 'time_from': None, 'time_to': None, 'comments': None}.
    """
    avail = _load_driver_weekly_availability()
    result = {}
    for a in avail:
        if a.get("driverid") != driverid:
            continue
        row_gid = a.get("group_id")  # may be None or an int
        if group_id is None and row_gid is None:
            result[a["day_of_week"]] = a
        elif group_id is not None and row_gid == group_id:
            result[a["day_of_week"]] = a
    return result

def get_knockoff_time_for_passenger(user_id, day_of_week):
    """Return the knock-off time for a passenger on a given day.

    Checks PassengerSchedule first (individual override), then GroupSchedule
    (group default). Returns a time string like '17:30' or None.
    """
    # 1. Check passenger's custom schedule
    psched = _load_passenger_schedules()
    custom = next(
        (s for s in psched if s.get("user_id") == user_id and s.get("day_of_week") == day_of_week),
        None,
    )
    if custom:
        return str(custom.get("knockoff_time", ""))[:5]  # HH:MM

    # 2. Fall back to group schedule
    user = get_user_by_id(user_id)
    if user and user.get("group_id") is not None:
        gsched = _load_group_schedules()
        group_s = next(
            (s for s in gsched if s.get("group_id") == user["group_id"] and s.get("day_of_week") == day_of_week),
            None,
        )
        if group_s:
            return str(group_s.get("knockoff_time", ""))[:5]

    return None


# ---------------------------------------------------------------------------
# Sidebar – navigation / status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🚐 Staff Transport")
    if st.session_state.role is None:
        st.info("Select a role to begin.")
    elif st.session_state.role == "passenger":
        st.success("Passenger mode")
        if st.button("Back to Home"):
            reset_session()
    elif st.session_state.role == "driver":
        if st.session_state.driver_logged_in:
            profile = st.session_state.driver_profile
            st.success(f"Driver: {profile.get('username', '')}")
            if st.button("Log Out"):
                reset_session()
        else:
            st.warning("Driver login required")
            if st.button("Back to Home"):
                reset_session()


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------
def landing_page():
    st.markdown("# 🚐 Staff Transport Register")
    st.markdown("Track trips, manage passengers, and view amounts owed.")
    st.write("")

    col1, col2, col3 = st.columns([1, 2, 2])

    with col2:
        st.markdown("### Are you a Passenger?")
        st.write("Look up your trips and amount owed using your Staff ID.")
        if st.button("Passenger Portal", use_container_width=True, type="primary"):
            st.session_state.role = "passenger"
            st.rerun()

    with col3:
        st.markdown("### Are you a Driver?")
        st.write("Log in to manage passengers and capture trips.")
        if st.button("Driver Portal", use_container_width=True):
            st.session_state.role = "driver"
            st.rerun()


# ---------------------------------------------------------------------------
# Passenger view
# ---------------------------------------------------------------------------
def passenger_view():
    st.markdown("# 👤 Passenger Portal")
    st.markdown("Enter your Staff ID to view your travel history and amount owed.")
    st.write("")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        staff_id_input = st.text_input(
            "Staff ID",
            placeholder="e.g. ABS1008",
            key="passenger_staff_id",
        )
        lookup = st.button("Look Up My Trips", type="primary", use_container_width=True)
        if st.session_state.passenger_lookup_id:
            if st.button("New Search", use_container_width=True):
                st.session_state.passenger_lookup_id = None
                st.rerun()

    if lookup:
        if not staff_id_input.strip():
            st.warning("Please enter your Staff ID.")
            return

        staff_id = staff_id_input.strip()
        user = get_user_by_id(staff_id)

        if not user:
            st.error(f"No record found for Staff ID '{staff_id}'. Please check your ID and try again.")
            return

        if user.get("type") == "Driver":
            st.error("This Staff ID belongs to a driver. Please use the Driver Portal.")
            return

        # Persist the lookup so details survive reruns (e.g. after schedule update)
        st.session_state.passenger_lookup_id = staff_id
        st.rerun()

    # --- Render passenger details from persisted lookup state ---
    active_id = st.session_state.passenger_lookup_id
    if active_id:
        user = get_user_by_id(active_id)
        if not user or user.get("type") == "Driver":
            st.session_state.passenger_lookup_id = None
            st.rerun()
            return

        staff_id = active_id

        # --- Passenger details ---
        st.write("")
        st.markdown("---")
        st.markdown(f"### {user.get('full_names', 'Unknown')}")

        detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
        with detail_col1:
            st.metric("Staff ID", user.get("user_id", ""))
        with detail_col2:
            group = get_group_by_id(user.get("group_id"))
            st.metric("Group", group.get("groupname", "N/A") if group else "N/A")
        with detail_col3:
            st.metric("Contact", user.get("contact_numbers") or "N/A")
        with detail_col4:
            rate = get_trip_rate_cached(staff_id, user.get("group_id"))
            st.metric("Trip Rate", f"R{rate:.2f}")

        st.write("")

        # --- Trip summary ---
        trips = get_trips_for_pass(staff_id)
        total_amount, total_paid, amount_owed = get_amount_owed(staff_id)
        account = get_account_for_user_cached(staff_id)
        account_balance = float(account.get("balance", 0)) if account else (total_paid - total_amount)

        summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
        with summary_col1:
            st.metric("Total Trips", len(trips))
        with summary_col2:
            # Count distinct trip dates as "days travelled"
            distinct_dates = set(t.get("tripdate") for t in trips if t.get("tripdate"))
            st.metric("Days Travelled", len(distinct_dates))
        with summary_col3:
            st.metric("Total Amount", f"R{total_amount:.2f}")
        with summary_col4:
            st.metric("Amount Owed", f"R{amount_owed:.2f}")
        with summary_col5:
            st.metric("Account Balance", f"R{account_balance:.2f}")

        st.write("")

        # --- Trip history table ---
        st.markdown("### Trip History")

        if not trips:
            st.info("No trips recorded yet.")
        else:
            # Build a display-friendly table
            display_rows = []
            for t in trips:
                trip_date = t.get("tripdate", "")
                if trip_date:
                    try:
                        trip_date = datetime.strptime(str(trip_date), "%Y-%m-%d").strftime("%d %b %Y")
                    except (ValueError, TypeError):
                        pass

                trip_status = t.get("tripstatus", "—") or "—"

                display_rows.append({
                    "Date": trip_date,
                    "From": t.get("fromloc") or "—",
                    "To": t.get("toloc") or "—",
                    "Amount": f"R{float(t.get('tripamount') or 0):.2f}",
                    "Status": trip_status,
                    "Comments": t.get("Comments") or "",
                })

            render_table(display_rows)

        # --- Payment history ---
        payments = get_payments_for_pass(staff_id)
        if payments:
            st.write("")
            st.markdown("### Payment History")
            pay_rows = []
            for p in payments:
                pay_date = p.get("paydate", "")
                if pay_date:
                    try:
                        pay_date = datetime.strptime(str(pay_date), "%Y-%m-%d").strftime("%d %b %Y")
                    except (ValueError, TypeError):
                        pass
                pay_rows.append({
                    "Date": pay_date,
                    "Amount Paid": f"R{float(p.get('amountpayed') or 0):.2f}",
                    "Comments": p.get("Comments") or "",
                })
            render_table(pay_rows)

        # --- Driver availability ---
        st.write("")
        st.markdown("### Driver Availability")
        today_dow = date.today().weekday()  # 0=Mon … 6=Sun — used to filter past days
        group_id = user.get("group_id")
        if group_id is not None:
            access = _load_group_access()
            driver_ids = set(a["driverid"] for a in access if a.get("groupid") == group_id)

            if not driver_ids:
                st.info("No driver has been assigned to your group yet.")
            else:
                for did in sorted(driver_ids):
                    driver_user = get_user_by_id(did)
                    driver_name = driver_user.get("full_names", did) if driver_user else did

                    # Merge all-groups records with group-specific records;
                    # group-specific takes precedence for the same day.
                    weekly_avail_all = get_driver_weekly_availability(did, group_id=None)
                    weekly_avail_grp = get_driver_weekly_availability(did, group_id=group_id)
                    merged_avail = {**weekly_avail_all, **weekly_avail_grp}

                    avail_days = []
                    unavail_rows = []   # list of (day_name, row_dict)
                    for dow in range(7):
                        # Skip days that have already passed this week
                        if dow < today_dow:
                            continue
                        row = merged_avail.get(dow, {})
                        is_available = row.get("available", True) if isinstance(row, dict) else True
                        if is_available:
                            avail_days.append(DAYS_OF_WEEK[dow])
                        else:
                            unavail_rows.append((DAYS_OF_WEEK[dow], row if isinstance(row, dict) else {}))

                    if not unavail_rows:
                        st.success(f"**{driver_name}** is available every day of the week.")
                    else:
                        # Summary warning line
                        unavail_day_names = [d for d, _ in unavail_rows]
                        st.warning(
                            f"**{driver_name}** is NOT available on: "
                            f"{', '.join(unavail_day_names)}"
                        )

                        # Per-day detail cards
                        for day_name, row in unavail_rows:
                            time_from = (row.get("time_from") or "")[:5]
                            time_to   = (row.get("time_to")   or "")[:5]
                            comments  =  row.get("comments")  or ""

                            if time_from and time_to:
                                avail_msg = f"Unavailable from **{time_from}** to **{time_to}**"
                            elif time_from:
                                avail_msg = f"Unavailable from **{time_from}**"
                            else:
                                avail_msg = "Unavailable for the **whole day**"

                            reason_msg = f"  \n📝 Reason: *{comments}*" if comments else ""

                            st.markdown(
                                f"&nbsp;&nbsp;🚫 **{day_name}** — {avail_msg}{reason_msg}"
                            )

                    if avail_days:
                        st.caption(f"Available days: {', '.join(avail_days)}")

                    # Date-specific unavailable dates
                    unavail_dates = get_driver_unavailable_dates(did)
                    today_str = str(date.today())
                    upcoming = [d for d in unavail_dates if str(d) >= today_str]

                    if upcoming:
                        st.write("")
                        st.markdown("**Specific unavailable dates:**")
                        for ud in upcoming:
                            ud_display = str(ud)
                            try:
                                ud_display = datetime.strptime(ud_display, "%Y-%m-%d").strftime("%d %b %Y (%A)")
                            except (ValueError, TypeError):
                                pass
                            st.write(f"  - {ud_display}")
        else:
            st.info("No group assigned to your account.")

        # --- Knock-off schedule ---
        st.write("")
        st.markdown("### My Knock-off Schedule")

        # Always work with the current week — no selector needed.
        # The schedule is one rolling 7-day window; past days are locked.
        week_start = get_week_start()
        wdates = week_dates(week_start)
        week_end = wdates[6]
        today_dow = date.today().weekday()  # 0=Mon … 6=Sun

        st.markdown(
            f"**Week: {week_start.strftime('%d %b %Y')} – {week_end.strftime('%d %b %Y')}**"
        )
        st.write(
            "Set your knock-off time for today and future days, then click "
            "**Update Schedule** to save. Past days are locked. "
            "Leave a day blank to use the group default."
        )

        # Load existing schedule for this passenger (keyed by day_of_week int)
        psched = _load_passenger_schedules()
        existing_psched = {
            s["day_of_week"]: str(s.get("knockoff_time", ""))[:5]
            for s in psched
            if s.get("user_id") == staff_id
        }

        ps_col1, ps_col2, ps_col3, ps_col4 = st.columns(4)
        new_times = {}
        for dow in range(7):
            target_col = [ps_col1, ps_col2, ps_col3, ps_col4][dow % 4]
            day_date_str = wdates[dow].strftime("%d %b")
            is_past = dow < today_dow  # days before today in this week

            with target_col:
                current_time = existing_psched.get(dow, "")
                group_default = get_knockoff_time_for_passenger(staff_id, dow)

                if is_past:
                    # Past day — show read-only, not editable
                    display_val = current_time or group_default or "—"
                    st.text_input(
                        f"{DAYS_OF_WEEK[dow]} ({day_date_str})",
                        value=display_val,
                        key=f"psched_{staff_id}_{dow}",
                        disabled=True,
                    )
                    new_times[dow] = None  # sentinel: skip on save
                else:
                    label = f"{DAYS_OF_WEEK[dow]} ({day_date_str})"
                    if not current_time and group_default:
                        label = f"{DAYS_OF_WEEK[dow]} ({day_date_str}) [default: {group_default}]"
                    time_str = st.text_input(
                        label,
                        value=current_time,
                        placeholder=group_default or "17:30",
                        key=f"psched_{staff_id}_{dow}",
                    )
                    new_times[dow] = time_str

        if st.button("Update Schedule", type="primary", key="update_sched_btn"):
            # Collect only future/today days that have a value
            times_to_save = {
                dow: t.strip()
                for dow, t in new_times.items()
                if t is not None and t.strip()
            }

            try:
                # Wipe the entire existing schedule for this passenger, then
                # re-insert only what was just entered. This keeps one clean
                # schedule per passenger and removes any stale entries.
                db.delete_all_passenger_schedules_for_user(staff_id)
                for dow, time_str in times_to_save.items():
                    db.upsert_passenger_schedule(staff_id, dow, time_str)
                clear_data_cache()
                st.success("Schedule updated successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update schedule: {e}")

    else:
        with col_right:
            st.info("👉 Enter your Staff ID on the left and click **Look Up My Trips** to see your travel history.")


# ---------------------------------------------------------------------------
# Driver login
# ---------------------------------------------------------------------------
def driver_login_page():
    st.markdown("# 🔐 Driver Login")
    st.markdown("Enter your username and password to access the driver dashboard.")
    st.write("")

    col1, col2 = st.columns([1, 2])

    with col1:
        with st.form("driver_login_form"):
            username = st.text_input("Username", placeholder="e.g. TB501")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In", type="primary", use_container_width=True)

    if submit:
        if not username.strip() or not password:
            st.warning("Please enter both your username and password.")
            return

        with st.spinner("Authenticating..."):
            profile, result = db.driver_login(username.strip(), password)

        if profile is None:
            st.error(result)
            return

        # Login succeeded — store in session state
        st.session_state.driver_logged_in = True
        st.session_state.driver_profile = profile

        # Also fetch the driver's user record from the users table
        driver_user = get_user_by_id(profile.get("username"))
        st.session_state.driver_user = driver_user

        st.success(f"Welcome, {profile.get('username')}!")
        st.rerun()

    with col2:
        st.info("👉 Enter your driver credentials on the left. Your username is the same as your Staff ID (e.g. TB501).")


# ---------------------------------------------------------------------------
# Driver dashboard
# ---------------------------------------------------------------------------
def driver_dashboard():
    profile = st.session_state.driver_profile
    driver_user = st.session_state.driver_user
    driver_id = profile.get("username")  # e.g. "TB501"

    st.markdown(f"# 🚐 Driver Dashboard — {driver_id}")

    if driver_user:
        st.markdown(f"**{driver_user.get('full_names', '')}**")
        st.write("")

    # -----------------------------------------------------------------------
    # Tabs for different driver functions
    # -----------------------------------------------------------------------
    tab_passengers, tab_trips, tab_add_trip, tab_payments, tab_add_staff, tab_group_access, tab_pschedule = st.tabs([
        "📋 Passengers",
        "🛣️ Trip History",
        "✏️ Capture Trip",
        "💳 Payments",
        "➕ Add Staff",
        "🔐 Group Access",
        "🗓️ Passenger Schedule",
    ])

    # --- Tab 1: Passengers overview ----------------------------------------
    with tab_passengers:
        st.markdown("### Passenger Overview")
        st.write("All passengers and their trip/amount summaries.")

        passengers = get_passengers_for_driver(driver_id)
        if not passengers:
            st.info("No passengers registered yet. Use the **Add Staff** tab to add one.")
        else:
            rows = []
            for p in passengers:
                trips = get_trips_for_pass(p["user_id"])
                total_amt, total_paid, owed = get_amount_owed(p["user_id"])

                group = get_group_by_id(p.get("group_id"))
                group_name = group.get("groupname", "N/A") if group else "N/A"

                rows.append({
                    "Staff ID": p.get("user_id", ""),
                    "Name": p.get("full_names", ""),
                    "Group": group_name,
                    "Contact": p.get("contact_numbers") or "",
                    "Trips": len(trips),
                    "Total Amount": f"R{total_amt:.2f}",
                    "Total Paid": f"R{total_paid:.2f}",
                    "Amount Owed": f"R{owed:.2f}",
                    "Account Balance": f"R{(total_paid - total_amt):.2f}",
                })

            render_table(rows)

    # --- Tab 2: Trip history (view / edit / delete) ------------------------
    with tab_trips:
        st.markdown("### Trip History")
        st.write("View, edit, or delete recorded trips.")

        all_passengers = get_passengers_for_driver(driver_id)

        # Filters: passenger + payment status
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            pass_options = {"All Passengers": None}
            for p in all_passengers:
                pass_options[f"{p['user_id']} — {p.get('full_names', '')}"] = p["user_id"]
            selected_filter = st.selectbox("Filter by passenger", list(pass_options.keys()), key="trip_filter_passenger")
            filter_id = pass_options[selected_filter]

        with filter_col2:
            status_options = {"All": None, "Unpaid": "Unpaid", "Paid": "Paid"}
            selected_status = st.selectbox("Filter by status", list(status_options.keys()), key="trip_filter_status")
            filter_status = status_options[selected_status]

        if filter_id:
            trips = get_trips_for_pass(filter_id)
        else:
            trips = get_trips_for_driver(driver_id)

        # Filter by payment status
        if filter_status:
            trips = [t for t in trips if t.get("tripstatus") == filter_status]

        if not trips:
            st.info("No trips found. Use the **Capture Trip** tab to record one.")
        else:
            display_rows = []
            for t in trips:
                trip_date = t.get("tripdate", "")
                if trip_date:
                    try:
                        trip_date = datetime.strptime(str(trip_date), "%Y-%m-%d").strftime("%d %b %Y")
                    except (ValueError, TypeError):
                        pass

                trip_status = t.get("tripstatus", "—") or "—"

                display_rows.append({
                    "ID": t.get("tripid"),
                    "Date": trip_date,
                    "Passenger": t.get("passid", ""),
                    "Driver": t.get("driverid", ""),
                    "From": t.get("fromloc") or "—",
                    "To": t.get("toloc") or "—",
                    "Amount": f"R{float(t.get('tripamount') or 0):.2f}",
                    "Status": trip_status,
                    "Comments": t.get("Comments") or "",
                })

            render_table(display_rows)

            # --- Edit / Delete a trip ---
            st.write("")
            st.markdown("#### Edit a Trip")
            trip_ids = [t.get("tripid") for t in trips]
            edit_trip_id = st.selectbox("Select trip to edit", trip_ids, key="edit_trip_select")

            if edit_trip_id:
                trip_to_edit = next((t for t in trips if t.get("tripid") == edit_trip_id), None)
                if trip_to_edit:
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        existing_date = trip_to_edit.get("tripdate")
                        if existing_date:
                            try:
                                existing_date = datetime.strptime(str(existing_date), "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                existing_date = date.today()
                        else:
                            existing_date = date.today()

                        edit_date = st.date_input("Trip Date", value=existing_date, key="edit_date")

                        pass_map = {f"{p['user_id']} — {p.get('full_names', '')}": p["user_id"] for p in all_passengers}
                        pass_labels = list(pass_map.keys())
                        current_pass_label = next(
                            (k for k, v in pass_map.items() if v == trip_to_edit.get("passid")),
                            pass_labels[0] if pass_labels else "",
                        )
                        edit_passenger = st.selectbox("Passenger", pass_labels, index=pass_labels.index(current_pass_label) if current_pass_label in pass_labels else 0, key="edit_passenger")
                        edit_passid = pass_map.get(edit_passenger, "")

                        edit_status = st.selectbox(
                            "Status",
                            ["Unpaid", "Paid"],
                            index=0 if trip_to_edit.get("tripstatus") != "Paid" else 1,
                            key="edit_status",
                        )

                    with edit_col2:
                        edit_fromloc = st.text_input("From Location", value=trip_to_edit.get("fromloc") or "", key="edit_fromloc")
                        edit_toloc = st.text_input("To Location", value=trip_to_edit.get("toloc") or "", key="edit_toloc")

                        edit_amount = st.number_input(
                            "Trip Amount (R)",
                            value=float(trip_to_edit.get("tripamount") or 0),
                            min_value=0.0,
                            step=0.5,
                            key="edit_amount",
                        )

                        edit_comments = st.text_input("Comments", value=trip_to_edit.get("Comments") or "", key="edit_comments")

                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("Save Changes", type="primary", key="save_edit"):
                            updates = {
                                "tripdate": str(edit_date),
                                "passid": edit_passid,
                                "tripstatus": edit_status,
                                "fromloc": edit_fromloc,
                                "toloc": edit_toloc,
                                "tripamount": edit_amount,
                                "Comments": edit_comments or None,
                            }
                            try:
                                db.update_trip(edit_trip_id, updates)
                                st.success("Trip updated successfully!")
                                clear_data_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update trip: {e}")

                    with btn_col2:
                        if st.button("Mark as Paid", key="mark_paid"):
                            try:
                                db.update_trip(edit_trip_id, {"tripstatus": "Paid"})
                                st.success("Trip marked as Paid.")
                                clear_data_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update trip: {e}")

                    with btn_col3:
                        if st.button("Delete Trip", key="delete_trip"):
                            try:
                                db.delete_trip(edit_trip_id)
                                st.success("Trip deleted.")
                                clear_data_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete trip: {e}")

    # --- Tab 3: Add new staff member ---------------------------------------
    with tab_add_staff:
        st.markdown("### Add New Staff Member")
        st.write("Register a new passenger. The Staff ID is auto-generated from the group abbreviation.")

        all_groups = get_groups_for_driver(driver_id)

        group_labels = [f"{g['groupid']} — {g['groupname']} (R{(g.get('groupamount') or 0):.2f})" for g in all_groups]
        group_map = {f"{g['groupid']} — {g['groupname']} (R{(g.get('groupamount') or 0):.2f})": g["groupid"] for g in all_groups}

        # Group selectbox
        selected_group = st.selectbox("Group *", group_labels, key="new_group_select")
        new_group_id = group_map.get(selected_group)
        selected_group_obj = next((g for g in all_groups if g["groupid"] == new_group_id), None)

        # Detect group change to auto-generate staff ID and populate trip rate
        last_group = st.session_state.get("_last_group_select")
        if last_group != selected_group:
            st.session_state["_last_group_select"] = selected_group
            if selected_group_obj:
                abbrev = selected_group_obj.get("groupAbrivation", "")
                if abbrev:
                    st.session_state["new_staff_id_display"] = cached_generate_staff_id(abbrev)
                st.session_state["new_trip_rate"] = float(selected_group_obj.get("groupamount") or 0)

        add_col1, add_col2 = st.columns(2)
        with add_col1:
            # Auto-generated staff ID (read-only)
            new_staff_id = st.text_input("Staff ID (auto-generated)", key="new_staff_id_display", disabled=True)
            new_name = st.text_input("Full Name *", key="new_name")
            new_phone = st.text_input("Contact Number", key="new_phone")
            new_email = st.text_input("Email", key="new_email")

        with add_col2:
            # Trip rate — auto-populated from group amount, editable
            if "new_trip_rate" not in st.session_state:
                st.session_state["new_trip_rate"] = float(selected_group_obj.get("groupamount") or 0) if selected_group_obj else 0.0
            new_trip_rate = st.number_input(
                "Trip Rate (R) *",
                min_value=0.0,
                step=0.5,
                key="new_trip_rate",
                help="Auto-populated from the group's rate. Change if this passenger has a different rate.",
            )
            new_home = st.text_input("Home Location", key="new_home")
            new_work = st.text_input("Work Location", key="new_work")
            new_comments = st.text_input("Comments", key="new_comments")

        if st.button("Add Staff Member", type="primary", key="add_staff_btn"):
            staff_id_val = st.session_state.get("new_staff_id_display", "").strip()
            if not staff_id_val or not new_name.strip():
                st.warning("Please select a group and enter a Full Name.")
                return

            existing = get_user_by_id(staff_id_val)
            if existing:
                st.error(f"Staff ID '{staff_id_val}' already exists.")
                return

            next_num = cached_get_next_user_number()
            new_user = {
                "user_id": staff_id_val,
                "full_names": new_name.strip(),
                "type": selected_group_obj["groupname"] if selected_group_obj else "Passenger",
                "home_location": new_home.strip() or None,
                "work_location": new_work.strip() or None,
                "email": new_email.strip() or None,
                "group_id": new_group_id,
                "comments": new_comments.strip() or None,
                "contact_numbers": new_phone.strip() or None,
                "user_number": next_num,
            }

            try:
                db.add_user(new_user)
                # Save the trip rate to TripPrice table
                db.upsert_trip_price(staff_id_val, new_group_id, new_trip_rate)
            except Exception as e:
                st.error(f"Failed to add staff member: {e}")
            else:
                # Create an account — non-fatal if it fails (account can be
                # created later; the user row is what matters)
                account_note = ""
                try:
                    db.create_account(staff_id_val)
                except Exception:
                    account_note = " (account creation skipped — already exists or column mismatch)"
                st.success(
                    f"Staff member '{staff_id_val}' added with trip rate "
                    f"R{new_trip_rate:.2f}.{account_note}"
                )
                clear_data_cache()
                st.rerun()

    # --- Tab 4: Capture a new trip -----------------------------------------
    with tab_add_trip:
        st.markdown("### Capture Trips")
        st.write("Select passengers and adjust dates/rates before capturing. Trips are marked as 'Unpaid' by default.")

        if not all_passengers:
            st.warning("No passengers available. Add staff members first.")

        # Default trip date, direction, and group filter
        cap_col1, cap_col2, cap_col3 = st.columns(3)
        with cap_col1:
            cap_default_date = st.date_input("Default Trip Date", value=date.today(), key="cap_default_date")
        with cap_col2:
            cap_direction = st.selectbox(
                "Direction",
                ["to_work", "from_work"],
                format_func=lambda x: "Home to Work" if x == "to_work" else "Work to Home",
                key="cap_direction",
            )
        with cap_col3:
            all_groups = get_groups_for_driver(driver_id)
            group_filter_options = {"All Groups": None}
            for g in all_groups:
                group_filter_options[g["groupname"]] = g["groupid"]
            selected_group_filter = st.selectbox("Filter by Group", list(group_filter_options.keys()), key="cap_group_filter")
            filter_group_id = group_filter_options[selected_group_filter]

        # Filter passengers by group if selected
        if filter_group_id is not None:
            display_passengers = [p for p in all_passengers if p.get("group_id") == filter_group_id]
        else:
            display_passengers = all_passengers

        st.write("")
        st.markdown("#### Select Passengers")
        selected_passengers = []
        for p in display_passengers:
            checked = st.checkbox(f"{p['user_id']} — {p.get('full_names', '')}", key=f"check_{p['user_id']}")
            if checked:
                selected_passengers.append(p)

        if selected_passengers:
            st.write("")
            st.markdown("#### Adjust Dates and Rates")

            trip_data_list = []
            for p in selected_passengers:
                with st.container(border=True):
                    st.markdown(f"**{p['user_id']} — {p.get('full_names', '')}**")
                    adj_col1, adj_col2 = st.columns(2)

                    with adj_col1:
                        p_date = st.date_input(
                            f"Trip Date",
                            value=cap_default_date,
                            key=f"pdate_{p['user_id']}",
                        )

                    with adj_col2:
                        default_rate = get_trip_rate_cached(p["user_id"], p.get("group_id"))
                        p_rate = st.number_input(
                            "Rate (R)",
                            value=default_rate,
                            min_value=0.0,
                            step=0.5,
                            key=f"prate_{p['user_id']}",
                        )

                    # Auto-populate from/to based on direction
                    home_loc = p.get("home_location", "") or ""
                    work_loc = p.get("work_location", "") or ""
                    if cap_direction == "to_work":
                        from_loc, to_loc = home_loc, work_loc
                    else:
                        from_loc, to_loc = work_loc, home_loc

                    trip_data_list.append({
                        "passid": p["user_id"],
                        "driverid": driver_id,
                        "tripdate": str(p_date),
                        "tripamount": p_rate,
                        "tripstatus": "Unpaid",
                        "fromloc": from_loc or None,
                        "toloc": to_loc or None,
                    })

            if st.button("Capture Selected Trips", type="primary", key="capture_all_btn"):
                success_count = 0
                errors = []
                for td in trip_data_list:
                    try:
                        db.add_trip(td)
                        success_count += 1
                    except Exception as e:
                        errors.append(f"{td['passid']}: {e}")

                if success_count > 0:
                    # Update account balances for affected passengers
                    updated_passids = set(td["passid"] for td in trip_data_list)
                    for pid in updated_passids:
                        try:
                            db.update_account_balance_for_user(pid)
                        except Exception:
                            pass  # account may not exist yet
                    st.success(f"Captured {success_count} trip(s) successfully!")
                if errors:
                    for err in errors:
                        st.error(f"Failed: {err}")
                if success_count > 0:
                    clear_data_cache()
                    st.rerun()

    # --- Tab 5: Payments ----------------------------------------------------
    with tab_payments:
        st.markdown("### Payment Capture")
        st.write("Capture a payment for a passenger. Payments are distributed across unpaid trips (oldest first).")

        all_passengers = get_passengers_for_driver(driver_id)
        if not all_passengers:
            st.warning("No passengers available.")
        else:
            pay_col1, pay_col2 = st.columns(2)
            with pay_col1:
                pass_map = {f"{p['user_id']} — {p.get('full_names', '')}": p["user_id"] for p in all_passengers}
                pass_labels = list(pass_map.keys())
                pay_passenger = st.selectbox("Select Passenger *", pass_labels, key="pay_passenger")
                pay_passid = pass_map.get(pay_passenger, "")

            with pay_col2:
                pay_date = st.date_input("Payment Date *", value=date.today(), key="pay_date")

            # Show passenger summary
            if pay_passid:
                trips = get_trips_for_pass(pay_passid)
                total_amt, total_paid, owed = get_amount_owed(pay_passid)
                account = get_account_for_user_cached(pay_passid)
                account_balance = float(account.get("balance", 0)) if account else (total_paid - total_amt)

                sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
                with sum_col1:
                    st.metric("Total Trips", len(trips))
                with sum_col2:
                    st.metric("Total Amount", f"R{total_amt:.2f}")
                with sum_col3:
                    st.metric("Total Paid", f"R{total_paid:.2f}")
                with sum_col4:
                    st.metric("Account Balance", f"R{account_balance:.2f}")

                # Show unpaid / partially paid trips
                unpaid_trips = [t for t in trips if t.get("tripstatus") in ("Unpaid", "partially paid")]
                if unpaid_trips:
                    st.write("")
                    st.markdown("#### Unpaid / Partially Paid Trips")
                    unpaid_rows = []
                    for t in unpaid_trips:
                        trip_date = t.get("tripdate", "")
                        if trip_date:
                            try:
                                trip_date = datetime.strptime(str(trip_date), "%Y-%m-%d").strftime("%d %b %Y")
                            except (ValueError, TypeError):
                                pass
                        unpaid_rows.append({
                            "Trip ID": t.get("tripid"),
                            "Date": trip_date,
                            "Amount": f"R{float(t.get('tripamount') or 0):.2f}",
                            "Status": t.get("tripstatus", ""),
                        })
                    render_table(unpaid_rows)

                # Payment form
                st.write("")
                st.markdown("#### Capture Payment")
                pay_amount = st.number_input(
                    "Payment Amount (R) *",
                    min_value=0.0,
                    step=1.0,
                    key="pay_amount",
                )
                pay_comments = st.text_input("Comments", key="pay_comments")

                if st.button("Capture Payment", type="primary", key="capture_payment_btn"):
                    if pay_amount <= 0:
                        st.warning("Payment amount must be greater than 0.")
                    else:
                        try:
                            db.capture_payment(pay_passid, driver_id, pay_amount, pay_date, pay_comments or None)
                            st.success(f"Payment of R{pay_amount:.2f} captured for {pay_passid}.")
                            clear_data_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to capture payment: {e}")

                # Payment history with edit option
                payments = get_payments_for_pass(pay_passid)
                if payments:
                    st.write("")
                    st.markdown("#### Payment History")
                    pay_hist_rows = []
                    for p in payments:
                        p_date = p.get("paydate", "")
                        if p_date:
                            try:
                                p_date = datetime.strptime(str(p_date), "%Y-%m-%d").strftime("%d %b %Y")
                            except (ValueError, TypeError):
                                pass
                        pay_hist_rows.append({
                            "Pay ID": p.get("payid"),
                            "Date": p_date,
                            "Driver": p.get("driverid", ""),
                            "Amount": f"R{float(p.get('amountpayed') or 0):.2f}",
                            "Comments": p.get("Comments") or "",
                        })
                    render_table(pay_hist_rows)

                    # Edit payment
                    st.write("")
                    st.markdown("##### Edit a Payment")
                    pay_ids = [p.get("payid") for p in payments]
                    edit_pay_id = st.selectbox("Select payment to edit", pay_ids, key="edit_pay_select")

                    if edit_pay_id:
                        pay_to_edit = next((p for p in payments if p.get("payid") == edit_pay_id), None)
                        if pay_to_edit:
                            edit_pay_col1, edit_pay_col2 = st.columns(2)
                            with edit_pay_col1:
                                existing_pay_date = pay_to_edit.get("paydate")
                                if existing_pay_date:
                                    try:
                                        existing_pay_date = datetime.strptime(str(existing_pay_date), "%Y-%m-%d").date()
                                    except (ValueError, TypeError):
                                        existing_pay_date = date.today()
                                else:
                                    existing_pay_date = date.today()
                                edit_pay_date = st.date_input("Payment Date", value=existing_pay_date, key="edit_pay_date")
                            with edit_pay_col2:
                                edit_pay_amount = st.number_input(
                                    "Amount (R)",
                                    value=float(pay_to_edit.get("amountpayed") or 0),
                                    min_value=0.0,
                                    step=1.0,
                                    key="edit_pay_amount",
                                )
                            edit_pay_comments = st.text_input(
                                "Comments",
                                value=pay_to_edit.get("Comments") or "",
                                key="edit_pay_comments",
                            )
                            if st.button("Update Payment", type="primary", key="update_payment_btn"):
                                try:
                                    db.edit_payment(edit_pay_id, pay_passid, edit_pay_amount, edit_pay_date, edit_pay_comments or None)
                                    st.success("Payment updated. Trip payments recalculated.")
                                    clear_data_cache()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update payment: {e}")

    # --- Tab 6: Group Access ------------------------------------------------
    with tab_group_access:
        st.markdown("### Group Access Control")
        st.write("Assign yourself to groups so you can see and manage their passengers.")

        all_groups = get_groups()
        driver_group_ids = get_driver_group_ids(driver_id)
        my_groups = [g for g in all_groups if g["groupid"] in driver_group_ids]
        available_groups = [g for g in all_groups if g["groupid"] not in driver_group_ids]

        # --- Assign to an existing group ---
        st.markdown("#### Assign to a Group")
        if available_groups:
            assign_map = {
                f"{g['groupname']} (R{(g.get('groupamount') or 0):.2f})": g
                for g in available_groups
            }
            assign_labels = list(assign_map.keys())
            selected_label = st.selectbox("Available groups", assign_labels, key="assign_group_select")
            if st.button("Assign Me to This Group", type="primary", key="assign_group_btn"):
                selected_group = assign_map[selected_label]
                try:
                    db.add_group_access(driver_id, selected_group["groupid"])
                    clear_data_cache()
                    st.success(f"Access granted to '{selected_group['groupname']}'.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
        else:
            if not all_groups:
                st.info("No groups exist yet. Create one below.")
            else:
                st.success("You have access to all available groups.")

        # --- Create a new group ---
        st.write("")
        st.markdown("#### Create a New Group")
        with st.expander("Click to create a new group"):
            ng_col1, ng_col2, ng_col3 = st.columns(3)
            with ng_col1:
                ng_name = st.text_input("Group Name *", key="ng_name")
            with ng_col2:
                ng_amount = st.number_input("Trip Rate (R)", min_value=0.0, step=0.5, value=0.0, key="ng_amount")
            with ng_col3:
                ng_abbr = st.text_input("Abbreviation *", placeholder="e.g. ABS", key="ng_abbr")
            if st.button("Create Group & Grant Access", type="primary", key="add_group_btn"):
                if not ng_name.strip() or not ng_abbr.strip():
                    st.warning("Group Name and Abbreviation are required.")
                else:
                    try:
                        result = db.add_group(ng_name.strip(), ng_amount, ng_abbr.strip().upper())
                        new_group_id = result[0]["groupid"] if result else None
                        if new_group_id:
                            db.add_group_access(driver_id, new_group_id)
                            clear_data_cache()
                            st.success(f"Group '{ng_name.strip()}' created and access granted.")
                            st.rerun()
                        else:
                            st.warning("Group created but could not determine group ID for access grant.")
                    except Exception as e:
                        st.error(f"Failed to create group: {e}")

        # --- Current access with remove buttons ---
        st.write("")
        st.markdown("---")
        st.markdown("#### Your Current Groups")
        if not my_groups:
            st.info("You don't have access to any groups yet. Assign yourself to one above.")
        else:
            for g in my_groups:
                rg_col1, rg_col2 = st.columns([4, 1])
                with rg_col1:
                    st.write(f"**{g['groupname']}** — R{(g.get('groupamount') or 0):.2f} per trip (Abbrev: {g.get('groupAbrivation', 'N/A')})")
                with rg_col2:
                    if st.button("Remove", key=f"rm_group_{g['groupid']}"):
                        try:
                            db.remove_group_access(driver_id, g["groupid"])
                            clear_data_cache()
                            st.success(f"Access removed from '{g['groupname']}'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

    # --- Tab 7: Passenger Schedule ------------------------------------------
    with tab_pschedule:
        st.markdown("### Passenger Knock-off Schedule")

        # Always show the current week
        ps_week_start = get_week_start()
        ps_wdates = week_dates(ps_week_start)
        ps_week_end = ps_wdates[6]
        st.markdown(
            f"**Week: {ps_week_start.strftime('%d %b %Y')} – {ps_week_end.strftime('%d %b %Y')}**"
        )
        st.write("")

        # ── Section A: My Weekly Availability ────────────────────────────────
        st.markdown("#### My Weekly Availability")
        st.write(
            "Check the days you **will** be available. "
            "Uncheck a day to mark it unavailable — you can then specify who "
            "is affected, a time range, and an optional comment. "
            "Past days are locked."
        )

        today_dow = date.today().weekday()  # 0=Mon … 6=Sun

        # Build a lookup of ALL this driver's saved availability rows keyed by
        # (day_of_week, group_id) — only keep rows for today or future days.
        all_drv_avail = _load_driver_weekly_availability()
        avail_by_day_group = {}
        for a in all_drv_avail:
            if a.get("driverid") == driver_id:
                dow_val = a["day_of_week"]
                # Skip rows for days that have already passed this week
                if dow_val < today_dow:
                    continue
                avail_by_day_group[(dow_val, a.get("group_id"))] = a

        # Helper: return the saved row for a day — tries specific group first,
        # then falls back to the all-groups (None) row.
        def _saved_row(dow, group_id):
            return avail_by_day_group.get((dow, group_id)) or avail_by_day_group.get((dow, None)) or {}

        # Build group options (used inside each day's expander)
        avail_groups = get_groups_for_driver(driver_id)
        avail_group_opts = {"All Groups": None}
        for g in avail_groups:
            avail_group_opts[g["groupname"]] = g["groupid"]

        # Checkboxes — one per day.
        # Past days are shown as disabled. Today + future days are editable.
        # The "available" state is taken from any saved row for that day
        # (all-groups takes precedence as the base).
        new_avail_checked = {}
        avail_cols = st.columns(7)
        for dow in range(7):
            is_past = dow < today_dow
            # Find base available state: prefer all-groups row, else any row
            base_row = avail_by_day_group.get((dow, None), {})
            if not base_row:
                # Fall back to any saved row for this day
                base_row = next(
                    (v for (d, _), v in avail_by_day_group.items() if d == dow), {}
                )
            is_available = base_row.get("available", True) if isinstance(base_row, dict) else True

            with avail_cols[dow]:
                if is_past:
                    # Render as disabled — show current state but no interaction
                    st.checkbox(
                        f"{DAYS_OF_WEEK[dow]}\n{ps_wdates[dow].strftime('%d %b')}",
                        value=is_available,
                        key=f"drv_avail_chk_{dow}",
                        disabled=True,
                    )
                    new_avail_checked[dow] = is_available  # keep saved state for save loop
                else:
                    new_avail_checked[dow] = st.checkbox(
                        f"{DAYS_OF_WEEK[dow]}\n{ps_wdates[dow].strftime('%d %b')}",
                        value=is_available,
                        key=f"drv_avail_chk_{dow}",
                    )

        # For each unchecked day that is today or future, show the detail expander
        new_avail_details = {}   # dow → {"group_id", "time_from", "time_to", "comments"}
        for dow in range(7):
            is_past = dow < today_dow
            if is_past:
                continue  # no expander for past days
            if not new_avail_checked[dow]:
                with st.expander(
                    f"🚫 {DAYS_OF_WEEK[dow]} ({ps_wdates[dow].strftime('%d %b')}) — unavailability details",
                    expanded=True,
                ):
                    st.caption("Leave the time range blank to mark the whole day as unavailable.")

                    # Pre-select group from whichever saved unavailable row exists for this day
                    saved_gid = None
                    for (d, gid), r in avail_by_day_group.items():
                        if d == dow and not r.get("available", True):
                            saved_gid = gid
                            break
                    saved_label = next(
                        (lbl for lbl, gid in avail_group_opts.items() if gid == saved_gid),
                        "All Groups",
                    )
                    sel_group_label = st.selectbox(
                        "Applies to",
                        list(avail_group_opts.keys()),
                        index=list(avail_group_opts.keys()).index(saved_label),
                        key=f"drv_avail_scope_{dow}",
                    )
                    day_group_id = avail_group_opts[sel_group_label]

                    # Pre-populate from the saved row for this (dow, group_id)
                    saved_row = _saved_row(dow, day_group_id)
                    saved_tf = (saved_row.get("time_from") or "")[:5]
                    saved_tt = (saved_row.get("time_to")   or "")[:5]
                    saved_cm =  saved_row.get("comments",  "") or ""

                    det_c1, det_c2, det_c3 = st.columns([1, 1, 2])
                    with det_c1:
                        tf = st.text_input(
                            "From (HH:MM)",
                            value=saved_tf,
                            placeholder="08:00",
                            key=f"drv_tf_{dow}",
                        )
                    with det_c2:
                        tt = st.text_input(
                            "To (HH:MM)",
                            value=saved_tt,
                            placeholder="12:00",
                            key=f"drv_tt_{dow}",
                        )
                    with det_c3:
                        cm = st.text_input(
                            "Comment (optional)",
                            value=saved_cm,
                            placeholder="e.g. Doctor's appointment",
                            key=f"drv_cm_{dow}",
                        )

                new_avail_details[dow] = {
                    "group_id":  day_group_id,
                    "time_from": tf.strip() or None,
                    "time_to":   tt.strip() or None,
                    "comments":  cm.strip() or None,
                }

        if st.button("Update My Availability", type="primary", key="update_drv_avail_btn"):
            errors = []
            for dow in range(7):
                if dow < today_dow:
                    continue  # never write past days
                avail = new_avail_checked[dow]
                details = new_avail_details.get(dow, {})
                day_gid = details.get("group_id")

                old_row = avail_by_day_group.get((dow, day_gid), {})
                old_avail = old_row.get("available", True) if isinstance(old_row, dict) else True
                old_tf = (old_row.get("time_from") or "")[:5] if isinstance(old_row, dict) else ""
                old_tt = (old_row.get("time_to")   or "")[:5] if isinstance(old_row, dict) else ""
                old_cm =  old_row.get("comments",  "")        if isinstance(old_row, dict) else ""

                new_tf = details.get("time_from") or ""
                new_tt = details.get("time_to")   or ""
                new_cm = details.get("comments")  or ""

                changed = (
                    avail != old_avail
                    or new_tf != old_tf
                    or new_tt != old_tt
                    or new_cm != old_cm
                )
                if changed:
                    try:
                        db.upsert_driver_weekly_availability(
                            driver_id, dow, avail,
                            time_from=details.get("time_from"),
                            time_to=details.get("time_to"),
                            comments=details.get("comments"),
                            group_id=day_gid,
                        )
                    except Exception as e:
                        errors.append(f"{DAYS_OF_WEEK[dow]}: {e}")

            if errors:
                for err in errors:
                    st.error(f"Failed — {err}")
            else:
                clear_data_cache()
                st.success("Availability updated.")
                st.rerun()

        st.write("")
        st.markdown("---")

        # ── Section B: Passenger Knock-off Times ─────────────────────────────
        st.markdown("#### Passenger Knock-off Times")

        # Group filter
        all_psched_passengers = get_passengers_for_driver(driver_id)
        driver_groups_for_filter = get_groups_for_driver(driver_id)
        group_filter_opts = {"All Groups": None}
        for g in driver_groups_for_filter:
            group_filter_opts[g["groupname"]] = g["groupid"]

        selected_group_label = st.selectbox(
            "Show passengers from",
            list(group_filter_opts.keys()),
            key="pschedule_group_filter",
        )
        filter_gid = group_filter_opts[selected_group_label]

        if filter_gid is not None:
            display_passengers = [p for p in all_psched_passengers if p.get("group_id") == filter_gid]
        else:
            display_passengers = all_psched_passengers

        st.write(
            "Each passenger's knock-off time for the week. "
            "Times in brackets are group defaults; plain times are custom overrides."
        )

        if not display_passengers:
            st.info("No passengers in the selected group yet.")
        else:
            sched_rows = []
            psched_cached = _load_passenger_schedules()

            for p in display_passengers:
                row = {"Passenger": f"{p['user_id']} — {p.get('full_names', '')}"}

                for dow in range(7):
                    custom_time = get_knockoff_time_for_passenger(p["user_id"], dow)
                    has_custom = any(
                        s.get("user_id") == p["user_id"] and s.get("day_of_week") == dow
                        for s in psched_cached
                    )
                    if custom_time:
                        row[DAYS_OF_WEEK[dow][:3]] = custom_time if has_custom else f"({custom_time})"
                    else:
                        row[DAYS_OF_WEEK[dow][:3]] = "—"
                sched_rows.append(row)

            # Date sub-header row
            date_row = {"Passenger": "Date"}
            for dow in range(7):
                date_row[DAYS_OF_WEEK[dow][:3]] = ps_wdates[dow].strftime("%d %b")
            sched_rows.insert(0, date_row)

            render_table(sched_rows)


# ---------------------------------------------------------------------------
# Main routing
# ---------------------------------------------------------------------------
if st.session_state.role is None:
    landing_page()
elif st.session_state.role == "passenger":
    passenger_view()
elif st.session_state.role == "driver":
    if st.session_state.driver_logged_in:
        driver_dashboard()
    else:
        driver_login_page()
