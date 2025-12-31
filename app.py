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

# Keys used by the form widgets
RESET_KEYS = [
    "date_field", "member_field", "component_field",
    "tickets_field", "banners_field", "hours_field",
    "minutes_field", "comments_field"
]

# If a reset was requested on the previous run, clear the form keys BEFORE rendering widgets
if st.session_state.get("do_reset"):
    for k in RESET_KEYS:
        st.session_state.pop(k, None)
    st.session_state["do_reset"] = False

# ------------------ Hard-coded working days for completed months ------------------
# Use these only for "Last Month" baseline (completed months)
WORKING_DAYS = {
    (2024, 11): 19,  # November 2024 → 19 days → 152 hours
    (2024, 12): 22,  # December 2024 → 22 days → 176 hours
    (2025, 1): 23    # January 2025 → 23 days → 184 hours
}

def baseline_hours_for_month(year: int, month: int) -> int:
    """Baseline hours for a completed month from hard-coded working days."""
    return WORKING_DAYS.get((year, month), 20) * 8  # default 20 days if missing

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Production Design", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True, key="team_display")

    # Use a form to group inputs and submit together
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
        # Validate required fields
        if isinstance(date_value, (datetime, date_cls)) and member != "-- Select --" and component != "-- Select --":
            duration_minutes = int(hours) * 60 + int(minutes)
            # Normalize date_value to a date object
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
                    # Mark for reset and rerun so widgets are re-created with fresh state
                    st.session_state["do_reset"] = True
                    st.rerun()
                else:
                    st.warning("Insert may not have returned data")
            except Exception as e:
                st.error(f"Error inserting: {e}")
        else:
            st.warning("Please select a member and component, and pick a date before submitting.")

    # Fetch all rows from Supabase
    try:
        response = supabase.table("creative").select("*").execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df = pd.DataFrame()

    if not df.empty:
        # Show only columns starting from "team"
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
        # Ensure date column is datetime for grouping/encoding
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        view = st.radio("Select View", ["Week-to-Date", "Month-to-Date", "Previous Month"])

        # ---------- FILTER ----------
        if view == "Week-to-Date":
            current_week = datetime.now().isocalendar()[1]
            filtered = df[df["week"] == current_week]
            grouped = filtered.groupby("date")[["tickets","banners"]].sum().reset_index()
            x_field = alt.X("date:T", title="Date")
        elif view == "Month-to-Date":
            current_month = datetime.now().month
            filtered = df[df["date"].dt.month == current_month]
            grouped = filtered.groupby("week")[["tickets","banners"]].sum().reset_index()
            x_field = alt.X("week:O", title="Week Number")
        else:
            prev_month = datetime.now().month - 1 or 12
            filtered = df[df["date"].dt.month == prev_month]
            grouped = filtered.groupby("week")[["tickets","banners"]].sum().reset_index()
            x_field = alt.X("week:O", title="Week Number")

        # ---------- TICKETS ----------
        tickets_chart = alt.Chart(grouped).mark_bar(color="steelblue").encode(
            x=x_field,
            y=alt.Y("tickets:Q", title="Tickets"),
            tooltip=["tickets"]
        )
        tickets_labels = alt.Chart(grouped).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x=x_field,
            y="tickets:Q",
            text="tickets:Q"
        )
        st.altair_chart(tickets_chart + tickets_labels, use_container_width=True)

        # ---------- BANNERS ----------
        banners_chart = alt.Chart(grouped).mark_bar(color="orange").encode(
            x=x_field,
            y=alt.Y("banners:Q", title="Banners"),
            tooltip=["banners"]
        )
        banners_labels = alt.Chart(grouped).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x=x_field,
            y="banners:Q",
            text="banners:Q"
        )
        st.altair_chart(banners_chart + banners_labels, use_container_width=True)

        # ---------- MEMBER-WISE ----------
        st.subheader("👥 Member-wise Tickets")
        member_grp = filtered.groupby("member")[["tickets","banners"]].sum().reset_index()

        tickets_chart = alt.Chart(member_grp).mark_bar(color="steelblue").encode(
            x=alt.X("member:N", title="Member"),
            y=alt.Y("tickets:Q", title="Total Tickets"),
            tooltip=["member", "tickets"]
        )
        tickets_labels = alt.Chart(member_grp).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x="member:N",
            y="tickets:Q",
            text="tickets:Q"
        )
        st.altair_chart(tickets_chart + tickets_labels, use_container_width=True)

        st.subheader("👥 Member-wise Banners")
        banners_chart = alt.Chart(member_grp).mark_bar(color="orange").encode(
            x=alt.X("member:N", title="Member"),
            y=alt.Y("banners:Q", title="Total Banners"),
            tooltip=["member", "banners"]
        )
        banners_labels = alt.Chart(member_grp).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x="member:N",
            y="banners:Q",
            text="banners:Q"
        )
        st.altair_chart(banners_chart + banners_labels, use_container_width=True)

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

        # Period selection
        view = st.radio("Select Period", ["Last Week","Week-to-Date","Last Month","Month-to-Date"])

        today = datetime.now().date()
        current_weekday = today.weekday()  # Mon=0 ... Sun=6
        current_month = today.month
        current_year = today.year

        # Helper: get only weekdays (Mon-Fri) between two dates inclusive
        def weekdays_between(start, end):
            days = pd.date_range(start, end, freq="D")
            return [d.normalize() for d in days if d.weekday() < 5]

        # Build period date set and baseline hours
        if view == "Week-to-Date":
            # Monday of current week → today
            start = today - timedelta(days=current_weekday)
            weekdays = weekdays_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8  # dynamic WTD baseline

        elif view == "Last Week":
            # Monday–Friday of previous week
            start = today - timedelta(days=current_weekday + 7)
            end = start + timedelta(days=4)
            weekdays = weekdays_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8  # dynamic last-week baseline

        elif view == "Month-to-Date":
            # Weekdays from 1st of current month → today (dynamic)
            start = datetime(current_year, current_month, 1).date()
            weekdays = weekdays_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8  # dynamic MTD baseline

        else:  # Last Month (use hard-coded baseline)
            prev_month = current_month - 1 if current_month > 1 else 12
            year = current_year if current_month > 1 else current_year - 1
            start = datetime(year, prev_month, 1).date()
            if prev_month == 12:
                end = datetime(year, 12, 31).date()
            else:
                end = (datetime(year, prev_month + 1, 1) - timedelta(days=1)).date()
            weekdays = weekdays_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = baseline_hours_for_month(year, prev_month)  # hard-coded completed month

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

            st.subheader("Member Utilization")
            st.dataframe(member_stats[["Name", "Total hours", "Leave hours", "Utilized hours", "Utilization %"]])

            # Team-level aggregation
            team_total_hours = member_stats["Total hours"].sum()
            team_leave_hours = member_stats["Leave hours"].sum()
            team_utilized_hours = member_stats["Utilized hours"].sum()
            team_utilization_pct = (team_utilized_hours / team_total_hours * 100) if team_total_hours > 0 else 0

            team_stats = pd.DataFrame({
                "Team": [TEAM],
                "Total hours": [team_total_hours],
                "Leave hours": [team_leave_hours],
                "Utilized hours": [team_utilized_hours],
                "Utilization %": [round(team_utilization_pct, 1)]
            })

            st.subheader("Team Utilization")
            st.dataframe(team_stats)
