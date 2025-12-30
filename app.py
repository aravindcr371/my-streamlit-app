import streamlit as st
import pandas as pd
from datetime import datetime, date as date_cls
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

# ------------------ Hard-coded working days per month ------------------
WORKING_DAYS = {
    1: 20,  # January
    2: 19,  # February
    3: 22,  # March
    4: 21,  # April
    5: 22,  # May
    6: 21,  # June
    7: 23,  # July
    8: 22,  # August
    9: 21,  # September
    10: 22, # October
    11: 21, # November
    12: 22  # December
}

def baseline_hours_for_month(month: int) -> int:
    return WORKING_DAYS.get(month, 20) * 8

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
            new_row = {
                "team": TEAM,
                "date": (date_value if isinstance(date_value, date_cls) else date_value.date()).isoformat(),
                "week": (date_value if isinstance(date_value, date_cls) else date_value.date()).isocalendar()[1],
                "month": (date_value if isinstance(date_value, date_cls) else date_value.date()).strftime("%B"),
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
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.info("No data available")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["hours"] = df["duration"] / 60.0
        df["productive_hours"] = df.apply(lambda r: 0 if r["component"]=="Break" else r["hours"], axis=1)
        df["leave_hours"] = df.apply(lambda r: 8 if r["component"]=="Leave" else 0, axis=1)

        view = st.radio("Select Period", ["Last Week","Week-to-Date","Last Month","Month-to-Date"])

        current_week = datetime.now().isocalendar()[1]
        current_month = datetime.now().month

        if view=="Last Week":
            target_week = current_week-1
            filtered = df[df["week"]==target_week]
            baseline_hours = len(filtered["date"].unique())*8
        elif view=="Week-to-Date":
            filtered = df[df["week"]==current_week]
            baseline_hours = len(filtered["date"].unique())*8
        elif view=="Last Month":
            target_month = current_month-1 or 12
            filtered = df[df["date"].dt.month==target_month]
            baseline_hours = baseline_hours_for_month(target_month)
        else: # MTD
            filtered = df[df["date"].dt.month==current_month]
            baseline_hours = baseline_hours_for_month(current_month)

        member_stats = filtered.groupby("member").agg(
            total_hours=("hours","sum"),
            leave_hours=("leave_hours","sum"),
            utilized_hours=("productive_hours","sum")
        ).reset_index()

        member_stats["available_hours"] = baseline_hours - member_stats["leave_hours"]
        member_stats["utilization_pct"] = (member_stats["utilized_hours"]/member_stats["available_hours"]*100).round(1)

        st.subheader("Member Utilization")
        st.dataframe(member_stats[["member","total_hours","leave_hours","utilized_hours","utilization_pct"]])

        team_stats = pd.DataFrame({
            "team":[TEAM],
            "total_hours":[member_stats["total_hours"].sum()],
            "leave_hours":[member_stats["leave_hours"].sum()],
            "utilized_hours":[member_stats["utilized_hours"].sum()],
            "available_hours":[baseline_hours*len(member_stats)-member_stats["leave_hours"].sum()]
        })
        team_stats["utilization_pct"] = (team_stats["utilized_hours"]/team_stats["available_hours"]*100).round(1)

        st.subheader("Team Utilization")
        st.dataframe(team_stats[["team","total_hours","leave_hours","utilized_hours","utilization_pct"]])
