import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import altair as alt
from supabase import create_client

# ------------------ SUPABASE SETUP ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"   # TODO: replace
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"                      # TODO: replace
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
PUBLIC_HOLIDAYS = {
    date(2024, 11, 14),
    date(2024, 12, 25),
    date(2025, 1, 1),
    # Add more dates as needed
}

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Production Design", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True, key="team_display")
    # ... (form logic unchanged)

# ------------------ TAB 2 ------------------
with tab2:
    st.title("Visuals Dashboard")
    # ... (visuals logic unchanged)

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

        # Utilization excludes Break and Leave
        df["utilization_hours"] = df.apply(
            lambda r: 0 if r["component"] in ["Break","Leave"] else r["hours"], axis=1
        )
        # Occupancy excludes Break, Leave, and Meeting
        df["occupancy_hours"] = df.apply(
            lambda r: 0 if r["component"] in ["Break","Leave","Meeting"] else r["hours"], axis=1
        )
        df["leave_hours"] = df.apply(lambda r: r["hours"] if r["component"]=="Leave" else 0, axis=1)

        today = date.today()
        current_weekday = today.weekday()
        current_month = today.month
        current_year = today.year

        def end_of_month(y: int, m: int) -> date:
            if m == 12:
                return date(y, 12, 31)
            return (date(y, m + 1, 1) - timedelta(days=1))

        def working_days_between(start: date, end: date):
            days = pd.date_range(start, end, freq="D")
            return [d.normalize() for d in days if d.weekday() < 5 and d.date() not in PUBLIC_HOLIDAYS]

        # Build dropdown options
        df["year_month"] = df["date"].dt.to_period("M")
        available_months = sorted(df["year_month"].unique())
        available_months = [m for m in available_months if (m.year > 2024 or (m.year == 2024 and m.month >= 11))]
        month_labels = [f"{m.strftime('%B %Y')}" for m in available_months]

        options = ["Current Week", "Previous Week", "Current Month", "Previous Month"] + month_labels
        choice = st.selectbox("Select period", options)

        # Determine weekdays for selected period
        if choice == "Current Week":
            start = today - timedelta(days=current_weekday)
            end = today
            weekdays = working_days_between(start, end)
        elif choice == "Previous Week":
            start = today - timedelta(days=current_weekday + 7)
            end = start + timedelta(days=4)
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
            sel_period = available_months[month_labels.index(choice)]
            sel_year, sel_mon = sel_period.year, sel_period.month
            start = date(sel_year, sel_mon, 1)
            end = end_of_month(sel_year, sel_mon)
            weekdays = working_days_between(start, end)

        # Filter df to period weekdays
        period_df = df[df["date"].dt.normalize().isin(weekdays)]
        baseline_hours_period = len(weekdays) * 8

        if period_df.empty:
            st.info("No data for the selected period.")
        else:
            # Aggregate both utilization and occupancy
            agg = period_df.groupby("member").agg(
                utilized_hours=("utilization_hours","sum"),
                occupied_hours=("occupancy_hours","sum"),
                leave_hours=("leave_hours","sum")
            ).reset_index()

            agg["total_hours"] = baseline_hours_period - agg["leave_hours"]
            agg["utilization_%"] = (
                (agg["utilized_hours"]/agg["total_hours"]).where(agg["total_hours"]>0,0)*100
            ).round(1)
            agg["occupancy_%"] = (
                (agg["occupied_hours"]/agg["total_hours"]).where(agg["total_hours"]>0,0)*100
            ).round(1)

            merged_stats = agg.rename(columns={
                "member":"Name",
                "leave_hours":"Leave Hours",
                "utilized_hours":"Utilized Hours",
                "occupied_hours":"Occupied Hours",
                "total_hours":"Total Hours",
                "utilization_%":"Utilization %",
                "occupancy_%":"Occupancy %"
            })

            st.subheader("Member Utilization & Occupancy")
            st.dataframe(
                merged_stats[["Name","Total Hours","Leave Hours","Utilized Hours","Occupied Hours","Utilization %","Occupancy %"]],
                use_container_width=True
            )

            # Team-level summary
            team_total = merged_stats["Total Hours"].sum()
            team_leave = merged_stats["Leave Hours"].sum()
            team_utilized = merged_stats["Utilized Hours"].sum()
            team_occupied = merged_stats["Occupied Hours"].sum()
            team_util_pct = (team_utilized/team_total*100) if team_total>0 else 0
            team_occ_pct = (team_occupied/team_total*100) if team_total>0 else 0

            team_df = pd.DataFrame({
                "Team":[TEAM],
                "Total Hours":[round(team_total,2)],
                "Leave Hours":[round(team_leave,2)],
                "Utilized Hours":[round(team_utilized,2)],
                "Occupied Hours":[round(team_occupied,2)],
                "Utilization %":[round(team_util_pct,1)],
                "Occupancy %":[round(team_occ_pct,1)]
            })

            st.subheader("Team Utilization & Occupancy")
            st.dataframe(team_df, use_container_width=True)
