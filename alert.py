from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import psycopg2
import smtplib
from email.mime.text import MIMEText
import json
HOST = "smtp.gmail.com"
PORT = 587

FROM_EMAIL = "akash75622@gmail.com"
TO_EMAIL = "akash265457k@gmail.com"
PASSWORD = ""

MESSAGE = """Subject: Alert Notification
This is a test email."""
# Function to execute queries and send alerts
def check_alerts(db, user, password):
    conn = psycopg2.connect(f"dbname={db} user={user} password={password}")
    cursor = conn.cursor()

    # Fetch alert configurations
    cursor.execute("SELECT id, alert_query, notification_channels FROM alert_configurations WHERE enabled = TRUE")
    alerts = cursor.fetchall()

    for alert in alerts:
        alert_id, alert_query, notification_channels = alert
        cursor.execute(alert_query)
        results = cursor.fetchall()

        if results:
            # Prepare alert message
            message = f"Alert ID: {alert_id}\n\nQuery Results:\n{results}"
            send_email(notification_channels['email'], message)

            # Log alert history
            cursor.execute("""
                INSERT INTO alert_history (alert_configuration_id, alert_data, status, created_at)
                VALUES (%s, %s, 'TRIGGERED', NOW())
            """, (alert_id, json.dumps(results)))

    conn.commit()
    cursor.close()
    conn.close()

# Function to send email
def send_email(to_email, message):
    smtp = smtplib.SMTP(HOST, PORT)
    smtp.ehlo()
    smtp.starttls()
    smtp.login(FROM_EMAIL, PASSWORD)
    smtp.sendmail(FROM_EMAIL, to_email, message)
    smtp.quit()
send_email("shrikanth@bluenorthai.com",MESSAGE)
# Airflow DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 10, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'alert_system',
    default_args=default_args,
    schedule_interval=timedelta(minutes=30),  # Adjust frequency as needed
    catchup=False,
)

task = PythonOperator(
    task_id='check_alerts',
    python_callable=check_alerts,
    dag=dag,
)





