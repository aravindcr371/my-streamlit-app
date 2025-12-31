
import os
import streamlit as st
import pandas as pd
from datetime import datetime, date as date_cls, timedelta
import altair as alt
from supabase import create_client

# ------------------ SUPABASE SETUP ------------------
# TIP: Prefer environment variables or st.secrets in production
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"  # anon key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TEAM = "Production Design"
MEMBERS = ["-- Select --", "Vinitha", "Vadivel", "Nirmal", "Karthi", "Jayaprakash", "Vidhya"]
COMPONENTS = ["-- Select --", "Content Email", "Digital Banners", "Weekend", "Edits", "Break",
              "Others", "Meeting", "Innovation", "Round 2 Banners", "Leave",
              "Internal Requests", "Promo Creative", "Social Requests",
              "Landing Pages", "Category Banners", "Image Requests"]

RESET_KEYS = [
    "date_field", "member_field", "component_field",
    "tickets_field", "banners_field", "sku_field", "pages_field",
    "hours_field", "minutes_field", "comments_field"
]

if st.session_state.get("do_reset"):
    for k in RESET_KEYS:
        st.session_state.pop(k, None)
    st.session_state["do_reset"] = False

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

        # Row: Tickets & Banners
        col3, col4 = st.columns(2)
        with col3:
            tickets = st.number_input("Tickets", min_value=0, step=1, key="tickets_field")
        with col4:
            banners = st.number_input("Banners", min_value=0, step=1, key="banners_field")

        # NEW Row: SKU & Pages (after Tickets & Banners)
        col3b, col4b = st.columns(2)
        with col3b:
            sku = st.number_input("SKU", min_value=0, step=1, key="sku_field")
        with col4b:
            pages = st.number_input("Pages", min_value=0, step=1, key="pages_field")

        # Row: Hours & Minutes
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
                "date": d.isoformat(),                 # YYYY-MM-DD
                "week": d.isocalendar()[1],            # integer week number
                "month": d.strftime("%B"),
                "member": member,
                "component": component.strip(),
                "tickets": int(tickets),
                "banners": int(banners),
                "sku": int(sku),                       # NEW
                "pages": int(pages),                   # NEW
                "duration": duration_minutes,          # minutes
                "comments": (comments.strip() if comments else None)
            }

            try:
                # If you added a uniqueness constraint, switch to upsert with on_conflict
                # res = supabase.table("creative").upsert(new_row, on_conflict=["team","member","component","date"]).execute()
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

    # Read back and show table
    try:
        response = supabase.table("creative").select("*").execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df = pd.DataFrame()

    if not df.empty:
        # Put 'team' as starting column if present
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
        # Normalize date to pandas datetime
        df["date"] = pd.to_datetime(df.get("date"), errors="coerce")

        # Ensure numeric fields for charts
        for c in ["tickets", "banners", "sku", "pages", "duration"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        view = st.radio("Select View", ["Week-to-Date", "Month-to-Date", "Previous Month"])

        # Example simple KPI cards (customize as needed)
        if view == "Week-to-Date":
            today = pd.Timestamp(datetime.now().date())
            start = today - pd.Timedelta(days=today.weekday())
            period = df[(df["date"] >= start) & (df["date"] <= today)]
        elif view == "Month-to-Date":
            today = pd.Timestamp(datetime.now().date())
            start = pd.Timestamp(datetime(today.year, today.month, 1))
            period = df[(df["date"] >= start) & (df["date"] <= today)]
        else:  # Previous Month
            today = pd.Timestamp(datetime.now().date())
            prev_month = (today.month - 1) or 12
            year = today.year if today.month > 1 else today.year - 1
            start = pd.Timestamp(datetime(year, prev_month, 1))
            end = pd.Timestamp(datetime(year, prev_month, 1)) + pd.offsets.MonthEnd(1)
            period = df[(df["date"] >= start) & (df["date"] <= end)]

        if period.empty:
            st.info("No data available for the selected period")
        else:
            # Example totals
            total_tickets = int(period["tickets"].sum()) if "tickets" in period.columns else 0
            total_banners = int(period["banners"].sum()) if "banners" in period.columns else 0
            total_sku = int(period["sku"].sum()) if "sku" in period.columns else 0
            total_pages = int(period["pages"].sum()) if "pages" in period.columns else 0

            st.metric("Tickets", total_tickets)
            st.metric("Banners", total_banners)
            st.metric("SKU", total_sku)
            st.metric("Pages", total_pages)

            # Simple chart example (banners by date)
            if "banners" in period.columns:
                line = alt.Chart(period).mark_line(point=True).encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("banners:Q", title="Banners"),
                    color=alt.value("#1f77b4")
                ).properties(height=300)
                st.altair_chart(line, use_container_width=True)

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

        # Normalize date and numeric columns
        df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
        for c in ["duration"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df["hours"] = df["duration"] / 60.0

        # Productive excludes Break and Leave
        df["productive_hours"] = df.apply(
            lambda r: 0 if str(r.get("component")) in ["Break", "Leave"] else r["hours"], axis=1
        )
        # Leave hours directly from component
        df["leave_hours"] = df.apply(
            lambda r: r["hours"] if str(r.get("component")) == "Leave" else 0, axis=1
        )

        view = st.radio("Select Period", ["Last Week", "Week-to-Date", "Last Month", "Month-to-Date"])

        today = datetime.now().date()
        current_weekday = today.weekday()  # Mon=0 ... Sun=6
        current_month = today.month
        current_year = today.year

        def weekdays_between(start, end):
            days = pd.date_range(start, end, freq="D")
            return [d for d in days if d.weekday() < 5]

        if view == "Week-to-Date":
            start = today - timedelta(days=current_weekday)
            weekdays = weekdays_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        elif view == "Last Week":
            start = today - timedelta(days=current_weekday + 7)
            end = start + timedelta(days=4)  # Mon–Fri
            weekdays = weekdays_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        elif view == "Month-to-Date":
            start = datetime(current_year, current_month, 1).date()
            weekdays = weekdays_between(start, today)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        else:  # Last Month
            prev_month = current_month - 1 or 12
            year = current_year if current_month > 1 else current_year - 1
            start = datetime(year, prev_month, 1).date()
            if prev_month == 12:
                end = datetime(year, 12, 31).date()
            else:
                end = (datetime(year, prev_month + 1, 1) - timedelta(days=1)).date()
            weekdays = weekdays_between(start, end)
            period_df = df[df["date"].dt.normalize().isin(weekdays)]
            baseline_hours_period = len(weekdays) * 8

        if period_df.empty:
            st.info("No data for the selected period.")
        else:
            agg = period_df.groupby("member").agg(
                utilized_hours=("productive_hours", "sum"),
                leave_hours=("leave_hours", "sum")
            ).reset_index()

            agg["total_hours"] = baseline_hours_period - agg["leave_hours"]
            agg["utilization_pct"] = (
                (agg["utilized_hours"] / agg["total_hours"]).where(agg["total_hours"] > 0, 0) * 100
            ).round(1)

            member_stats = agg.rename(columns={
                "member": "Name",
                "leave_hours": "Leave hours",
                "utilized_hours": "Utilized hours",
                "total_hours": "Baseline hours",
                "utilization_pct": "Utilization (%)"
            })

            st.dataframe(member_stats)
