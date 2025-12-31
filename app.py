import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from supabase import create_client

# ------------------ Page Config ------------------
st.set_page_config(layout="wide")

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
}

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Production Design", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True, key="team_display")

    with st.form(key="entry_form", clear_on_submit=False):
        date_value = st.date_input("Date", key="date_field")
        c1, c2 = st.columns(2)
        with c1:
            member = st.selectbox("Member", MEMBERS, key="member_field")
        with c2:
            component = st.selectbox("Component", COMPONENTS, key="component_field")

        c3, c4 = st.columns(2)
        with c3:
            tickets = st.number_input("Tickets", min_value=0, step=1, key="tickets_field")
        with c4:
            banners = st.number_input("Banners", min_value=0, step=1, key="banners_field")

        c5, c6 = st.columns(2)
        with c5:
            hours = st.selectbox("Hours", list(range(24)), key="hours_field")
        with c6:
            minutes = st.selectbox("Minutes", list(range(60)), key="minutes_field")

        comments = st.text_area("Comments", key="comments_field")
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

    try:
        response = supabase.table("creative").select("*").execute()
        df1 = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df1 = pd.DataFrame()

    if not df1.empty:
        if "team" in df1.columns:
            start_index = df1.columns.get_loc("team")
            df1 = df1.iloc[:, start_index:]
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
        view = st.radio("Select view", ["Week-to-Date", "Month-to-Date", "Previous Month"])

        if view == "Week-to-Date":
            current_week = datetime.now().isocalendar()[1]
            filtered = vdf[vdf["week"] == current_week]
        elif view == "Month-to-Date":
            now = datetime.now()
            filtered = vdf[(vdf["date"].dt.month == now.month) & (vdf["date"].dt.year == now.year)]
        else:
            now = datetime.now()
            prev_month = now.month - 1 if now.month > 1 else 12
            prev_year = now.year if now.month > 1 else now.year - 1
            filtered = vdf[(vdf["date"].dt.month == prev_month) & (vdf["date"].dt.year == prev_year)]

        if filtered.empty:
            st.info("No visuals for selected view.")
        else:
            week_grouped = filtered.groupby("week")[["tickets","banners"]].sum().reset_index().sort_values("week")
            member_grouped = filtered.groupby("member")[["tickets","banners"]].sum().reset_index()

            # Row 1: Tickets by Week + Banners by Week
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.subheader("Tickets by week")
                tickets_week_chart = alt.Chart(week_grouped).mark_bar(color="steelblue").encode(
                    x=alt.X("week:O", title="Week"),
                    y=alt.Y("tickets:Q", title="Tickets")
                )
                tickets_week_text = alt.Chart(week_grouped).mark_text(
                    align="center", baseline="bottom", dy=-5, color="black"
                ).encode(x="week:O", y="tickets:Q", text="tickets:Q")
                st.altair_chart(tickets_week_chart + tickets_week_text, use_container_width=True)
            with r1c2:
                st.subheader("Banners by week")
                banners_week_chart = alt.Chart(week_grouped).mark_bar(color="orange").encode(
                    x=alt.X("week:O", title="Week"),
                    y=alt.Y("banners:Q", title="Banners")
                )
                banners_week_text = alt.Chart(week_grouped).mark_text(
                    align="center", baseline="bottom", dy=-5, color="black"
                ).encode(x="week:O", y="banners:Q", text="banners:Q")
                st.altair_chart(banners_week_chart + banners_week_text, use_container_width=True)

            # Row 2: Tickets by Member + Banners by Member
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.subheader("Tickets by member")
                tickets_member_chart = alt.Chart(member_grouped).mark_bar(color="steelblue").encode(
                    x=alt.X("member:N", title="Member", sort="-y"),
                    y=alt.Y("tickets:Q", title="Tickets")
                )
                tickets_member_text = alt.Chart(member_grouped).mark_text(
                    align="center", baseline="bottom", dy=-5, color="black"
                ).encode(x="member:N", y="tickets:Q", text="tickets:Q")
                st.altair_chart(tickets_member_chart + tickets_member_text, use_container_width=True)
            with r2c2:
                st.subheader("Banners by member")
                banners_member_chart = alt.Chart(member_grouped).