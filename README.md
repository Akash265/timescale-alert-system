# Timescale Alert System (Azure & Databricks Edition)

A real-time alerting system built with Python, FastAPI, Azure PostgreSQL (with TimescaleDB extension), and notification services (email and WhatsApp via Twilio). This project monitors database tables, executes user-defined queries at scheduled intervals or on data changes, and sends alerts when trigger conditions (e.g., new rows added) are met.

## 🚀 Features

- **Dynamic Query Scheduling**: Executes SQL queries at intervals defined in alert_config (e.g., every 15 minutes).
- **Real-Time Event Detection**: Uses PostgreSQL LISTEN/NOTIFY to detect new rows in tables hosted on Azure Database for PostgreSQL.
- **Conditional Notifications**: Sends alerts via email and WhatsApp only when query results change.
- **Initial Run Notification**: Triggers notifications with the initial result set upon alert creation.
- **Databricks Integration**: Compatible with data sources managed or ETL-ed through Azure Databricks.
- **API Endpoints**: FastAPI provides RESTful APIs to manage alerts, incidents, and notifications.

## 🧰 Prerequisites

- **Python**: 3.10+
- **Azure PostgreSQL (TimescaleDB)**: Ensure timescaledb extension is enabled.
- **Azure Databricks**: For upstream ETL or ML pipelines.
- **Twilio Account**: For WhatsApp alerts.
- **SMTP Server**: For email notifications (e.g., Gmail SMTP with app password).
- **Git**

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Akash265/timescale-alert-system.git
cd timescale-alert-system
```
2. Set Up a Virtual Environment
```bash
Copy
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install Dependencies
```bash
Copy
pip install -r requirements.txt
Sample requirements.txt:
```
```bash
Copy
fastapi==0.103.1
uvicorn==0.23.2
psycopg2-binary==2.9.9
twilio==9.4.4
python-dotenv==1.0.0
schedule==1.2.2
pandas==2.0.3
faker==19.6.2
```
🔐 Configuration
Create a .env file in the project root with the following values:

```ini
Copy
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+your_whatsapp_number
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
DB_CONNECTION=postgres://your_user:your_password@your_azure_postgres_host:5432/your_db?sslmode=require
RETRY_DELAY_MINUTES=10
MAX_RETRIES=3
```
Twilio: Get credentials from Twilio Console.

SMTP: Use an app-specific password for Gmail if 2FA is enabled.

DB: Replace with your Azure PostgreSQL connection string.

🧱 Database Initialization
Run the following to initialize TimescaleDB tables and enums:

```bash
Copy
python -c "from database import init_db; init_db()"
```
Creates tables: alert_config, incident, notification, and enums: priority_enum, status_enum.

🚦 Usage
Start FastAPI App
```bash
Copy
python main.py
```
Visit: http://0.0.0.0:8000/api/docs for Swagger UI.

Create an Alert
Use this sample curl request to add an alert:

```bash
Copy
curl -X 'POST' \
  'http://0.0.0.0:8000/alert-configs/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Order Monitor",
  "description": "Monitor new orders",
  "query": "SELECT order_number FROM dc_order ORDER BY order_number DESC LIMIT 5",
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
✅ This immediately runs the query and sets up ongoing monitoring.

Insert Test Data
Insert test rows into your Azure PostgreSQL database:

```bash
Copy
python insert_test.py
📋 How It Works
Scheduler: Executes SQL queries at defined intervals using the schedule library.

LISTEN/NOTIFY: Triggers PostgreSQL notifications when new data is inserted.

Databricks: You can push pre-processed data from Databricks into the monitored tables.

Notifications: Sends only when query results differ from previous runs.
```
📁 Project Structure
```bash
Copy
timescale-alert-system/
├── .env               # Environment config (excluded from Git)
├── .gitignore
├── app.log            # Runtime logs
├── api.py             # FastAPI endpoint definitions
├── config.py          # Configuration loader
├── database.py        # TimescaleDB setup
├── insert_test.py     # Test script for inserting data
├── main.py            # App runner
├── notification.py    # Email/WhatsApp alert service
├── scheduler.py       # Scheduler and trigger logic
└── requirements.txt   # Python dependencies
```
🛠 Troubleshooting
Problem	Solution
No Emails Sent	Check .env SMTP config and log output
WhatsApp Alerts Failing	Ensure Twilio number is WhatsApp-enabled
Query Not Triggering	Confirm trigger created via \d tablename in psql
Azure DB Connection Fail	Ensure firewall rules and SSL mode are correct
🧠 Ideas for Extension
Slack & MS Teams integration

Frontend dashboard to manage alerts

Integration with Azure Event Grid or Logic Apps

Support for data from Delta Lake tables in Databricks

📬 Contact
Created by @Akash265
Have questions? Open an issue or reach out!

