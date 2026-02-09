# 🏃 Family Step Challenge App 

A simple, no-auth Streamlit app for tracking family and friends' daily step counts in a weekly challenge. Data is stored in Google Sheets with a leaderboard and visualizations.

## Features

- **User-friendly Interface**: Enter your name and log daily steps
- **Weekly Tracking**: Monday through Sunday step entry for the current week
- **Leaderboard**: Real-time rankings sorted by total steps
- **Visualizations**: 
  - Bar chart of top performers
- **Weekly Statistics**: Total participants, combined steps, averages, and top scores
- **Google Sheets Integration**: All data stored in a shared Google Sheet

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Sheets

#### a. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one

#### b. Enable Required APIs
1. Enable the **Google Sheets API**
2. Enable the **Google Drive API**

#### c. Create Service Account
1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Give it a name (e.g., "step-challenge-bot")
4. Click **Create and Continue**
5. Skip the optional steps and click **Done**

#### d. Create and Download Key
1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Choose **JSON** format
5. Download the key file (keep it secure!)

#### e. Create Google Sheet
1. Create a new Google Sheet named **"Step Challenge"**
2. Share this sheet with the service account email (found in your JSON key file)
   - Give it **Editor** permissions
   - The email looks like: `your-service-account@your-project.iam.gserviceaccount.com`

### 3. Configure Streamlit Secrets

1. Copy the example secrets file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. Open `.streamlit/secrets.toml` and paste the contents of your JSON key file:
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
   ```

### 4. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. **Enter Your Name**: Type your name in the sidebar
2. **Log Steps**: Enter your daily step counts for each day of the week
3. **Save**: Click the "Save Steps" button
4. **View Results**: Check the leaderboard and visualizations on the main page

## Deployment

### Streamlit Community Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add your secrets in the Streamlit Cloud dashboard (Settings > Secrets)
5. Deploy!

**Note**: Never commit `.streamlit/secrets.toml` to version control (it's already in .gitignore)

## Data Structure

The Google Sheet will automatically be structured with the following columns:
- Name
- Week (date range)
- Monday through Sunday (daily steps)
- Total (auto-calculated)

## Contributing

Feel free to open issues or submit pull requests for improvements!

## License

MIT License - Feel free to use this for your own step challenges!
