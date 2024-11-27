# This Streamlit application logs user visits to different zones and checks if all zones have been visited.
# It uses an SQLite database to store visit data and a cookie manager to handle user sessions securely.

import streamlit as st
import os
from st_supabase_connection import SupabaseConnection

# Set page to wide mode and other configurations
st.set_page_config(
    page_title="Reboot Zone Explorer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Import all required libraries
import sqlite3
import pandas as pd
from streamlit_cookies_manager import EncryptedCookieManager
import datetime
from collections import defaultdict
from urllib.parse import urlencode
import time
from streamlit_qrcode_scanner import qrcode_scanner
import qrcode
from io import BytesIO
import base64

# Zones mapping
zone_mapping = {
    "zone123abc": "Wack A Mole Challenge", 
    "zone456def": "Chat Bot Demo",
    "zone789ghi": "Engineering Experience",
    "zone345mno": "DevOps",
    "zone678pqr": "Quality Engineering",
    "zone901stu": "Voice of a Customer",
    "zone567yza": "Engineering Mission",
    "zone846fgh": "Developer Control Plane",
    "zone642fvs": "Harness & Backstage",
    "zone321efg": "Cloud Mission",
    "zone654hij": "How Cloud Can Help",
}

# Initialize cookies manager with a password
cookies = EncryptedCookieManager(prefix="streamlit_app", password="your_secret_password")

if not cookies.ready():
    st.stop()

# Initialize session state
if 'show_email_override' not in st.session_state:
    st.session_state.show_email_override = False
if 'last_scanned_code' not in st.session_state:
    st.session_state.last_scanned_code = None
if 'processing_scan' not in st.session_state:
    st.session_state.processing_scan = False

# QR Code Functions
def generate_qr_code(data):
    """Generate a QR code and return it as a base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def show_test_qr_codes():
    """Show test QR codes for each zone"""
    st.markdown("### 🧪 Test QR Codes")
    st.info("Use these QR codes to test the scanner. Each code represents a different zone.")
    
    # Create columns for QR codes
    cols = st.columns(3)
    for i, (zone_id, zone_name) in enumerate(zone_mapping.items()):
        col_idx = i % 3
        with cols[col_idx]:
            qr_base64 = generate_qr_code(zone_id)
            st.markdown(f"##### {zone_name}")
            st.markdown(
                f'<img src="data:image/png;base64,{qr_base64}" alt="{zone_name}" width="150">',
                unsafe_allow_html=True
            )

def show_quick_buttons():
    """Show quick buttons for testing zone visits"""
    st.markdown("### Quick Zone Completion")
    st.info("Click buttons below to mark zones as visited")
    
    # Create columns for zone buttons
    cols = st.columns(3)
    for i, (zone_id, zone_name) in enumerate(zone_mapping.items()):
        col_idx = i % 3
        with cols[col_idx]:
            if st.button(f"Visit {zone_name}", key=f"visit_{zone_id}", use_container_width=True):
                if log_visit(st.session_state.user_email, zone_id):
                    st.success(f"Great job! You've discovered {zone_name}!")
                else:
                    st.warning("Please wait a minute before visiting this zone again.")
                st.rerun()

def show_manual_checkin():
    """Show manual check-in buttons for each zone"""
    st.markdown("### 🔄 Manual Check-in")
    st.info("If QR scanning isn't working, you can manually check in to a zone here")
    
    # Create columns for zone buttons
    cols = st.columns(3)
    for i, (zone_id, zone_name) in enumerate(zone_mapping.items()):
        col_idx = i % 3
        with cols[col_idx]:
            if st.button(f"Check in to {zone_name}", key=f"manual_{zone_id}", use_container_width=True):
                if log_visit(st.session_state.user_email, zone_id):
                    st.success(f"Successfully checked in to {zone_name}! 🎉")
                else:
                    st.warning("Please wait a minute before checking in to this zone again.")
                time.sleep(1)
                st.rerun()

def show_zone_interface():
    """Show the zone interface with tabs for different methods"""
    # Check if we're in testing mode
    testing_mode = os.getenv('TESTING_MODE', 'false').lower() == 'true'
    
    if testing_mode:
        tab1, tab2, tab3, tab4 = st.tabs(["📱 Scan QR Code", "✍️ Manual Check-in", "🧪 Test QR Codes", "🔘 Quick Buttons"])
    else:
        # In production, only show QR scanner
        tab1, = st.tabs(["📱 Scan QR Code"])
    
    with tab1:
        st.markdown("### 📱 Scan Zone QR Code")
        st.info("Point your camera at a zone QR code to log your visit")
        
        # Initialize the QR scanner
        qr_code = qrcode_scanner(key='scanner')
        
        # QR code processing logic...
        if qr_code and not st.session_state.processing_scan:
            st.session_state.processing_scan = True
            
            if qr_code in zone_mapping:
                if log_visit(st.session_state.user_email, qr_code):
                    st.success(f"Successfully logged visit to {zone_mapping[qr_code]}! 🎉")
                    st.session_state.processing_scan = False
                    time.sleep(1)  # Give time to see the success message
                    st.rerun()  # Refresh to update the UI
            else:
                st.error("Invalid QR code! Please try again.")
                st.session_state.processing_scan = False
                time.sleep(1)
                st.rerun()
            
            # Reset processing flag if we didn't rerun
            st.session_state.processing_scan = False
    
    if testing_mode:  # Only show these tabs in testing mode
        with tab2:
            show_manual_checkin()
        with tab3:
            show_test_qr_codes()
        with tab4:
            show_quick_buttons()

# Initialize SQLite database
@st.cache_resource
def get_db_connection():
    """Get Supabase connection"""
    return st.connection("supabase", type=SupabaseConnection)

# Function to log visit
def log_visit(user_id, zone):
    """Log a zone visit if cooldown period has passed"""
    conn = get_db_connection()
    
    # Check for recent visits in the last minute
    from datetime import datetime, timedelta
    one_min_ago = (datetime.now() - timedelta(minutes=1)).isoformat()
    
    result = conn.table("visits")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("zone", zone)\
        .gte("timestamp", one_min_ago)\
        .execute()
    
    recent_visits = len(result.data)
    
    if recent_visits == 0:
        # No recent visits, ok to log new visit
        conn.table("visits").insert({
            "user_id": user_id,
            "zone": zone,
            "timestamp": "now()"
        }).execute()
        return True
    return False

# Function to check if all zones are visited
def all_zones_visited(user_id):
    """Check if user has visited all zones"""
    conn = get_db_connection()
    data = conn.table("visits")\
        .select("zone")\
        .eq("user_id", user_id)\
        .execute()
    visited_zones = set(row['zone'] for row in data.data)
    return all(zone in visited_zones for zone in zone_mapping.keys())

# Function to visualize visited zones
def visualize_zones(user_id):
    """Show visited zones status"""
    conn = get_db_connection()
    data = conn.table("visits")\
        .select("zone")\
        .eq("user_id", user_id)\
        .execute()
    
    visited_zones = [row['zone'] for row in data.data]
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    # Split zones into two groups for two columns
    zones_list = list(zone_mapping.items())
    mid_point = len(zones_list) // 2
    
    for i, (complex_zone, friendly_zone) in enumerate(zones_list):
        current_col = col1 if i < mid_point else col2
        if complex_zone in visited_zones:
            current_col.markdown(f"✅ {friendly_zone}", unsafe_allow_html=True)
        else:
            current_col.markdown(f"⭕ {friendly_zone}", unsafe_allow_html=True)

# Function to get remaining zones
def get_remaining_zones(user_id):
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    return [friendly_zone for complex_zone, friendly_zone in zone_mapping.items() if complex_zone not in visited_zones]

# Function to get user stats
def get_user_stats(user_id):
    """Get user statistics"""
    conn = get_db_connection()
    # Change from using query to using table().select()
    result = conn.table("visits").select("zone").eq("user_id", user_id).execute()
    
    visits_by_zone = defaultdict(int)
    # Access the data through result.data
    for row in result.data:
        visits_by_zone[row['zone']] += 1
    
    total_visits = sum(visits_by_zone.values())
    unique_zones = len(visits_by_zone)
    completion_percentage = (unique_zones / len(zone_mapping)) * 100
    
    return {
        'total_visits': total_visits,
        'unique_zones': unique_zones,
        'completion_percentage': completion_percentage,
        'visits_by_zone': dict(visits_by_zone)
    }

# Function to get user rank
def get_user_rank(user_email):
    if not all_zones_visited(user_email):
        stats = get_user_stats(user_email)
        if stats['unique_zones'] == 0:
            return "Novice Explorer 🌱"
        elif stats['unique_zones'] <= 3:
            return "Zone Seeker 🔍"
        elif stats['unique_zones'] <= 6:
            return "Zone Adventurer 🌟"
        elif stats['unique_zones'] <= 9:
            return "Zone Master 💫"
        else:
            return "Zone Expert 👑"
    return "Zone Champion 🏆"

# Add this function after the other helper functions
def reset_user_progress(user_email):
    conn = get_db_connection()
    # Delete all visits for this user
    conn.execute('DELETE FROM visits WHERE user_id = ?', (user_email,))
    # Remove from prize draw if present
    conn.execute('DELETE FROM prize_draw WHERE user_id = ?', (user_email,))
    conn.commit()

# Add this function after reset_user_progress
def logout_user():
    # Clear cookies
    for key in list(cookies.keys()):
        del cookies[key]
    cookies.save()
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Don't rerun here - let the button handler do it

# Add this function near the other helper functions
@st.cache_data(ttl=30)  # Cache data for 30 seconds
def get_zone_traffic():
    """Get live zone activity data for the current day"""
    conn = get_db_connection()
    
    # Get today's date in ISO format
    today = datetime.datetime.now().date().isoformat()
    start_of_day = f"{today}T00:00:00"
    end_of_day = f"{today}T23:59:59"
    
    # Query visits for the entire day
    data = conn.table("visits")\
        .select("zone")\
        .gte("timestamp", start_of_day)\
        .lte("timestamp", end_of_day)\
        .execute()
    
    # Count visits per zone
    traffic = defaultdict(int)
    for row in data.data:
        traffic[row['zone']] += 1
    
    return traffic

# Update the show_zone_traffic function to use the cached data
def show_zone_traffic():
    """Show live zone activity"""
    st.markdown("### 👥 Today's Zone Activity")
    st.info("See which zones are popular today!")
    
    # Use cached traffic data
    traffic = get_zone_traffic()
    
    # Find the most visited zone
    if traffic:
        most_visited_zone_id = max(traffic.items(), key=lambda x: x[1])[0]
        most_visited_count = traffic[most_visited_zone_id]
        st.write(f"🔥 {zone_mapping[most_visited_zone_id]} is today's most visited zone!")
    
    # Display zone traffic
    col1, col2 = st.columns(2)
    zones_list = list(zone_mapping.items())
    mid_point = len(zones_list) // 2
    
    for i, (zone_id, zone_name) in enumerate(zones_list):
        current_col = col1 if i < mid_point else col2
        visits = traffic.get(zone_id, 0)
        
        if traffic and zone_id == most_visited_zone_id:
            current_col.write(f"{zone_name} 🔥: {visits} explorers today")
        else:
            current_col.write(f"{zone_name}: {visits} explorers today")

# Add this helper function near the other helper functions
def get_name_from_email(email):
    """Extract first name from email address in FIRSTNAME.LASTNAME format"""
    if not email:
        return ""
    # Get the part before @ and split by dot
    name_parts = email.split('@')[0].split('.')
    # Take the first part (firstname)
    firstname = name_parts[0]  # Changed from name_parts[1] to name_parts[0]
    # Capitalize first letter
    return firstname.capitalize()

# Welcome header and instructions
st.title("Welcome to the Reboot 2024 Engineering & Cloud Zone Explorer!")

# Add Help section as expander
with st.expander("Need Help? 🤔"):
    st.markdown("""
    ### Common Questions:
    
    **Q: My zone visit didn't register?**
    A: Try refreshing the page. If that fails, try visiting the zone again.
    
    **Q: Can I visit zones in any order?**
    A: Yes! Visit them in whatever order you prefer
    
    **Q: How do I know if I've won?**
    A: Prize draw winners will be notified by email after the event
    
    **Q: How many zones do I need to visit?**
    A: Visit all 11 zones to be eligible for the prize draw
    
    **Q: I need assistance!**
    A: Find a volunteer from the Quality Engineering CoE stand - they will be happy to help!
    """)

st.markdown("""
### How it works:
1. Enter your email address below to start your journey
2. Visit each zone and scan the QR code you find there
3. Track your progress - visited zones will show in green
4. Visit all zones to enter the prize draw! 🎉

Ready to begin your adventure? Let's go! 
""")

# Replace the testing tools expander section with this:
testing_mode = os.getenv('TESTING_MODE', 'false').lower() == 'true'

if testing_mode:
    # Only show testing tools when in testing mode
    with st.expander("⚠️ Testing Tools"):
        st.session_state.show_email_override = st.checkbox("Override Current Email", 
            value=st.session_state.show_email_override)
        
        if st.session_state.show_email_override:
            temp_email = st.text_input("Testing Email:", 
                value=cookies.get('user_email', ''))
            if st.button("Use This Email"):
                cookies['user_email'] = temp_email
                cookies.save()
                st.session_state.user_email = temp_email
                st.success(f"Now using email: {temp_email}")
                st.rerun()

        st.warning("Warning: These actions will affect your progress!")
        if st.button("Reset My Progress", type="primary"):
            reset_user_progress(st.session_state.user_email)
            st.success("Progress reset successfully!")
            st.rerun()

# Check for user email in cookies
if 'user_email' not in cookies and not st.session_state.show_email_override:
    st.markdown("### ✉️ First, let's get you registered!")
    user_email = st.text_input("Enter your LBG email to start your journey:")
    if user_email:
        cookies['user_email'] = user_email
        cookies.save()
        st.session_state.user_email = user_email
        st.success("✅ Successfully registered! You can now start exploring the zones.")
        st.rerun()
else:
    user_email = cookies['user_email']
    st.session_state.user_email = user_email

if user_email:
    # 1. User Identity
    user_name = get_name_from_email(user_email)
    st.markdown(f"### 👋 Hello {user_name}!")
    
    # 2. Progress Stats
    stats = get_user_stats(user_email)
    rank = get_user_rank(user_email)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rank", rank)
    with col2:
        st.metric("Zones Discovered", f"{stats['unique_zones']}/{len(zone_mapping)}")
    with col3:
        st.metric("Total Visits", stats['total_visits'])
    
    # 3. Progress Bar
    st.progress(stats['completion_percentage'] / 100, text=f"Journey Progress: {stats['completion_percentage']:.1f}%")
    
    # 4. Main Interface with Tabs
    testing_mode = os.getenv('TESTING_MODE', 'false').lower() == 'true'
    
    if testing_mode:
        tab1, tab2 = st.tabs(["📱 Scan QR Code", "✍️ Manual Check-in"])
    else:
        tab1, = st.tabs(["📱 Scan QR Code"])
    
    with tab1:
        st.markdown("### 📱 Scan Zone QR Code")
        st.info("Point your camera at a zone QR code to log your visit")
        
        # Initialize the QR scanner
        qr_code = qrcode_scanner(key='scanner')
        
        # QR code processing logic...
        if qr_code and not st.session_state.processing_scan:
            st.session_state.processing_scan = True
            
            if qr_code in zone_mapping:
                if log_visit(st.session_state.user_email, qr_code):
                    st.success(f"Successfully logged visit to {zone_mapping[qr_code]}! 🎉")
                    st.session_state.processing_scan = False
                    time.sleep(1)  # Give time to see the success message
                    st.rerun()  # Refresh to update the UI
            else:
                st.error("Invalid QR code! Please try again.")
                st.session_state.processing_scan = False
                time.sleep(1)
                st.rerun()
            
            # Reset processing flag if we didn't rerun
            st.session_state.processing_scan = False
    
    if testing_mode:  # Only show manual check-in in testing mode
        with tab2:
            st.markdown("### ✍️ Manual Zone Check-in")
            st.info("If QR scanning isn't working, you can manually check in to a zone here")
            
            # Create columns for zone buttons
            cols = st.columns(3)
            for i, (zone_id, zone_name) in enumerate(zone_mapping.items()):
                col_idx = i % 3
                with cols[col_idx]:
                    if st.button(f"Check in to {zone_name}", key=f"manual_{zone_id}", use_container_width=True):
                        if log_visit(st.session_state.user_email, zone_id):
                            st.success(f"Successfully checked in to {zone_name}! 🎉")
                        else:
                            st.warning("Please wait a minute before checking in to this zone again.")
                        time.sleep(1)
                        st.rerun()
    
    # 5. Progress Map
    st.markdown("### Your Progress")
    visualize_zones(user_email)
    
    # 6. Zone Activity
    show_zone_traffic()
    
    # 7. Prize Draw Section
    if all_zones_visited(user_email):
        st.markdown("### 🎉 Congratulations!")
        
        conn = get_db_connection()
        # Change from using execute() to using table().select()
        result = conn.table("prize_draw")\
            .select("*")\
            .eq("user_id", user_email)\
            .execute()
        
        already_entered = len(result.data) > 0
        
        if already_entered:
            st.success("You've completed all zones and are entered in the prize draw! 🎁")
            st.info("Good luck! Winners will be notified by email 🍀")
        else:
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                if st.button("Enter Prize Draw! 🎁", type="primary", use_container_width=True):
                    # Change from execute() to table().insert()
                    conn.table("prize_draw")\
                        .insert({
                            "user_id": user_email,
                            "email": user_email
                        })\
                        .execute()
                    
                    st.balloons()
                    st.success("🎊 Fantastic! You're now entered in the prize draw!")
                    st.info("Good luck! Winners will be notified by email 🍀")
                    st.rerun()  # Refresh to show the entered state
    else:
        st.info("💡 Complete all zones to unlock the prize draw entry!")
