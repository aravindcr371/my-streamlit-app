import streamlit as st
import pandas as pd
from datetime import datetime, date as date_cls, timedelta
import altair as alt
from supabase import create_client

# ------------------ SUPABASE SETUP ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"  # replace with your anon key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TEAM = "Production Design"
MEMBERS = ["-- Select --","Vinitha","Vadivel","Nirmal","Karthi","Jayaprakash","Vidhya"]
COMPONENTS = ["-- Select --","Content Email","Digital Banners","Weekend","Edits","Break",
              "Others","Meeting","Innovation","Round 2 Banners","Leave",
              "Internal Requests","Promo Creative","Social Requests",
              "Landing Pages","Category Banners","Image Requests"]

RESET_KEYS = [
    "date_field", "member_field", "component_field",
    "tickets_field", "banners_field", "hours_field",
    "minutes_field", "comments_field"
]

if st.session_state.get("do_reset"):
    for k in RESET_KEYS:
        st.session_state.pop(k, None)
    st.session_state["do_reset"] = False

# ------------------ Public Holidays ------------------
# Hard-code public holidays here as a set of datetime.date objects
PUBLIC_HOLIDAYS = {
    date(2024, 12, 25),  # Example: Dec 25, 2024
    date(2025, 1, 1),    # Example: Jan 1, 2025
    # Add more dates as needed
}

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Production Design", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True, key="team_display")

    with st.form(key="entry_form", clear_on_submit=False):
        date_value = st.date_input("Date", key="date_field")
        col1, col2 = st.columns(2)
        with col1:
            member = st.selectbox("Member", MEMBERS, key="member_field")
        with col2:
            component = st.selectbox("Component", COMPONENTS, key="component_field")

        col3, col4 = st.columns(2)
        with col3:
            tickets = st.number_input("Tickets", min_value=0, step=1, key="tickets_field")
        with col4:
            banners = st.number_input("Banners", min_value=0, step=1, key="banners_field")

        col5, col6 = st.columns(2)
        with col5:
            hours = st.selectbox("Hours", range(24), key="hours_field")
        with col6:
            minutes = st.selectbox("Minutes", range(60), key="minutes_field")

        comments = st.text_area("Comments", key="comments_field")

        submitted = st.form_submit_button("Submit")

    if submitted:
        if isinstance(date_value, (datetime, date_cls)) and member != "-- Select --" and component != "-- Select --":
            duration_minutes = int(hours) * 60 + int(minutes)
            d = date_value if isinstance(date_value, date_cls) else date_value.date()
            new_row = {
                "team": TEAM,
                "date": d.isoformat(),
                "week": d.isocalendar()[1],
                "month": d.strftime("%B"),
                "member": member,
                "component": component,
                "tickets": int(tickets),
                "banners": int(banners),
                "duration": duration_minutes,
                "comments": comments.strip() if comments else None
            }
            try:
                res = supabase.table("creative").insert(new_row).execute()
                if res.data:
                    st.success("Saved successfully")
                    st.session_state["do_reset"] = True
                    st.rerun()
                else:
                    st.warning("Insert may not have returned data")
            except Exception as e:
                st.error(f"Error inserting: {e}")
        else:
            st.warning("Please select a member and component, and pick a date before submitting.")

    try:
        response = supabase.table("creative").select("*").execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df = pd.DataFrame()

    if not df.empty:
        if "team" in df.columns:
            start_index = df.columns.get_loc("team")
            df = df.iloc[:, start_index:]
        st.dataframe(df)

# ------------------ TAB 2 ------------------
with tab2:
    st.title("Visuals Dashboard")
    try:
        response = supabase.table("creative").select("*").execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.info("No data available")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        view = st.radio("Select View", ["Week-to-Date", "Month-to-Date", "Previous Month"])
        # (Visuals logic same as before...)

# ------------------ TAB 3 ------------------
with tab3:
    st.title("Utilization & Occupancy")

    try:
        response = supabase.table("creative").select("*").execute()
        raw = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        raw = pd.DataFrame()

    if raw.empty:
        st.info("No data available")
    else:
        df = raw.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["hours"] = df["duration"] / 60.0

        df["productive_hours"] = df.apply(lambda r: 0 if r["component"] in ["Break","Leave"] else r["hours"], axis=1)
        df["leave_hours"] = df.apply(lambda r: r["hours"] if r["component"]=="Leave" else 0, axis=1)

        view = st.radio("Select Period", ["Last Week","Week-to-Date","Last Month","Month-to-Date"])

        today = datetime.now().date()
        current_weekday = today.weekday()
        current_month = today.month
        current_year = today.year

        def working_days_between(start, end):
            days = pd.date_range(start, end, freq="D")
            return [d.normalize() for d in days if d.weekday() < 5 and d.date() not in PUBLIC_HOLIDAYS]

        if view == "Week-to-Date":
            start = today - timedelta(days=current_weekday)
            weekdays = working_days_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        elif view == "Last Week":
            start = today - timedelta(days=current_weekday + 7)
            end = start + timedelta(days=4)
            weekdays = working_days_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        elif view == "Month-to-Date":
            start = datetime(current_year, current_month, 1).date()
            weekdays = working_days_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        else:  # Last Month
            prev_month = current_month - 1 if current_month > 1 else 12
            year = current_year if current_month > 1 else current_year - 1
            start = datetime(year, prev_month, 1).date()
            if prev_month == 12:
                end = datetime(year, 12, 31).date()
            else:
                end = (datetime(year, prev_month + 1, 1) - timedelta(days=1)).date()
            weekdays = working_days_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        if period_df.empty:
            st.info("No data for the selected period.")
        else:
            agg = period_df.groupby("member").agg(
                utilized_hours=("productive_hours","sum"),
                leave_hours=("leave_hours","sum")
            ).reset_index()

            agg["total_hours"] = baseline_hours_period - agg["leave_hours"]
