import streamlit as st
import pandas as pd
import os
from datetime import datetime
import altair as alt

# ------------------ FILE SETUP ------------------
excel_file = "data.xlsx"

# Create file with explicit dtypes if not exists
if not os.path.exists(excel_file):
    pd.DataFrame({
        "Team": pd.Series(dtype="str"),
        "Date": pd.Series(dtype="datetime64[ns]"),
        "Week": pd.Series(dtype="Int64"),
        "Month": pd.Series(dtype="str"),
        "Member": pd.Series(dtype="str"),
        "Component": pd.Series(dtype="str"),
        "Tickets": pd.Series(dtype="int"),
        "Banners": pd.Series(dtype="int"),
        "Duration": pd.Series(dtype="str"),
        "Comments": pd.Series(dtype="str"),
    }).to_excel(excel_file, index=False)

# Read back and coerce dtypes
df = pd.read_excel(excel_file)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Week"] = pd.to_numeric(df["Week"], errors="coerce").astype("Int64")
df["Tickets"] = pd.to_numeric(df["Tickets"], errors="coerce").fillna(0).astype(int)
df["Banners"] = pd.to_numeric(df["Banners"], errors="coerce").fillna(0).astype(int)
df["Month"] = df["Month"].astype(str)
df["Duration"] = df["Duration"].astype(str)
df["Comments"] = df["Comments"].astype(str)

TEAM = "Production Design"
MEMBERS = ["Vinitha", "Vadivel", "Nirmal", "Karthi", "Jayaprakash", "Vidhya"]

tab1, tab2 = st.tabs(["📝 Production Design", "📊 Visuals"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Production Design")
    st.text_input("Team", TEAM, disabled=True)
    date = st.date_input("Date")

    col1, col2 = st.columns(2)
    with col1:
        member = st.selectbox("Member", MEMBERS)
    with col2:
        component = st.selectbox("Component", [
            "Content Email","Digital Banners","Weekend","Edits","Break",
            "Others","Meeting","Innovation","Round 2 Banners","Leave",
            "Internal Requests","Promo Creative","Social Requests",
            "Landing Pages","Category Banners","Image Requests"
        ])

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

    comments = st.text_area("Comments")

    if st.button("Submit") and date:
        new_row = pd.DataFrame([{
            "Team": TEAM,
            "Date": pd.to_datetime(date),
            "Week": date.isocalendar()[1],
            "Month": date.strftime("%B"),
            "Member": member,
            "Component": component,
            "Tickets": int(tickets),
            "Banners": int(banners),
            "Duration": f"{hours}h {minutes}m",
            "Comments": comments
        }])
        df = pd.concat([df, new_row], ignore_index=True)

        # Save back to Excel
        df.to_excel(excel_file, index=False)
        st.success("Saved successfully")

    st.dataframe(df)

# ------------------ TAB 2 ------------------
with tab2:
    st.title("Visuals Dashboard")

    if df.empty:
        st.info("No data available")
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        view = st.radio("Select View", [
            "Week-to-Date",
            "Month-to-Date",
            "Previous Month"
        ])

        # ---------- FILTER ----------
        if view == "Week-to-Date":
            current_week = datetime.now().isocalendar()[1]
            filtered = df[df["Week"] == current_week]
            grouped = filtered.groupby("Date")[["Tickets","Banners"]].sum().reset_index()
            x_field = alt.X("Date:T", title="Date")
        elif view == "Month-to-Date":
            current_month = datetime.now().month
            filtered = df[df["Date"].dt.month == current_month]
            grouped = filtered.groupby("Week")[["Tickets","Banners"]].sum().reset_index()
            x_field = alt.X("Week:O", title="Week Number")
        else:
            prev_month = datetime.now().month - 1 or 12
            filtered = df[df["Date"].dt.month == prev_month]
            grouped = filtered.groupby("Week")[["Tickets","Banners"]].sum().reset_index()
            x_field = alt.X("Week:O", title="Week Number")

        # ---------- TICKETS ----------
        tickets_chart = alt.Chart(grouped).mark_bar(color="steelblue").encode(
            x=x_field,
            y=alt.Y("Tickets:Q", title="Tickets"),
            tooltip=["Tickets"]
        )
        tickets_labels = alt.Chart(grouped).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x=x_field,
            y="Tickets:Q",
            text="Tickets:Q"
        )
        st.altair_chart(tickets_chart + tickets_labels, use_container_width=True)

        # ---------- BANNERS ----------
        banners_chart = alt.Chart(grouped).mark_bar(color="orange").encode(
            x=x_field,
            y=alt.Y("Banners:Q", title="Banners"),
            tooltip=["Banners"]
        )
        banners_labels = alt.Chart(grouped).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x=x_field,
            y="Banners:Q",
            text="Banners:Q"
        )
        st.altair_chart(banners_chart + banners_labels, use_container_width=True)

        # ---------- MEMBER-WISE ----------
        st.subheader("👥 Member-wise Tickets")
        member_grp = filtered.groupby("Member")[["Tickets","Banners"]].sum().reset_index()

        tickets_chart = alt.Chart(member_grp).mark_bar(color="steelblue").encode(
            x=alt.X("Member:N", title="Member"),
            y=alt.Y("Tickets:Q", title="Total Tickets"),
            tooltip=["Member", "Tickets"]
        )
        tickets_labels = alt.Chart(member_grp).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x="Member:N",
            y="Tickets:Q",
            text="Tickets:Q"
        )
        st.altair_chart(tickets_chart + tickets_labels, use_container_width=True)

        st.subheader("👥 Member-wise Banners")
        banners_chart = alt.Chart(member_grp).mark_bar(color="orange").encode(
            x=alt.X("Member:N", title="Member"),
            y=alt.Y("Banners:Q", title="Total Banners"),
            tooltip=["Member", "Banners"]
        )
        banners_labels = alt.Chart(member_grp).mark_text(
            align="center", baseline="bottom", dy=-2, color="black"
        ).encode(
            x="Member:N",
            y="Banners:Q",
            text="Banners:Q"
        )
        st.altair_chart(banners_chart + banners_labels, use_container_width=True)
