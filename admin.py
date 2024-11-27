import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
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

# Initialize date filters
start_date = st.date_input("Start Date", datetime.now(), key="start_date")
end_date = st.date_input("End Date", datetime.now(), key="end_date")

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

# Add Zone Name column
if not visits_df.empty:
    visits_df['Zone Name'] = visits_df['Zone'].map(zone_mapping)
    
    # Calculate all required statistics
    unique_users = len(visits_df["User ID"].unique())
    total_visits = len(visits_df)
    
    # Calculate completion rates
    user_zone_counts = visits_df.groupby('User ID')['Zone'].nunique()
    completed_users = len(user_zone_counts[user_zone_counts == len(zone_mapping)])
    completion_rate = (completed_users / unique_users * 100) if unique_users > 0 else 0
    
    # Calculate completion statistics
    completed_all = len(user_zone_counts[user_zone_counts == len(zone_mapping)])
    not_completed = len(user_zone_counts[user_zone_counts < len(zone_mapping)])
    
    # Calculate completion times
    completion_times = []
    if completed_users > 0:
        completed_user_ids = user_zone_counts[user_zone_counts == len(zone_mapping)].index
        for user_id in completed_user_ids:
            user_visits = visits_df[visits_df['User ID'] == user_id]
            if not user_visits.empty:
                user_visits['Timestamp'] = pd.to_datetime(user_visits['Timestamp'])
                first_visit = user_visits['Timestamp'].min()
                last_visit = user_visits['Timestamp'].max()
                completion_time = (last_visit - first_visit).total_seconds() / 60
                completion_times.append(completion_time)
    
    # Calculate progress statistics
    sorted_counts = user_zone_counts.value_counts().sort_index(ascending=False)
    progress_viz = pd.DataFrame({
        'Zones': [f"{zones} zones {'✅' if zones == len(zone_mapping) else ''}" for zones in sorted_counts.index],
        'Users': sorted_counts.values,
        'Percentage': (sorted_counts.values / unique_users * 100).round(1)
    })
    
    # Calculate average and median
    avg_zones_visited = user_zone_counts.mean().round(1)
    median_zones = user_zone_counts.median()
    incomplete_users = unique_users - completed_users
    
    # Calculate pathway data
    pathway_data = []
    for zone_count in range(1, len(zone_mapping) + 1):
        users_reached = len(user_zone_counts[user_zone_counts >= zone_count])
        pathway_data.append({
            'Milestone': f"Users who visited {zone_count}+ zones",
            'Users': users_reached,
            'Drop-off': unique_users - users_reached
        })
    pathway_df = pd.DataFrame(pathway_data)
    
    # Create funnel chart
    fig = go.Figure(go.Funnel(
        y=pathway_df['Milestone'],
        x=pathway_df['Users'],
        textinfo="value+percent initial",
        textposition="inside",
        opacity=0.65,
        marker={
            "color": ["royalblue"] * len(pathway_df),
            "line": {"width": [2] * len(pathway_df)}
        },
    ))
    fig.update_layout(
        title_text="User Retention Funnel",
        showlegend=False,
        height=600,
        font=dict(size=14),
        margin=dict(t=60, b=0)
    )
    
    # Calculate zone popularity
    zone_counts = visits_df['Zone Name'].value_counts()
    chart_data = pd.DataFrame({
        'Zone': zone_counts.index,
        'Visits': zone_counts.values
    })

# Admin Dashboard
with st.container():
    st.title("Zone Explorer Admin Dashboard 🎯")
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()

# Prize Draw Section
with st.container():
    st.header("Prize Draw Entries 🎁")
    prize_draw_entries = get_prize_entries()
    prize_draw_df = pd.DataFrame([
        {
            'User ID': entry['user_id'],
            'Email': entry['email']
        } for entry in prize_draw_entries
    ])
    st.dataframe(prize_draw_df, use_container_width=True)

# Date Filter Container
with st.container():
    st.header("Zone Visits 📊")
    st.subheader("Filter Visits")
    col1, col2 = st.columns(2)
    with col1:
        st.date_input("Start Date", datetime.now(), key="start_date")
    with col2:
        st.date_input("End Date", datetime.now(), key="end_date")

# Key Statistics Container
with st.container():
    st.header("Key Statistics 📈")
    if not visits_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Unique Users", unique_users)
        with col2:
            st.metric("Total Visits", total_visits)
        with col3:
            st.metric("Users Completed All Zones", completed_users)
        with col4:
            st.metric("Completion Rate", f"{completion_rate:.1f}%")

# Completion Analysis Container
with st.container():
    st.header("Completion Analysis 📊")
    
    # Left column for completion rate
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Overall Completion")
        completion_viz_data = pd.DataFrame({
            'Completion Status': ['Completed All Zones', 'Did Not Complete All Zones'],
            'Number of Users': [completed_all, not_completed]
        })
        st.bar_chart(completion_viz_data.set_index('Completion Status'))
        
    # Right column for completion time
    with col2:
        st.subheader("Average Completion Time")
        if completed_users > 0 and completion_times:
            avg_completion_time = sum(completion_times) / len(completion_times)
            avg_hours = int(avg_completion_time // 60)
            avg_minutes = int(avg_completion_time % 60)
            st.metric(
                "Average Time to Complete",
                f"{avg_hours}h {avg_minutes}m" if avg_hours > 0 else f"{avg_minutes}m"
            )

# User Progress Container
with st.container():
    st.header("User Progress Analysis")
    
    # Progress Overview
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Progress Distribution")
        st.bar_chart(
            progress_viz.set_index('Zones')['Users'],
            use_container_width=True
        )
    
    with col2:
        st.subheader("Progress Statistics")
        st.metric("Average Zones Visited", f"{avg_zones_visited:.1f}")
        st.metric("Median Zones Visited", f"{median_zones}")
        st.metric("Users Still in Progress", incomplete_users)

# User Retention Container
with st.container():
    st.header("User Retention Analysis")
    
    # Funnel chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Drop-off analysis
    st.subheader("Key Drop-off Points")
    for i, row in pathway_df.iterrows():
        if i > 0:
            users_lost = pathway_df.iloc[i-1]['Users'] - row['Users']
            if users_lost > 0:
                percentage = (users_lost / pathway_df.iloc[i-1]['Users'] * 100).round(1)
                st.markdown(f"- **{users_lost}** users ({percentage}%) stopped after completing {i} zones")

# Zone Popularity Container
with st.container():
    st.header("Zone Popularity")
    st.bar_chart(chart_data.set_index('Zone'))

# Raw Data Container
with st.container():
    st.header("Raw Visit Data 📝")
    if not visits_df.empty:
        st.dataframe(visits_df, use_container_width=True)
    else:
        st.info("No visits found in the selected date range")