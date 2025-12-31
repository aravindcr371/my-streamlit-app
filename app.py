
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from supabase import create_client

# ------------------ Page config ------------------
st.set_page_config(layout="wide")

# ------------------ Supabase setup ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"   # TODO: replace
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"  # TODO: replace
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

# ------------------ Public holidays ------------------
PUBLIC_HOLIDAYS = {
    date(2024, 12, 25),
    date(2025, 1, 1),
}

# ------------------ Shared helpers ------------------
def end_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return (date(y, m + 1, 1) - timedelta(days=1))

def working_days_between(start: date, end: date):
    days = pd.date_range(start, end, freq="D")
    return [d.normalize() for d in days if d.weekday() < 5 and d.date() not in PUBLIC_HOLIDAYS]

def build_period_options_and_months(df_dates: pd.Series):
    today = date.today()
    current_weekday = today.weekday()
    current_month = today.month
    current_year = today.year

    year_month = pd.to_datetime(df_dates, errors="coerce").dt.to_period("M")
    available_months = sorted([m for m in year_month.unique() if (m.year > 2024 or (m.year == 2024 and m.month >= 11))])

    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    previous_month_period = pd.Period(f"{prev_year}-{prev_month:02d}")

    filtered_months = [m for m in available_months if m != previous_month_period]
    month_labels = [f"{m.strftime('%B %Y')}" for m in filtered_months]

    options = ["Current Week", "Previous Week", "Current Month", "Previous Month"] + month_labels
    return options, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year

def compute_weekdays_for_choice(choice, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year):
    if choice == "Current Week":
        start = today - timedelta(days=current_weekday)
        end = today
    elif choice == "Previous Week":
        start = today - timedelta(days=current_weekday + 7)
        end = start + timedelta(days=4)
    elif choice == "Current Month":
        start = date(current_year, current_month, 1)
        end = today
    elif choice == "Previous Month":
        pm = previous_month_period
        start = date(pm.year, pm.month, 1)
        end = end_of_month(pm.year, pm.month)
    else:
        sel_period = filtered_months[month_labels.index(choice)]
        start = date(sel_period.year, sel_period.month, 1)
        end = end_of_month(sel_period.year, sel_period.month)

    return working_days_between(start, end)

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Production Design", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True)

    with st.form(key="entry_form", clear_on_submit=False):
        date_value = st.date_input("Date")
        c1, c2 = st.columns(2)
        with c1:
            member = st.selectbox("Member", MEMBERS)
        with c2:
            component = st.selectbox("Component", COMPONENTS)

        c3, c4 = st.columns(2)
        with c3:
            tickets = st.number_input("Tickets", min_value=0, step=1)
        with c4:
            banners = st.number_input("Banners", min_value=0, step=1)

        c5, c6 = st.columns(2)
        with c5:
            hours = st.selectbox("Hours", list(range(24)))
        with c6:
            minutes = st.selectbox("Minutes", list(range(60)))

        comments = st.text_area("Comments")
        submitted = st.form_submit_button("Submit")

    if submitted:
        if isinstance(date_value, (datetime, date)) and member != "-- Select --" and component != "-- Select --":
            d = date_value if isinstance(date_value, date) else date_value.date()
            duration_minutes = int(hours) * 60 + int(minutes)
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
                "comments": (comments or "").strip() or None
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

    # Fetch sorted by date descending
    try:
        response = supabase.table("creative").select("*").order("date", desc=True).execute()
        df1 = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        try:
            response = supabase.table("creative").select("*").execute()
            df1 = pd.DataFrame(response.data)
            if "date" in df1.columns:
                df1["date"] = pd.to_datetime(df1["date"], errors="coerce")
                df1 = df1.sort_values("date", ascending=False)
        except Exception as e2:
            st.error(f"Fallback error: {e2}")
            df1 = pd.DataFrame()

    if not df1.empty:
        st.subheader("Latest entries (sorted by Date descending)")
        st.dataframe(df1, use_container_width=True)

# ------------------ TAB 2 ------------------
with tab2:
    st.title("Visuals Dashboard")
    try:
        response = supabase.table("creative").select("*").execute()
        vdf = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        vdf = pd.DataFrame()

    if vdf.empty:
        st.info("No data available")
    else:
        vdf["date"] = pd.to_datetime(vdf["date"], errors="coerce")
        options, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year = build_period_options_and_months(vdf["date"])
        choice = st.selectbox("Select period", options)
        weekdays = compute_weekdays_for_choice(choice, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year)
        filtered = vdf[vdf["date"].dt.normalize().isin(weekdays)]

        if filtered.empty:
            st.info("No visuals for selected period.")
        else:
            week_grouped = filtered.groupby("week")[["tickets","banners"]].sum().reset_index().sort_values("week")
            member_grouped = filtered.groupby("member")[["tickets","banners"]].sum().reset_index()

            def bar_with_labels(df, x_field, y_field, color):
                bar = alt.Chart(df).mark_bar(color=color).encode(x=x_field, y=y_field)
                text = alt.Chart(df).mark_text(align="center", baseline="bottom", dy=-5).encode(x=x_field, y=y_field, text=y_field)
                return bar + text

            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.subheader("Tickets by week")
                st.altair_chart(bar_with_labels(week_grouped, "week", "tickets", "steelblue"), use_container_width=True)
            with r1c2:
                st.subheader("Banners by week")
                st.altair_chart(bar_with_labels(week_grouped, "week", "banners", "orange"), use_container_width=True)

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.subheader("Tickets by member")
                st.altair_chart(bar_with_labels(member_grouped, "member", "tickets", "steelblue"), use_container_width=True)
            with r2c2:
                st.subheader("Banners by member")
                st.altair_chart(bar_with_labels(member_grouped, "member", "banners", "orange"), use_container_width=True)

            st.subheader("By Component (Sum of Tickets + Banners)")
            component_grouped = filtered.groupby("component")[["tickets","banners"]].sum().reset_index()
            component_grouped["component"] = component_grouped["component"].fillna("Unspecified")
            component_grouped["total"] = component_grouped["tickets"] + component_grouped["banners"]
            component_grouped = component_grouped.sort_values("total", ascending=False)

            bar = alt.Chart(component_grouped).mark_bar(color="#4C78A8").encode(
                x=alt.X("component:N", sort=alt.SortField(field="total", order="descending")),
                y="total:Q"
            )
            text = alt.Chart(component_grouped).mark_text(align="center", baseline="bottom", dy=-5).encode(
                x="component:N", y="total:Q", text="total:Q"
            )
            st.altair_chart(bar + text, use_container_width=True)

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
        df["utilization_hours"] = df.apply(lambda r: 0 if r["component"] in ["Break","Leave"] else r["hours"], axis=1)
        df["occupancy_hours"] = df.apply(lambda r: 0 if r["component"] in ["Break","Leave","Meeting"] else r["hours"], axis=1)
        df["leave_hours"] = df.apply(lambda r: r["hours"] if r["component"] == "Leave" else 0, axis=1)

        options, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year = build_period_options_and_months(df["date"])
        choice = st.selectbox("Select period", options)
        weekdays = compute_weekdays_for_choice(choice, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year)
        period_df = df[df["date"].dt.normalize().isin(weekdays)]
        baseline_hours_period = len(weekdays) * 8

        if period_df.empty:
            st.info("No data for the selected period.")
        else:
            agg = period_df.groupby("member").agg(utilized_hours=("utilization_hours","sum"), occupied_hours=("occupancy_hours","sum"), leave_hours=("leave_hours","sum")).reset_index()
            agg["total_hours"] = baseline_hours_period - agg["leave_hours"]
            agg["utilization_%"] = ((agg["utilized_hours"]/agg["total_hours"]).where(agg["total_hours"]>0,0)*100).round(1)
            agg["occupancy_%"] = ((agg["occupied_hours"]/agg["total_hours"]).where(agg["total_hours"]>0,0)*100).round(1)
            agg = agg.round(1)

            merged_stats = agg.rename(columns={"member":"Name","total_hours":"Total Hours","leave_hours":"Leave Hours","utilized_hours":"Utilized Hours","occupied_hours":"Occupied Hours","utilization_%":"Utilization %","occupancy_%":"Occupancy %"})
            st.subheader("Member Utilization & Occupancy")
            st.dataframe(merged_stats, use_container_width=True)

            team_total = merged_stats["Total Hours"].sum()
            team_leave = merged_stats["Leave Hours"].sum()
            team_utilized = merged_stats["Utilized Hours"].sum()
            team_occupied = merged_stats["Occupied Hours"].sum()
            team_util_pct = (team_utilized/team_total*100) if team_total>0 else 0
            team_occ_pct = (team_occupied/team_total*100) if team_total>0 else 0

            team_df = pd.DataFrame({"Team":[TEAM],"Total Hours":[round(team_total,1)],"Leave Hours":[round(team_leave,1)],"Utilized Hours":[round(team_utilized,1)],"Occupied Hours":[round(team_occupied,1)],"Utilization %":[round(team_util_pct,1)],"Occupancy %":[round(team_occ_pct,1)]})
            st.subheader("Team Utilization & Occupancy")
            st.dataframe(team_df, use_container_width=True)
