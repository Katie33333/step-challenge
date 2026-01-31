import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Family Step Challenge",
    page_icon="🏃",
    layout="wide"
)

# Google Sheets configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_google_sheet():
    """Connect to Google Sheets"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open("Step Challenge").sheet1
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.info("Please make sure you have configured the Google Sheets credentials in .streamlit/secrets.toml")
        return None

def get_current_week_dates():
    """Get Monday-Sunday dates for the current week"""
    today = datetime.now()
    # Find Monday of current week (0 = Monday, 6 = Sunday)
    monday = today - timedelta(days=today.weekday())
    week_dates = []
    for i in range(7):
        date = monday + timedelta(days=i)
        week_dates.append(date)
    return week_dates

def get_week_string(dates):
    """Format week range as string"""
    return f"{dates[0].strftime('%b %d')} - {dates[6].strftime('%b %d, %Y')}"

def initialize_sheet_headers(sheet):
    """Initialize the Google Sheet with headers if empty"""
    try:
        headers = sheet.row_values(1)
        if not headers:
            headers = ['Name', 'Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Total']
            sheet.update('A1:J1', [headers])
    except:
        headers = ['Name', 'Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Total']
        sheet.update('A1:J1', [headers])

def get_all_data(sheet):
    """Get all data from the sheet"""
    try:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_user_data(sheet, name, week_string):
    """Get user data for the current week"""
    all_data = get_all_data(sheet)
    if all_data.empty:
        return None
    
    user_data = all_data[(all_data['Name'] == name) & (all_data['Week'] == week_string)]
    if not user_data.empty:
        return user_data.iloc[0]
    return None

def save_user_data(sheet, name, week_string, steps):
    """Save user's step data for the week"""
    all_data = get_all_data(sheet)
    
    # Calculate total
    total = sum(steps.values())
    
    # Prepare row data
    row_data = [name, week_string] + list(steps.values()) + [total]
    
    # Check if user already has data for this week
    if not all_data.empty:
        user_week_data = all_data[(all_data['Name'] == name) & (all_data['Week'] == week_string)]
        if not user_week_data.empty:
            # Update existing row
            row_num = user_week_data.index[0] + 2  # +2 because index is 0-based and sheet has header
            sheet.update(f'A{row_num}:J{row_num}', [row_data])
            return
    
    # Append new row
    sheet.append_row(row_data)

def get_leaderboard(sheet, week_string):
    """Get leaderboard for the current week"""
    all_data = get_all_data(sheet)
    if all_data.empty:
        return pd.DataFrame()
    
    week_data = all_data[all_data['Week'] == week_string]
    if week_data.empty:
        return pd.DataFrame()
    
    # Sort by total steps
    leaderboard = week_data[['Name', 'Total']].sort_values('Total', ascending=False)
    return leaderboard

# App title
st.title("🏃 Family Step Challenge")

# Get week information
week_dates = get_current_week_dates()
week_string = get_week_string(week_dates)
st.subheader(f"Week: {week_string}")

# Connect to Google Sheets
sheet = get_google_sheet()

if sheet:
    initialize_sheet_headers(sheet)
    
    # Sidebar for name selection and data entry
    st.sidebar.header("Enter Your Steps")
    
    # User selection
    user_name = st.sidebar.text_input("Enter your name:", key="username")
    
    if user_name:
        st.sidebar.write(f"Hello, {user_name}! 👋")
        
        # Load existing data if available
        existing_data = get_user_data(sheet, user_name, week_string)
        
        # Create form for step entry
        st.sidebar.subheader("Daily Steps")
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        steps = {}
        
        for i, day in enumerate(days):
            date_str = week_dates[i].strftime('%m/%d')
            default_value = 0
            if existing_data is not None and day in existing_data:
                default_value = int(existing_data[day]) if existing_data[day] else 0
            
            steps[day] = st.sidebar.number_input(
                f"{day} ({date_str})",
                min_value=0,
                max_value=100000,
                value=default_value,
                step=100,
                key=f"steps_{day}"
            )
        
        # Save button
        if st.sidebar.button("💾 Save Steps", type="primary"):
            save_user_data(sheet, user_name, week_string, steps)
            st.sidebar.success("✅ Steps saved successfully!")
            st.rerun()
    
    # Main content area - Leaderboard and Visualization
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("🏆 Leaderboard")
        leaderboard = get_leaderboard(sheet, week_string)
        
        if not leaderboard.empty:
            # Add rank
            leaderboard['Rank'] = range(1, len(leaderboard) + 1)
            leaderboard = leaderboard[['Rank', 'Name', 'Total']]
            leaderboard['Total'] = leaderboard['Total'].apply(lambda x: f"{int(x):,}")
            
            # Display leaderboard
            st.dataframe(
                leaderboard,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Rank": st.column_config.NumberColumn("🏅 Rank", width="small"),
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Total": st.column_config.TextColumn("Total Steps", width="medium")
                }
            )
        else:
            st.info("No data yet for this week. Be the first to log your steps!")
    
    with col2:
        st.header("📊 Step Distribution")
        
        if not leaderboard.empty:
            # Get full data for histogram
            all_data = get_all_data(sheet)
            week_data = all_data[all_data['Week'] == week_string]
            
            if not week_data.empty:
                # Create histogram
                fig = px.histogram(
                    week_data,
                    x='Total',
                    nbins=10,
                    title='Distribution of Total Steps',
                    labels={'Total': 'Total Steps', 'count': 'Number of Participants'},
                    color_discrete_sequence=['#1f77b4']
                )
                
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Total Steps",
                    yaxis_title="Number of Participants",
                    bargap=0.1
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Additional bar chart showing top performers
                st.subheader("Top Performers")
                top_10 = week_data.nlargest(10, 'Total')[['Name', 'Total']]
                
                fig2 = px.bar(
                    top_10,
                    x='Name',
                    y='Total',
                    title='Top 10 Participants',
                    labels={'Total': 'Total Steps', 'Name': 'Participant'},
                    color='Total',
                    color_continuous_scale='Viridis'
                )
                
                fig2.update_layout(
                    showlegend=False,
                    xaxis_title="Participant",
                    yaxis_title="Total Steps"
                )
                
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data to visualize yet!")
    
    # Weekly stats
    st.header("📈 Weekly Statistics")
    all_data = get_all_data(sheet)
    week_data = all_data[all_data['Week'] == week_string]
    
    if not week_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Total Participants", len(week_data))
        
        with col2:
            total_steps = week_data['Total'].sum()
            st.metric("👟 Total Steps", f"{int(total_steps):,}")
        
        with col3:
            avg_steps = week_data['Total'].mean()
            st.metric("📊 Average Steps", f"{int(avg_steps):,}")
        
        with col4:
            max_steps = week_data['Total'].max()
            st.metric("🏅 Highest Steps", f"{int(max_steps):,}")
    
else:
    st.warning("Unable to connect to Google Sheets. Please configure your credentials.")
    st.markdown("""
    ### Setup Instructions:
    1. Create a Google Cloud Project
    2. Enable Google Sheets API and Google Drive API
    3. Create a Service Account and download the JSON key
    4. Share your Google Sheet with the service account email
    5. Add credentials to `.streamlit/secrets.toml`
    """)
