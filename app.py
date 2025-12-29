import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
from supabase import create_client, Client
# ------------------ SUPABASE SETUP ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# ------------------ CONSTANTS ------------------
TEAM = "Production Design"
MEMBERS = ["Vinitha", "Vadivel", "Nirmal", "Karthi", "Jayaprakash", "Vidhya"]
# ------------------ FETCH DATA ------------------
def fetch_data():
   response = supabase.table("creative").select("*").execute()
   if response.data:
       df = pd.DataFrame(response.data)
       df["date"] = pd.to_datetime(df["date"], errors="coerce")
       return df
   return pd.DataFrame()
df = fetch_data()
tab1, tab2 = st.tabs(["📝 Production Design", "📊 Visuals"])
# ------------------ TAB 1 : DATA ENTRY ------------------
with tab1:
   st.title("Production Design")
   st.text_input("Team", TEAM, disabled=True)
   date = st.date_input("Date")
   col1, col2 = st.columns(2)
   with col1:
       member = st.selectbox("Member", MEMBERS)
   with col2:
       component = st.selectbox(
           "Component",
           [
               "Content Email","Digital Banners","Weekend","Edits","Break",
               "Others","Meeting","Innovation","Round 2 Banners","Leave",
               "Internal Requests","Promo Creative","Social Requests",
               "Landing Pages","Category Banners","Image Requests"
           ],
       )
   col3, col4 = st.columns(2)
   with col3:
       tickets = st.number_input("Tickets", min_value=0, step=1)
   with col4:
       banners = st.number_input("Banners", min_value=0, step=1)
   col5, col6 = st.columns(2)
   with col5:
       hours = st.selectbox("Hours", range(24))
   with col6:
       minutes = st.selectbox("Minutes", range(60))
   if st.button("Submit") and date:
       payload = {
           "team": TEAM,
           "date": date.isoformat(),
           "week": date.isocalendar()[1],
           "month": date.strftime("%B"),
           "member": member,
           "component": component,
           "tickets": int(tickets),
           "banners": int(banners),
           "duration": (hours * 60) + minutes,  # store minutes
       }
       supabase.table("creative").insert(payload).execute()
       st.success("Saved successfully")
       st.experimental_rerun()
   st.dataframe(df)
# ------------------ TAB 2 : DASHBOARD ------------------
with tab2:
   st.title("Visuals Dashboard")
   if df.empty:
       st.info("No data available")
   else:
       view = st.radio(
           "Select View",
           ["Week-to-Date", "Month-to-Date", "Previous Month"],
       )
       now = datetime.now()
       if view == "Week-to-Date":
           filtered = df[df["week"] == now.isocalendar()[1]]
           grouped = filtered.groupby("date")[["tickets", "banners"]].sum().reset_index()
           x_field = alt.X("date:T", title="Date")
       elif view == "Month-to-Date":
           filtered = df[df["date"].dt.month == now.month]
           grouped = filtered.groupby("week")[["tickets", "banners"]].sum().reset_index()
           x_field = alt.X("week:O", title="Week Number")
       else:
           prev_month = now.month - 1 or 12
           filtered = df[df["date"].dt.month == prev_month]
           grouped = filtered.groupby("week")[["tickets", "banners"]].sum().reset_index()
           x_field = alt.X("week:O", title="Week Number")
       # ---------- TICKETS ----------
       st.altair_chart(
           alt.Chart(grouped)
           .mark_bar(color="steelblue")
           .encode(x=x_field, y="tickets:Q", tooltip=["tickets"]),
           use_container_width=True,
       )
       # ---------- BANNERS ----------
       st.altair_chart(
           alt.Chart(grouped)
           .mark_bar(color="orange")
           .encode(x=x_field, y="banners:Q", tooltip=["banners"]),
           use_container_width=True,
       )
       # ---------- MEMBER-WISE ----------
       st.subheader("👥 Member-wise Summary")
       member_grp = filtered.groupby("member")[["tickets", "banners"]].sum().reset_index()
       st.altair_chart(
           alt.Chart(member_grp)
           .mark_bar(color="steelblue")
           .encode(x="member:N", y="tickets:Q", tooltip=["member", "tickets"]),
           use_container_width=True,
       )
       st.altair_chart(
           alt.Chart(member_grp)
           .mark_bar(color="orange")
           .encode(x="member:N", y="banners:Q", tooltip=["member", "banners"]),
           use_container_width=True,
       )