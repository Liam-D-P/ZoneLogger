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

# Admin Dashboard
st.title("Zone Explorer Admin Dashboard 🎯")

# Replace the refresh indicators with a simple refresh button
if st.button("🔄 Refresh Dashboard"):
    st.rerun()

st.markdown("---")  # Add divider

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

st.markdown("---")  # Add divider

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

# Add Zone Name column by mapping zone IDs to names - Add this right after creating visits_df
if not visits_df.empty:
    visits_df['Zone Name'] = visits_df['Zone'].map(zone_mapping)

st.markdown("---")  # Add divider

# Statistics Section
st.header("Key Statistics 📈")

if not visits_df.empty:
    # Total unique users and basic stats
    unique_users = len(visits_df["User ID"].unique())
    total_visits = len(visits_df)
    
    # Calculate completion rates
    user_zone_counts = visits_df.groupby('User ID')['Zone'].nunique()
    completed_users = len(user_zone_counts[user_zone_counts == len(zone_mapping)])
    completion_rate = (completed_users / unique_users * 100) if unique_users > 0 else 0
    
    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Unique Users", unique_users)
    with col2:
        st.metric("Total Visits", total_visits)
    with col3:
        st.metric("Users Completed All Zones", completed_users)
    with col4:
        st.metric("Completion Rate", f"{completion_rate:.1f}%")

st.markdown("---")  # Add divider

# Completion Analysis Section
st.header("Completion Analysis 📊")
    
# Create completion rate visualization
completed_all = len(user_zone_counts[user_zone_counts == len(zone_mapping)])
not_completed = len(user_zone_counts[user_zone_counts < len(zone_mapping)])
    
completion_viz_data = pd.DataFrame({
    'Completion Status': ['Completed All Zones', 'Did Not Complete All Zones'],
    'Number of Users': [completed_all, not_completed]
})
    
# Create bar chart
st.bar_chart(completion_viz_data.set_index('Completion Status'))
st.markdown(f"The completion rate is approximately {completion_rate:.2f}%, meaning that about {int(completion_rate)}% of users scanned all 11 zones.")
    
# Calculate and display average completion time
if completed_users > 0:
    completed_user_ids = user_zone_counts[user_zone_counts == len(zone_mapping)].index
        
    completion_times = []
    for user_id in completed_user_ids:
        user_visits = visits_df[visits_df['User ID'] == user_id]
        if not user_visits.empty:
            user_visits['Timestamp'] = pd.to_datetime(user_visits['Timestamp'])
            first_visit = user_visits['Timestamp'].min()
            last_visit = user_visits['Timestamp'].max()
            completion_time = (last_visit - first_visit).total_seconds() / 60
            completion_times.append(completion_time)
        
    if completion_times:
        avg_completion_time = sum(completion_times) / len(completion_times)
        avg_hours = int(avg_completion_time // 60)
        avg_minutes = int(avg_completion_time % 60)
        
        if avg_hours > 0:
            st.markdown(f"Users who completed all zones took on average **{avg_hours} hours and {avg_minutes} minutes** to visit all zones.")
        else:
            st.markdown(f"Users who completed all zones took on average **{avg_minutes} minutes** to visit all zones.")

st.markdown("---")  # Add divider

# User Progress Breakdown Section
st.subheader("User Progress Breakdown")
    
# Sort data in descending order by number of zones
sorted_counts = user_zone_counts.value_counts().sort_index(ascending=False)
    
# Create DataFrame for visualization
progress_viz = pd.DataFrame({
    'Zones': [f"{zones} zones {'✅' if zones == len(zone_mapping) else ''}" for zones in sorted_counts.index],
    'Users': sorted_counts.values,
    'Percentage': (sorted_counts.values / unique_users * 100).round(1)
})
    
# Create bar chart using Streamlit
st.bar_chart(
    progress_viz.set_index('Zones')['Users'],
    use_container_width=True
)
    
# Calculate meaningful statistics
avg_zones_visited = user_zone_counts.mean().round(1)
median_zones = user_zone_counts.median()
incomplete_users = unique_users - completed_users
    
st.markdown(f"""
**Progress Overview:**
- Average zones visited per user: **{avg_zones_visited}** zones
- Median zones visited: **{median_zones}** zones
- **{completed_users}** users completed all zones
- **{incomplete_users}** users still in progress
""")

st.markdown("---")  # Add divider

# Completion Pathways Analysis
st.markdown("### Completion Pathways Analysis")
    
# Calculate how many users reached each number of zones
pathway_data = []
for zone_count in range(1, len(zone_mapping) + 1):
    users_reached = len(user_zone_counts[user_zone_counts >= zone_count])
    pathway_data.append({
        'Milestone': f"Users who visited {zone_count}+ zones",
        'Users': users_reached,
        'Drop-off': unique_users - users_reached
    })
    
pathway_df = pd.DataFrame(pathway_data)
    
# Calculate drop-off percentages
pathway_df['Retention Rate'] = (pathway_df['Users'] / unique_users * 100).round(1)
pathway_df['Drop-off Rate'] = (pathway_df['Drop-off'] / unique_users * 100).round(1)
    
# Display the funnel chart
st.markdown("#### User Retention Funnel")
st.markdown("""
This funnel shows user progression through the zones:
- Top number (23) represents total users who visited at least 1 zone
- Each level shows how many users visited that many zones or more
- Bottom number shows users who completed all zones
""")

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
    
# Customize layout
fig.update_layout(
    title_text="User Retention Funnel",
    showlegend=False,
    height=600,
    font=dict(size=14),
    margin=dict(t=60, b=0)  # Adjust margins
)
    
# Display the funnel chart
st.plotly_chart(fig, use_container_width=True)
    
# Add textual analysis
st.markdown("#### Key Drop-off Points:")
for i, row in pathway_df.iterrows():
    if i > 0:  # Skip first row to calculate drop-off from previous milestone
        users_lost = pathway_df.iloc[i-1]['Users'] - row['Users']
        if users_lost > 0:
            percentage = (users_lost / pathway_df.iloc[i-1]['Users'] * 100).round(1)
            st.markdown(f"- **{users_lost}** users ({percentage}%) stopped after completing {i} zones")
    
st.markdown("---")  # Add divider

# Zone Popularity
st.subheader("Zone Popularity")
zone_counts = visits_df['Zone Name'].value_counts()
chart_data = pd.DataFrame({
    'Zone': zone_counts.index,
    'Visits': zone_counts.values
})
st.bar_chart(chart_data.set_index('Zone'))

st.markdown("---")  # Add divider

# Raw Data Section
st.header("Raw Visit Data 📝")
if not visits_df.empty:
    st.dataframe(visits_df, use_container_width=True)
else:
    st.info("No visits found in the selected date range")