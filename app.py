import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
from supabase import create_client

# ------------------ SUPABASE SETUP ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"  # your anon key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TEAM = "Production Design"
MEMBERS = ["Vinitha", "Vadivel", "Nirmal", "Karthi", "Jayaprakash", "Vidhya"]

tab1, tab2 = st.tabs(["📝 Production Design", "📊 Visuals"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True, key="team_field")
    date = st.date_input("Date", key="date_field")

    col1, col2 = st.columns(2)
    with col1:
        member = st.selectbox("Member", MEMBERS, key="member_field")
    with col2:
        component = st.selectbox("Component", [
            "Content Email","Digital Banners","Weekend","Edits","Break",
            "Others","Meeting","Innovation","Round 2 Banners","Leave",
            "Internal Requests","Promo Creative","Social Requests",
            "Landing Pages","Category Banners","Image Requests"
        ], key="component_field")

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

    if st.button("Submit"):
        if date:
            duration_minutes = hours * 60 + minutes
            new_row = {
                "team": TEAM,
                "date": date.isoformat(),
                "week": date.isocalendar()[1],
                "month": date.strftime("%B"),
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

                    # Clear form fields
                    st.session_state["date_field"] = datetime.today().date()
                    st.session_state["member_field"] = MEMBERS[0]
                    st.session_state["component_field"] = "Content Email"
                    st.session_state["tickets_field"] = 0
                    st.session_state["banners_field"] = 0
                    st.session_state["hours_field"] = 0
                    st.session_state["minutes_field"] = 0
                    st.session_state["comments_field"] = ""
                else:
                    st.warning("Insert may not have returned data")
            except Exception as e:
                st.error(f"Error inserting: {e}")

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
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        view = st.radio("Select View", [
            "Week-to-Date",
            "Month-to-Date",
            "Previous Month"
        ])

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
