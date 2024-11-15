import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# Set page to wide mode
st.set_page_config(
    page_title="Zone Explorer Admin",
    page_icon="⚙️",
    layout="wide"
)

# Password protection
def check_password():
    """Returns `True` if the user has the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Kj#9mP$vN2@xL5nQ":  # Hardcoded password
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
            st.error("😕 Password incorrect")

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.markdown("### 🔒 Admin Authentication Required")
        st.text_input(
            "Please enter the admin password", 
            type="password", 
            key="password",
            on_change=password_entered
        )
        return False
    
    return st.session_state["password_correct"]

# Show admin interface only if password is correct
if not check_password():
    st.stop()

# Database connection
@st.cache_resource
def get_db_connection():
    """Get Supabase connection"""
    return st.connection("supabase", type=SupabaseConnection)

# Add these functions after the get_db_connection function

def get_prize_entries():
    """Get all prize draw entries"""
    conn = get_db_connection()
    return conn.query('''
        SELECT user_id, email 
        FROM prize_draw
        ORDER BY user_id
    ''')

def get_visits(start_date, end_date):
    """Get visits between specified dates"""
    conn = get_db_connection()
    return conn.query('''
        SELECT user_id, zone, timestamp 
        FROM visits 
        WHERE DATE(timestamp) BETWEEN :1 AND :2
        ORDER BY timestamp DESC
    ''', params=[start_date, end_date])

# Admin Dashboard
st.title("Zone Explorer Admin Dashboard 🎯")

# Prize Draw Section
st.header("Prize Draw Entries 🎁")
prize_draw_entries = get_prize_entries()
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
visits = get_visits(start_date, end_date)
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