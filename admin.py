import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection
from ZoneLogger_prod import zone_mapping  # Import your zone mapping

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

def get_prize_entries():
    """Get all prize draw entries"""
    conn = get_db_connection()
    data = conn.table("prize_draw").select("*").execute()
    return data.data

def get_visits(start_date, end_date):
    """Get visits between specified dates"""
    conn = get_db_connection()
    # Convert dates to datetime with time boundaries
    start_datetime = f"{start_date}T00:00:00"
    end_datetime = f"{end_date}T23:59:59"
    
    data = conn.table("visits")\
        .select("*")\
        .gte("timestamp", start_datetime)\
        .lte("timestamp", end_datetime)\
        .execute()
    return data.data

# Admin Dashboard
st.title("Zone Explorer Admin Dashboard 🎯")

# Replace the refresh indicators with a simple refresh button
if st.button("🔄 Refresh Dashboard"):
    st.rerun()

# Prize Draw Section
st.header("Prize Draw Entries 🎁")
prize_draw_entries = get_prize_entries()
prize_draw_df = pd.DataFrame([
    {
        'User ID': entry['user_id'],
        'Email': entry['email']
    } for entry in prize_draw_entries
])
st.dataframe(prize_draw_df, use_container_width=True)

# Random Winner Draw
if st.button("Draw Random Winner! 🎲"):
    conn = get_db_connection()
    
    # Get all eligible entries
    prize_entries = conn.table("prize_draw")\
        .select("user_id, email")\
        .execute()
    
    # Convert to DataFrame
    prize_draw_entries = pd.DataFrame(prize_entries.data)
    
    # Get visit counts for each user
    visits = conn.table("visits")\
        .select("user_id, zone")\
        .execute()
    
    visits_df = pd.DataFrame(visits.data)
    user_completion = visits_df.groupby('user_id')['zone'].nunique()
    eligible_users = user_completion[user_completion == 6].index
    
    eligible_entries = prize_draw_entries[prize_draw_entries['user_id'].isin(eligible_users)]
    
    if len(eligible_entries) == 0:
        st.warning("No eligible entries found! Participants must visit all zones to be eligible.")
    else:
        # Draw single winner
        winner = eligible_entries.sample(n=1)
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
# Create DataFrame from Supabase data
visits_df = pd.DataFrame([
    {
        'User ID': visit['user_id'],
        'Zone': visit['zone'],
        'Timestamp': visit['timestamp']
    } for visit in visits
])

if not visits_df.empty:
    # Convert zone IDs to zone names for better readability
    visits_df['Zone Name'] = visits_df['Zone'].map(zone_mapping)
    
    # Display raw data
    st.subheader("Raw Visit Data")
    st.dataframe(visits_df, use_container_width=True)
    
    # Create visualizations
    zone_counts = visits_df['Zone Name'].value_counts()
    
    # Make the bar chart more readable
    st.subheader("Visits by Zone")
    chart_data = pd.DataFrame({
        'Zone': zone_counts.index,
        'Visits': zone_counts.values
    })
    st.bar_chart(chart_data.set_index('Zone'))
else:
    st.info("No visits found in the selected date range")

# Statistics Section
st.header("Statistics 📈")

# Total unique users
unique_users = len(visits_df["User ID"].unique()) if not visits_df.empty else 0
total_visits = len(visits_df) if not visits_df.empty else 0

col1, col2 = st.columns(2)
with col1:
    st.metric("Unique Users", unique_users)
with col2:
    st.metric("Total Visits", total_visits)
  