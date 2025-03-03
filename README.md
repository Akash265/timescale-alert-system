# Timescale Alert System

A real-time alerting system built with Python, FastAPI, TimescaleDB, and notification services (email and WhatsApp via Twilio). This project monitors database tables, executes user-defined queries at scheduled intervals or on data changes, and sends alerts when trigger conditions (e.g., new rows added) are met.

## Features

- **Dynamic Query Scheduling**: Executes SQL queries at intervals specified in `alert_config` (e.g., every 15 minutes).
- **Real-Time Event Detection**: Uses PostgreSQL `LISTEN/NOTIFY` to detect new row insertions across multiple tables.
- **Conditional Notifications**: Sends alerts via email and WhatsApp only when query results change (e.g., new rows detected).
- **Initial Run Notification**: Reports query results immediately when an alert is created.
- **Database Integration**: Built on TimescaleDB for time-series data management.
- **API Endpoints**: FastAPI provides RESTful endpoints to manage alerts, incidents, and notifications.

## Prerequisites

- **Python**: 3.10+
- **TimescaleDB**: PostgreSQL with TimescaleDB extension (hosted or local).
- **Twilio Account**: For WhatsApp notifications.
- **SMTP Server**: For email notifications (e.g., Gmail).
- **Git**: For version control.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Akash265/timescale-alert-system.git
cd timescale-alert-system

```
### 2. Set Up a Virtual Environment
```bash
python -m venv llm-api
source llm-api/bin/activate  # On Windows: llm-api\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
#### Sample requirements.txt

```bash
fastapi==0.103.1
uvicorn==0.23.2
psycopg2-binary==2.9.9
twilio==9.4.4
python-dotenv==1.0.0
schedule==1.2.2
pandas==2.0.3
faker==19.6.2
```
#### 4. Configure Environment Variables
Create a .env file in the project root and add your credentials:

```bash
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+your_twilio_whatsapp_number
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
DB_CONNECTION=postgres://tsdbadmin:your_password@your_host:39236/tsdb?sslmode=require
RETRY_DELAY_MINUTES=10
MAX_RETRIES=3
```

Twilio: Get credentials from Twilio Console.
SMTP: Use an app-specific password if using Gmail with 2FA.
DB: Replace with your TimescaleDB connection string.

#### 5. Initialize the Database
Run the database setup script:

```bash
python -c "from database import init_db; init_db()"
```

This creates tables (alert_config, incident, notification, etc.) and enums (priority_enum, status_enum).

## Usage
### Running the Application
Start the FastAPI server:

```bash
python main.py
```

Access the API at http://0.0.0.0:8000/api/docs for Swagger UI.

### Creating an Alert
Add an alert configuration via the /alert-configs/ endpoint:

```bash
curl -X 'POST' \
  'http://0.0.0.0:8000/alert-configs/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Order Monitor",
  "description": "Monitor new orders",
  "query": "SELECT order_number FROM dc_order ORDER BY order_number ASC LIMIT 5",
  "data_source_id": "d43cc24e-4f7e-4957-9570-43782ca414f9",
  "trigger_condition": "New row added",
  "schedule": "interval:1m",
  "notification_channels": {
    "email": ["your_email@example.com"],
    "whatsapp": ["+your_phone_number"]
  },
  "priority": "MEDIUM",
  "created_by": "e35fd031-c992-4c24-9dbf-53e5fe22da85"
}'
```


Initial query results are sent immediately.
The query runs every x minute and on new row insertions.
Inserting Test Data
Run a script to insert a row into dc_order:

```bash
insert_dc_order_test.py
```

Monitoring Logs
Logs are written to app.log. Check for:

```bash
2025-03-03 19:xx:xx,xxx - scheduler - INFO - New order numbers detected for alert Order Monitor: {'ORD00000010'}
```

### How It Works
Scheduler: AlertScheduler runs queries at intervals (interval:Xm) and listens for table inserts using LISTEN/NOTIFY.
Triggers: Automatically sets up triggers on tables referenced in queries (e.g., dc_order).
Notifications: Sends initial results on alert creation and subsequent alerts only when query results change.

## Project Structure
```bash
timescale-alert-system/
├── app.log          # Application logs
├── .env             # Environment variables (not tracked)
├── .gitignore       # Ignores logs and .env
├── api.py           # FastAPI endpoints
├── config.py        # Settings and env loading
├── database.py      # Database initialization
├── insert_test.py   # Test data insertion
├── main.py          # Application entry point
├── notification.py  # Email/WhatsApp notification service
├── scheduler.py     # Alert scheduling and event handling
└── requirements.txt # Python dependencies
```

### Troubleshooting
No Emails: Verify SMTP settings in .env and check app.log for errors.
No WhatsApp: Ensure TWILIO_FROM_NUMBER is a WhatsApp-enabled number (e.g., +919350311150).
Alerts Not Triggering: Confirm table triggers are set (\d dc_order in psql) and query matches table data.
