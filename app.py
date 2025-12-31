import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
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
# Hard-code public holidays (Mon–Fri will be counted, Saturdays/Sundays always ignored)
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
        if isinstance(date_value, (datetime, date)) and member != "-- Select --" and component != "-- Select --":
            duration_minutes = int(hours) * 60 + int(minutes)
            d = date_value if isinstance(date_value, date) else date_value.date()
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
        # Simple example charts (customize as needed)
        if view == "Week-to-Date":
            wk = datetime.now().isocalendar()[1]
            filtered = df[df["week"] == wk]
        elif view == "Month-to-Date":
            m = datetime.now().month
            filtered = df[df["date"].dt.month == m]
        else:
            prev_m = (datetime.now().month - 1) or 12
            filtered = df[df["date"].dt.month == prev_m]

        if filtered.empty:
            st.info("No visuals for selected view.")
        else:
            grouped = filtered.groupby("member")[["tickets","banners"]].sum().reset_index()
            chart_t = alt.Chart(grouped).mark_bar(color="steelblue").encode(
                x=alt.X("member:N", title="Member"),
                y=alt.Y("tickets:Q", title="Tickets"),
                tooltip=["member","tickets"]
            )
            chart_b = alt.Chart(grouped).mark_bar(color="orange").encode(
                x=alt.X("member:N", title="Member"),
                y=alt.Y("banners:Q", title="Banners"),
                tooltip=["member","banners"]
            )
            st.altair_chart(chart_t, use_container_width=True)
            st.altair_chart(chart_b, use_container_width=True)

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
        # Prepare data
        df = raw.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["hours"] = df["duration"] / 60.0

        # Productive excludes Break and Leave
        df["productive_hours"] = df.apply(lambda r: 0 if r["component"] in ["Break","Leave"] else r["hours"], axis=1)
        # Leave hours directly from component
        df["leave_hours"] = df.apply(lambda r: r["hours"] if r["component"] == "Leave" else 0, axis=1)

        # Current date context
        today = datetime.now().date()
        current_weekday = today.weekday()          # Mon=0 ... Sun=6
        current_month = today.month
        current_year = today.year
        iso_year = today.isocalendar()[0]
        iso_week = today.isocalendar()[1]

        # Helpers
        def end_of_month(y: int, m: int) -> date:
            if m == 12:
                return date(y, 12, 31)
            return (date(y, m + 1, 1) - timedelta(days=1))

        def working_days_between(start: date, end: date):
            days = pd.date_range(start, end, freq="D")
            return [d.normalize() for d in days if d.weekday() < 5 and d.date() not in PUBLIC_HOLIDAYS]

        # Build dropdown options (single selector)
        df["year_month"] = df["date"].dt.to_period("M")
        available_months = sorted(df["year_month"].unique())
        # Only months from Nov 2024 onwards
        available_months = [m for m in available_months if (m.year > 2024 or (m.year == 2024 and m.month >= 11))]
        month_labels = [f"{m.strftime('%B %Y')}" for m in available_months]

        options = ["Current Week", "Previous Week", "Current Month", "Previous Month"] + month_labels
        choice = st.selectbox("Select period", options)

        # Compute date range and filter df based on choice
        if choice == "Current Week":
            start = today - timedelta(days=current_weekday)
            end = today
            weekdays = working_days_between(start, end)

        elif choice == "Previous Week":
            start = today - timedelta(days=current_weekday + 7)  # previous Monday
            end = start + timedelta(days=4)                      # previous Friday
            weekdays = working_days_between(start, end)

        elif choice == "Current Month":
            start = date(current_year, current_month, 1)
            end = today
            weekdays = working_days_between(start, end)

        elif choice == "Previous Month":
            prev_month = current_month - 1 if current_month > 1 else 12
            prev_year = current_year if current_month > 1 else current_year - 1
            start = date(prev_year, prev_month, 1)
            end = end_of_month(prev_year, prev_month)
            weekdays = working_days_between(start, end)

        else:
            # A specific month label from data (e.g., "November 2024")
            sel_period = available_months[month_labels.index(choice)]
            sel_year, sel_mon = sel_period.year, sel_period.month
            start = date(sel_year, sel_mon, 1)
            end = end_of_month(sel_year, sel_mon)
            weekdays = working_days_between(start, end)

        # Filter df to only those weekdays
        period_df = df[df["date"].dt.normalize().isin(weekdays)]
        baseline_hours_period = len(weekdays) * 8

        if period_df.empty:
            st.info("No data for the selected period.")
        else:
            # Aggregate member-level metrics
            agg = period_df.groupby("member").agg(
                utilized_hours=("productive_hours", "sum"),
                leave_hours=("leave_hours", "sum")
            ).reset_index()

            # Total hours baseline per member = period baseline - leave hours
            agg["total_hours"] = baseline_hours_period - agg["leave_hours"]

            # Utilization % per member = utilized_hours / total_hours
            agg["utilization_pct"] = (
                (agg["utilized_hours"] / agg["total_hours"]).where(agg["total_hours"] > 0, 0) * 100
            ).round(1)

            # Final display columns
            member_stats = agg.rename(columns={
                "member": "Name",
                "leave_hours": "Leave hours",
                "utilized_hours": "Utilized hours",
                "total_hours": "Total hours",
                "utilization_pct": "Utilization %"
            })

            st.subheader("Member utilization")
            st.dataframe(member_stats[["Name", "Total hours", "Leave hours", "Utilized hours", "Utilization %"]],
                         use_container_width=True)

            # Team-level aggregation
            team_total_hours = member_stats["Total hours"].sum()
            team_leave_hours = member_stats["Leave hours"].sum()
            team_utilized_hours = member_stats["Utilized hours"].sum()
            team_utilization_pct = (team_utilized_hours / team_total_hours * 100) if team_total_hours > 0 else 0

            team_stats = pd.DataFrame({
                "Team": [TEAM],
                "Total hours": [round(team_total_hours, 2)],
                "Leave hours": [round(team_leave_hours, 2)],
                "Utilized hours": [round(team_utilized_hours, 2)],
                "Utilization %": [round(team_utilization_pct, 1)]
            })

            st.subheader("Team utilization")
            st.dataframe(team_stats, use_container_width=True)
