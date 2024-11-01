import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import random

# Set page to wide mode
st.set_page_config(layout="wide")

# Initialize SQLite database connection
def get_db_connection():
    return sqlite3.connect('visits.db', check_same_thread=False)

# Admin Dashboard
st.title("Zone Explorer Admin Dashboard 🎯")

# Database Contents
conn = get_db_connection()

# Prize Draw Section
st.header("Prize Draw Entries 🎁")
prize_draw_entries = conn.execute('SELECT * FROM prize_draw').fetchall()
prize_draw_df = pd.DataFrame(prize_draw_entries, columns=["User ID", "Email"])
st.dataframe(prize_draw_df, use_container_width=True)

# Random Winner Draw
if st.button("Draw Random Winner! 🎲"):
    conn = get_db_connection()
    
    # Get all eligible entries
    prize_draw_entries = pd.read_sql('''
        SELECT DISTINCT prize_draw.user_id, prize_draw.email,
        COUNT(DISTINCT visits.zone) as zones_visited
        FROM prize_draw 
        JOIN visits ON prize_draw.user_id = visits.user_id
        GROUP BY prize_draw.user_id
        HAVING zones_visited = 6
    ''', conn)
    
    if len(prize_draw_entries) == 0:
        st.warning("No eligible entries found! Participants must visit all zones to be eligible.")
    else:
        # Draw single winner
        winner = prize_draw_entries.sample(n=1)
        st.success("🎉 Winner drawn!")
        st.markdown(f"### 🏆 Winner: {winner['email'].iloc[0]}")

# Visits Section
st.header("Zone Visits 📊")

# Add date filter
st.subheader("Filter Visits")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.now())
with col2:
    end_date = st.date_input("End Date", datetime.now())

# Query with date filter
visits = conn.execute('''
    SELECT * FROM visits 
    WHERE date(timestamp) BETWEEN date(?) AND date(?)
    ORDER BY timestamp DESC
''', (start_date, end_date)).fetchall()

visits_df = pd.DataFrame(visits, columns=["User ID", "Zone", "Timestamp"])
st.dataframe(visits_df, use_container_width=True)

# Statistics Section
st.header("Statistics 📈")

# Total unique users
unique_users = len(visits_df["User ID"].unique())
total_visits = len(visits_df)

col1, col2 = st.columns(2)
with col1:
    st.metric("Unique Users", unique_users)
with col2:
    st.metric("Total Visits", total_visits)

# Visits by zone
st.subheader("Visits by Zone")
zone_counts = visits_df["Zone"].value_counts()
st.bar_chart(zone_counts)

# Close connection at the end
conn.close() 