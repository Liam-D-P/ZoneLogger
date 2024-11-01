# This Streamlit application logs user visits to different zones and checks if all zones have been visited.
# It uses an SQLite database to store visit data and a cookie manager to handle user sessions securely.

import streamlit as st
import sqlite3
import pandas as pd
from streamlit_cookies_manager import EncryptedCookieManager

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

# Initialize SQLite database
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('visits.db', check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            user_id TEXT,
            zone TEXT
        )
    ''')
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
    conn.execute('INSERT INTO visits (user_id, zone) VALUES (?, ?)', (user_id, zone))
    conn.commit()

# Function to check if all zones are visited
def all_zones_visited(user_id):
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    return all(zone in visited_zones for zone in zone_mapping.keys())

# Function to visualize visited zones
def visualize_zones(user_id):
    st.write("Zone Visit Status:")
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    for complex_zone, friendly_zone in zone_mapping.items():
        if complex_zone in visited_zones:
            st.markdown(f"<span style='color: green;'>{friendly_zone}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color: red;'>{friendly_zone}</span>", unsafe_allow_html=True)

# Function to get remaining zones
def get_remaining_zones(user_id):
    conn = get_db_connection()
    cursor = conn.execute('SELECT zone FROM visits WHERE user_id = ?', (user_id,))
    visited_zones = [row[0] for row in cursor.fetchall()]
    return [friendly_zone for complex_zone, friendly_zone in zone_mapping.items() if complex_zone not in visited_zones]

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Database Contents"])

if page == "Home":
    # Get query parameters
    query_params = st.query_params
    zone = query_params["zone"]
    
    # Check for user email in cookies
    if 'user_email' not in cookies:
        user_email = st.text_input("Enter your email to start:")
        if user_email:
            cookies['user_email'] = user_email
            cookies.save()
    else:
        user_email = cookies['user_email']

    if user_email:
        #st.write(f"Welcome, {user_email}!") # Not required welcome message in "zone"
        if zone:
            if zone in zone_mapping:
                log_visit(user_email, zone)
                st.success(f"Welcome {user_email} to the {zone_mapping[zone]}!")
                remaining_zones = get_remaining_zones(user_email)
                if remaining_zones:
                    st.info(f"You now have {len(remaining_zones)} more zones to visit: {', '.join(remaining_zones)}")
                else:
                    st.success("Well done for visiting all zones!")
                visualize_zones(user_email)
            else:
                st.error("Invalid zone. Please provide a valid zone parameter.")
        else:
            st.write("Scan the QR code at each zone to log your visit.")

        # Check if all zones are visited
        if all_zones_visited(user_email):
            st.success("Congratulations, you have visited all zones! Click the Submit button to enter the prize draw.")
            if st.button("Submit"):
                conn = get_db_connection()
                conn.execute('INSERT INTO prize_draw (user_id, email) VALUES (?, ?)', (user_email, user_email))
                conn.commit()
                st.success("You have been entered into the prize draw!")
        else:
            st.info("Visit all zones to enter the prize draw.")

elif page == "Database Contents":
    st.title("Database Contents")

    conn = get_db_connection()
    
    st.subheader("Prize Draw Entries")
    prize_draw_entries = conn.execute('SELECT * FROM prize_draw').fetchall()
    prize_draw_df = pd.DataFrame(prize_draw_entries, columns=["User ID", "Email"])
    st.dataframe(prize_draw_df)

    st.subheader("Visits")
    visits = conn.execute('SELECT * FROM visits').fetchall()
    visits_df = pd.DataFrame(visits, columns=["User ID", "Zone"])
    st.dataframe(visits_df)
