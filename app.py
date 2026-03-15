import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

CENTRAL_TZ = ZoneInfo("America/Chicago")
WEEK_DAYS = 7

def get_google_sheet():
    """Connect to Google Sheets and return worksheets for steps and messages."""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open("Step Challenge")

        # Keep existing weekly step data in the first worksheet.
        step_sheet = spreadsheet.sheet1

        # Create or reuse a dedicated worksheet for chat-style messages.
        try:
            message_sheet = spreadsheet.worksheet("Messages")
        except WorksheetNotFound:
            message_sheet = spreadsheet.add_worksheet(title="Messages", rows=1000, cols=3)

        return step_sheet, message_sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.info("Please make sure you have configured the Google Sheets credentials in .streamlit/secrets.toml")
        return None, None

def get_current_week_dates():
    """Get Monday-Sunday dates for the current week"""
    today = datetime.now(CENTRAL_TZ)
    # Find Monday of current week (0 = Monday, 6 = Sunday)
    monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_dates = []
    for i in range(7):
        date = monday + timedelta(days=i)
        week_dates.append(date)
    return week_dates

def get_week_string(dates):
    """Format week range as string"""
    return f"{dates[0].strftime('%b %d')} - {dates[6].strftime('%b %d, %Y')}"

def initialize_sheet_headers(step_sheet, message_sheet):
    """Initialize headers for both worksheets if missing."""
    try:
        headers = step_sheet.row_values(1)
        if not headers:
            headers = ['Name', 'Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Total']
            step_sheet.update('A1:J1', [headers])
    except Exception:
        headers = ['Name', 'Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Total']
        step_sheet.update('A1:J1', [headers])

    try:
        message_headers = message_sheet.row_values(1)
        if not message_headers:
            message_sheet.update('A1:C1', [['Timestamp', 'Name', 'Message']])
    except Exception:
        message_sheet.update('A1:C1', [['Timestamp', 'Name', 'Message']])

def get_all_data(sheet):
    """Get all data from the sheet"""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # Ensure expected columns exist to avoid KeyError on empty/malformed sheets
        expected_cols = ['Name', 'Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Total']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = pd.NA
        return df
    except Exception:
        return pd.DataFrame()

def get_user_data(sheet, name, week_string):
    """Get user data for the current week"""
    all_data = get_all_data(sheet)
    if all_data.empty:
        return None

    if 'Name' not in all_data.columns or 'Week' not in all_data.columns:
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

    if 'Week' not in all_data.columns:
        return pd.DataFrame()

    week_data = all_data[all_data['Week'] == week_string]
    if week_data.empty:
        return pd.DataFrame()
    
    # Sort by total steps
    leaderboard = week_data[['Name', 'Total']].sort_values('Total', ascending=False)
    return leaderboard

def post_message(message_sheet, name, message):
    """Append a message with a timestamp to the message worksheet."""
    timestamp = datetime.now(CENTRAL_TZ).strftime('%Y-%m-%d %H:%M:%S')
    message_sheet.append_row([timestamp, name.strip(), message.strip()])

def get_recent_messages(message_sheet, week_dates, limit=50):
    """Return messages from current week plus one day, ordered newest->oldest."""
    try:
        data = message_sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=['Timestamp', 'Name', 'Message'])

        df = pd.DataFrame(data)
        for col in ['Timestamp', 'Name', 'Message']:
            if col not in df.columns:
                df[col] = pd.NA

        df['ParsedTimestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Show only this challenge week with a one-day grace period before week start.
        # Week boundaries are based on Central Time.
        # Example: if week starts Monday, include messages from Sunday 00:00 onward.
        window_start = (week_dates[0] - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = week_dates[6].replace(hour=23, minute=59, second=59, microsecond=999999)

        filtered = df[(df['ParsedTimestamp'] >= window_start) & (df['ParsedTimestamp'] <= window_end)]
        recent = filtered.sort_values('ParsedTimestamp', ascending=False).head(limit)
        return recent[['Timestamp', 'Name', 'Message']]
    except Exception:
        return pd.DataFrame(columns=['Timestamp', 'Name', 'Message'])

def get_past_week_team_record(all_data, current_week):
    """Return highest team total from weeks before the current week."""
    if all_data.empty or 'Week' not in all_data.columns or 'Total' not in all_data.columns:
        return None

    historical = all_data[all_data['Week'] != current_week].copy()
    if historical.empty:
        return None

    historical['Total'] = pd.to_numeric(historical['Total'], errors='coerce').fillna(0)
    weekly_totals = historical.groupby('Week', as_index=False)['Total'].sum()
    if weekly_totals.empty:
        return None

    best_week = weekly_totals.loc[weekly_totals['Total'].idxmax()]
    return {
        'week': best_week['Week'],
        'total': int(best_week['Total'])
    }

# App title
st.title("Step Challenge")

# Get week information
week_dates = get_current_week_dates()
week_string = get_week_string(week_dates)
st.subheader(f"Week: {week_string}")
st.info("Tip: Click the arrow in the top-left corner to open the sidebar and enter your steps.")

# Connect to Google Sheets
sheet, message_sheet = get_google_sheet()

if sheet and message_sheet:
    initialize_sheet_headers(sheet, message_sheet)
    
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
    
    # Weekly challenge status
    st.header("🎯 Weekly Challenge Status")
    all_data = get_all_data(sheet)
    week_data = all_data[all_data['Week'] == week_string].copy()
    week_data['Total'] = pd.to_numeric(week_data['Total'], errors='coerce').fillna(0)
    current_team_total = int(week_data['Total'].sum())
    record = get_past_week_team_record(all_data, week_string)

    if record:
        goal_total = record['total']
        progress_ratio = min(current_team_total / goal_total, 1.0) if goal_total > 0 else 0

        # Thermometer-style gauge for current week progress vs record goal.
        thermometer = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=current_team_total,
                number={'valueformat': ',d', 'suffix': ' steps'},
                gauge={
                    'axis': {'range': [0, goal_total], 'tickformat': ',d'},
                    'bar': {'color': '#E4572E'},
                    'steps': [
                        {'range': [0, goal_total], 'color': '#FBE9E5'}
                    ],
                    'threshold': {
                        'line': {'color': '#2E7D32', 'width': 4},
                        'thickness': 0.8,
                        'value': goal_total
                    }
                },
                title={'text': 'Current Team Total'}
            )
        )
        thermometer.update_layout(height=240, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(thermometer, use_container_width=True)

        st.caption(f"Goal to beat: {goal_total:,} steps ({record['week']})")
        st.caption(f"Progress: {progress_ratio * 100:.1f}%")
        if current_team_total >= goal_total:
            st.success("Record matched or beaten. New challenge: maintain or push higher.")
        else:
            remaining = goal_total - current_team_total
            st.info(f"{remaining:,} more steps needed this week to beat the record.")
    else:
        st.info("No prior weeks yet. This week sets the benchmark to beat.")
        st.metric("Current Team Total", f"{current_team_total:,}")

    st.divider()

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
                    "Rank": st.column_config.NumberColumn("Rank", width="small"),
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Total": st.column_config.TextColumn("Total Steps", width="medium")
                }
            )
        else:
            st.info("No data yet for this week. Be the first to log your steps!")

    st.divider()
    st.subheader("💬 Message Board")
    st.caption("Post a quick update. Recent messages appear below.")

    with st.form("message_board_form", clear_on_submit=True):
        default_name = user_name if user_name else ""
        message_name = st.text_input("Name", value=default_name, max_chars=40)
        message_text = st.text_input("Message", max_chars=200, placeholder="Great job team! Keep moving 👟")
        posted = st.form_submit_button("Post Message")

    if posted:
        if not message_name.strip():
            st.warning("Please enter your name before posting.")
        elif not message_text.strip():
            st.warning("Please enter a message.")
        else:
            post_message(message_sheet, message_name, message_text)
            st.success("Message posted!")
            st.rerun()

    recent_messages = get_recent_messages(message_sheet, week_dates=week_dates, limit=50)
    if recent_messages.empty:
        st.info("No messages yet. Start the conversation!")
    else:
        for _, row in recent_messages.iterrows():
            st.markdown(f"**{row['Name']}**")
            st.write(row['Message'])
            st.caption(row['Timestamp'])
            st.divider()
     
    # Weekly stats
    st.header("📈 Weekly Statistics")
    
    if not week_data.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Participants", len(week_data))
        
        with col2:
            avg_daily_per_person = week_data['Total'].mean() / WEEK_DAYS
            st.metric("Avg Daily / Person", f"{int(avg_daily_per_person):,}")

        with col3:
            total_steps = week_data['Total'].sum()
            st.metric("Total Steps", f"{int(total_steps):,}")
        
        with col4:
            avg_steps = week_data['Total'].mean()
            st.metric("Average Steps", f"{int(avg_steps):,}")
        
        with col5:
            max_steps = week_data['Total'].max()
            st.metric("Highest Steps", f"{int(max_steps):,}")

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
