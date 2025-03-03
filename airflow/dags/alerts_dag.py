# airflow_dag.py
import sys
sys.path.append('/home/ak265/Desktop/analytics')
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import json
from database import get_db_connection
import psycopg2
from notification import NotificationService
from config import Settings

settings = Settings()

def process_alert(alert_id, **context):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get alert details
            cur.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,))
            alert = cur.fetchone()
            
            if not alert or alert['status'] != 'ACTIVE':
                return
            
            # Execute alert query
            cur.execute(alert['query'])
            query_result = cur.fetchall()
            
            if query_result:
                # Create alert history entry
                cur.execute("""
                    INSERT INTO alert_history (alert_id, query_result, notification_status)
                    VALUES (%s, %s, 'RETRY')
                    RETURNING id;
                """, (alert_id, json.dumps(query_result)))
                alert_history_id = cur.fetchone()['id']
                
                # Send notifications
                notification_service = NotificationService(settings)
                message = notification_service.create_alert_message(alert, query_result)
                
                notification_success = True
                if 'email' in alert['notification_channels']:
                    email_success = notification_service.send_email(
                        alert['notification_channels']['email'],
                        f"Alert: {alert['title']}",
                        message
                    )
                    notification_success = notification_success and email_success
                
                if 'whatsapp' in alert['notification_channels']:
                    whatsapp_success = notification_service.send_whatsapp(
                        alert['notification_channels']['whatsapp'],
                        message
                    )
                    notification_success = notification_success and whatsapp_success
                
                # Update alert history status
                status = 'SUCCESS' if notification_success else 'FAILED'
                cur.execute("""
                    UPDATE alert_history 
                    SET notification_status = %s
                    WHERE id = %s
                """, (status, alert_history_id))
                
                # Handle retry if needed
                if not notification_success:
                    cur.execute("""
                        UPDATE alert_history 
                        SET retry_count = retry_count + 1,
                            last_retry_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND retry_count < %s
                    """, (alert_history_id, settings.MAX_RETRIES))
                
                conn.commit()

def create_alert_dag(alert):
    dag_id = f'alert_dag_{alert["id"]}'
    
    default_args = {
        'owner': 'airflow',
        'start_date': datetime(2024, 1, 1),
        'retries': 0,
    }
    
    if alert['frequency'] == '1min':
        schedule_interval = '* * * * *'  # Cron expression for every minute
    else:
        frequency_map = {
            'm': lambda x: timedelta(minutes=x),
            'h': lambda x: timedelta(hours=x),
            'd': lambda x: timedelta(days=x),
        }
        
        value = int(alert['frequency'][:-1])
        unit = alert['frequency'][-1]
        schedule_interval = frequency_map[unit](value)
    dag = DAG(
        dag_id,
        default_args=default_args,
        schedule_interval=schedule_interval,
        catchup=False,
    )
    
    task = PythonOperator(
        task_id=f'process_alert_{alert["id"]}',
        python_callable=process_alert,
        op_kwargs={'alert_id': alert['id']},
        dag=dag,
    )
    
    return dag

# Create DAGs for each active alert
with get_db_connection() as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM alerts WHERE status = 'ACTIVE'")
        active_alerts = cur.fetchall()
        
for alert in active_alerts:
    globals()[f'alert_dag_{alert["id"]}'] = create_alert_dag(alert)