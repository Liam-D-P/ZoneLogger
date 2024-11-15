# This Streamlit application logs user visits to different zones and checks if all zones have been visited.
# It uses an SQLite database to store visit data and a cookie manager to handle user sessions securely.

import streamlit as st
import os

# Set page to wide mode
st.set_page_config(layout="wide")

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
    "zone123abc": "Zone 1",
    "zone456def": "Zone 2",
    "zone789ghi": "Zone 3",
    "zone012jkl": "Zone 4",
    "zone345mno": "Zone 5",
    "zone678pqr": "Zone 6"
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
                log_visit(st.session_state.user_email, zone_id)
                st.success(f"Great job! You've discovered {zone_name}!")
                st.rerun()

def show_zone_interface():
    """Show the zone interface with tabs for different methods"""
    # Check if we're in testing mode
    testing_mode = os.getenv('TESTING_MODE', 'false').lower() == 'true'
    
    if testing_mode:
        # Show all tabs in testing mode
        tab1, tab2, tab3 = st.tabs(["📱 Scan QR Code", "🧪 Test QR Codes", "🔘 Quick Buttons"])
        
        with tab1:
            st.markdown("### 📱 Scan Zone QR Code")
            st.info("Point your camera at a zone QR code to log your visit")
            
            # Initialize the QR scanner
            qr_code = qrcode_scanner(key='scanner')
            
            # Only process if we have a new QR code and aren't already processing
            if (qr_code and 
                qr_code != st.session_state.last_scanned_code and 
                not st.session_state.processing_scan):
                
                st.session_state.processing_scan = True
                
                if qr_code in zone_mapping:
                    # Check if this zone was visited in the last minute
                    conn = get_db_connection()
                    cursor = conn.execute('''
                        SELECT COUNT(*) FROM visits 
                        WHERE user_id = ? AND zone = ? 
                        AND datetime(timestamp) > datetime('now', '-1 minute')
                    ''', (st.session_state.user_email, qr_code))
                    recent_visits = cursor.fetchone()[0]
                    
                    if recent_visits == 0:
                        log_visit(st.session_state.user_email, qr_code)
                        st.success(f"Successfully logged visit to {zone_mapping[qr_code]}! 🎉")
                    else:
                        st.warning("You've already logged this zone recently. Please wait a moment before scanning again.")
                else:
                    st.error("Invalid QR code! Please try again.")
                
                # Update last scanned code
                st.session_state.last_scanned_code = qr_code
                
                # Reset processing flag after a short delay
                time.sleep(1)
                st.session_state.processing_scan = False
        
        with tab2:
            show_test_qr_codes()
        
        with tab3:
            show_quick_buttons()
    
    else:
        # Only show QR scanner in production mode
        st.markdown("### 📱 Scan Zone QR Code")
        st.info("Point your camera at a zone QR code to log your visit")
        
        # Initialize the QR scanner
        qr_code = qrcode_scanner(key='scanner')
        
        # Only process if we have a new QR code and aren't already processing
        if (qr_code and 
            qr_code != st.session_state.last_scanned_code and 
            not st.session_state.processing_scan):
            
            st.session_state.processing_scan = True
            
            if qr_code in zone_mapping:
                # Check if this zone was visited in the last minute
                conn = get_db_connection()
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM visits 
                    WHERE user_id = ? AND zone = ? 
                    AND datetime(timestamp) > datetime('now', '-1 minute')
                ''', (st.session_state.user_email, qr_code))
                recent_visits = cursor.fetchone()[0]
                
                if recent_visits == 0:
                    log_visit(st.session_state.user_email, qr_code)
                    st.success(f"Successfully logged visit to {zone_mapping[qr_code]}! 🎉")
                else:
                    st.warning("You've already logged this zone recently. Please wait a moment before scanning again.")
            else:
                st.error("Invalid QR code! Please try again.")
            
            # Update last scanned code
            st.session_state.last_scanned_code = qr_code
            
            # Reset processing flag after a short delay
            time.sleep(1)
            st.session_state.processing_scan = False

# Initialize SQLite database
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('visits.db', check_same_thread=False)
    
    # Check if timestamp column exists
    cursor = conn.execute("PRAGMA table_info(visits)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'timestamp' not in columns:
        # Get existing data
        try:
            cursor = conn.execute('SELECT user_id, zone FROM visits')
            existing_data = cursor.fetchall()
            
            # Drop existing table
            conn.execute('DROP TABLE IF EXISTS visits')
            
            # Create new table with timestamp
            conn.execute('''
                CREATE TABLE visits (
                    user_id TEXT,
                    zone TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Reinsert existing data with current timestamp
            for user_id, zone in existing_data:
                conn.execute('''
                    INSERT INTO visits (user_id, zone, timestamp) 
                    VALUES (?, ?, datetime('now'))
                ''', (user_id, zone))
            
            conn.commit()
        except sqlite3.OperationalError:
            # If table doesn't exist yet, just create it
            conn.execute('''
                CREATE TABLE visits (
                    user_id TEXT,
                    zone TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    # Create prize_draw table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS prize_draw (
            user_id TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    return conn

# Function to log visit
def log_visit(user_id, zone):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO visits (user_id, zone, timestamp) 
        VALUES (?, ?, datetime('now'))
    ''', (user_id, zone))
    conn.commit()

# Function to check if all zones are visited
def all_zones_visited(user_id):
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    all_visited = all(zone in visited_zones for zone in zone_mapping.keys())
    
    # Initialize the session state key if it doesn't exist
    if 'shown_completion_balloons' not in st.session_state:
        st.session_state.shown_completion_balloons = False
    
    # Show balloons if all zones just completed and balloons haven't been shown yet
    if all_visited and not st.session_state.shown_completion_balloons:
        st.balloons()
        st.session_state.shown_completion_balloons = True
    
    # Reset balloon state if not all zones are visited
    if not all_visited:
        st.session_state.shown_completion_balloons = False
    
    return all_visited

# Function to visualize visited zones
def visualize_zones(user_id):
    st.write("Zone Visit Status:")
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    
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
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone, COUNT(*) as visits FROM visits WHERE user_id = ? GROUP BY zone', (user_id,))
    visits_by_zone = defaultdict(int)
    for zone, count in cursor.fetchall():
        visits_by_zone[zone] = count
    
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
        elif stats['unique_zones'] <= 2:
            return "Zone Seeker 🔍"
        elif stats['unique_zones'] <= 4:
            return "Zone Master 🌟"
        else:
            return "Zone Expert 💫"
    return "Zone Champion 👑"

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

# Add the show_zone_traffic function
def show_zone_traffic():
    st.write("📊 Recent Zone Activity")
    
    # Get visit counts for last 30 minutes
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT zone, COUNT(*) as visits 
        FROM visits 
        WHERE datetime(timestamp) > datetime('now', '-30 minutes')
        GROUP BY zone
    ''')
    
    # Convert results to dictionary
    traffic = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    # Split zones into two groups for two columns
    zones_list = list(zone_mapping.items())
    mid_point = len(zones_list) // 2
    
    for i, (zone_id, zone_name) in enumerate(zones_list):
        current_col = col1 if i < mid_point else col2
        visits = traffic.get(zone_id, 0)
        
        current_col.write(f"{zone_name}: {visits} visits in last 30 min")

# Welcome header and instructions
st.title("Welcome to the Zone Explorer! 🎯")

# Add Help section as expander
with st.expander("Need Help? 🤔"):
    st.markdown("""
    ### Common Questions:
    
    **Q: My zone visit didn't register?**
    A: Try refreshing the page and visit the zone again
    
    **Q: Can I visit zones in any order?**
    A: Yes! Visit them in whatever order you prefer
    
    **Q: How do I know if I've won?**
    A: Prize draw winners will be notified by email
    
    **Q: How many zones do I need to visit?**
    A: Visit all 6 zones to be eligible for the prize draw
    
    **Q: I need assistance!**
    A: Find a volunteer in a blue t-shirt - they'll be happy to help!
    """)

st.markdown("""
### How it works:
1. Enter your email address below to start your journey
2. Visit each zone and scan the QR code you find there
3. Track your progress - visited zones will show in green
4. Visit all zones to enter the prize draw! 🎉

Ready to begin your adventure? Let's go! 
""")

# Add a toggle for email override
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

# Check for user email in cookies (keep existing logic)
if 'user_email' not in cookies and not st.session_state.show_email_override:
    st.markdown("### ✉️ First, let's get you registered!")
    user_email = st.text_input("Enter your email to start your journey:")
    if user_email:
        cookies['user_email'] = user_email
        cookies.save()
        st.session_state.user_email = user_email
        st.success("✅ Successfully registered! You can now start exploring the zones.")
else:
    user_email = cookies['user_email']
    st.session_state.user_email = user_email
    st.markdown(f"### 👋 Welcome back!")

if user_email:
    # Add traffic display before or after zone buttons
    show_zone_traffic()
    
    # Process zone visits
    show_zone_interface()
    
    # Then get and display updated stats
    stats = get_user_stats(user_email)
    rank = get_user_rank(user_email)
    
    # Create three columns for stats with updated data
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rank", rank)
    with col2:
        st.metric("Zones Discovered", f"{stats['unique_zones']}/{len(zone_mapping)}")
    with col3:
        st.metric("Total Visits", stats['total_visits'])
    
    # Add progress bar with updated data
    st.progress(stats['completion_percentage'] / 100, text=f"Journey Progress: {stats['completion_percentage']:.1f}%")
    
    # Show progress map
    st.markdown("### Your Progress Map:")
    visualize_zones(user_email)
    
    # Check if all zones are visited
    if all_zones_visited(user_email):
        st.markdown("---")
        st.markdown("### 🎉 Congratulations!")
        
        # Check if already entered before showing button
        conn = get_db_connection()
        cursor = conn.execute('SELECT * FROM prize_draw WHERE user_id = ?', (user_email,))
        already_entered = cursor.fetchone() is not None
        
        if already_entered:
            st.success("You've completed all zones and are entered in the prize draw! 🎁")
            st.info("Good luck! Winners will be notified by email 🍀")
        else:
            st.success("You've completed all zones! Click below to enter the prize draw.")
            # Make button bigger and centered
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                if st.button("Enter Prize Draw! 🎁", type="primary", use_container_width=True):
                    conn.execute('INSERT INTO prize_draw (user_id, email) VALUES (?, ?)', (user_email, user_email))
                    conn.commit()
                    st.balloons()
                    st.success("🎊 Fantastic! You're now entered in the prize draw!")
                    st.info("Good luck! Winners will be notified by email 🍀")
    else:
        st.markdown("---")
        st.info("💡 Complete all zones to unlock the prize draw entry!")
