# Zone Explorer

A Streamlit-based web application for tracking user visits to different zones and managing a prize draw system.

## 🎯 Overview

Zone Explorer allows users to:
- Register with their email
- Track visits to 6 different zones
- View their progress and achievements
- Enter a prize draw upon completing all zones
- Monitor recent zone activity

Administrators can:
- View all prize draw entries
- Draw random winners
- View filtered visit logs
- Monitor usage statistics

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- pip (Python package installer)

### Required Packages
- streamlit
- pandas
- streamlit-cookies-manager
- sqlite3 (included with Python)

### Installation

1. Clone the repository
2. Create a new virtual environment
    `python -m venv zone_explorer_env`
3. Navigate to new virtual environment
    `cd zone_explorer_env/Scripts`
4. Activate the virtual environment
    `.\activate`
5. Install the required packages
    `pip install -r requirements.txt`

### Running the Application

1. Start the main application:
    `streamlit run ZoneLogger.py`
2. Start the admin application:
    `streamlit run admin.py --server.port 8502`

### Accessing the Applications

1. Main application: http://localhost:8501
2. Admin application: http://localhost:8502

## 📱 Features

### User Interface
- Email-based user registration
- Real-time zone visit tracking
- Progress visualization
- Achievement ranks
- Prize draw entry system
- Help section with FAQs

### Admin Dashboard
- View all prize draw entries
- Random winner selection
- Date-filtered visit logs
- Usage statistics and visualizations
- Zone activity monitoring

## 🔧 Testing Tools

The application includes testing features:
- Email override for testing different users
- Quick zone completion buttons
- Progress reset functionality

## 📊 Database

Uses SQLite with two main tables:
- `visits`: Tracks zone visits with timestamps
- `prize_draw`: Stores prize draw entries

## 🔒 Security

- User sessions managed via encrypted cookies
- Admin interface on separate port
- Database operations use parameterized queries

## 📝 Notes

- The application uses a wide layout for better visualization
- Zone visits are tracked with timestamps
- Prize draw entries are limited to one per user
- Users must visit all zones to be eligible for the prize draw
