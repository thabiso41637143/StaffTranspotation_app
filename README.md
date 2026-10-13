# StaffTranspotation_app

A staff transportation register built with Python and Streamlit, backed by Supabase (PostgreSQL).

## Features

- **Passenger portal** — look up trip history, amounts owed, knock-off schedule, and driver availability
- **Driver portal** — manage passengers, capture trips, record payments, and manage weekly availability
- **Group-based access control** — drivers are assigned to groups and only see their passengers
- **Knock-off schedules** — passengers set their own pick-up times; drivers see the full weekly schedule
- **Driver availability** — drivers mark unavailable days (with optional time range, group scope, and comments); passengers see this in real time

## Tech Stack

- [Streamlit](https://streamlit.io/) — front-end UI
- [Supabase](https://supabase.com/) — PostgreSQL database + Auth
- Python 3.11+

## Setup

1. Clone the repo
2. Create a `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-service-role-key
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the database migration scripts in the Supabase SQL Editor:
   - `create_new_tables.sql`
   - `create_trips_payment.sql`
   - `migrate_availability.sql`
5. Start the app:
   ```bash
   python -m streamlit run app.py
   ```

## Running on Windows (AppLocker environments)

If `streamlit run app.py` is blocked by Application Control policy, use:
```bash
python -m streamlit run app.py
```
