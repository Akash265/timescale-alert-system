# airflow/dags/alert_dags.py
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
from database import get_db_connection
from notification import NotificationService
from airflow.models.dagbag import DagBag
from config import Settings
import json
import logging
import psycopg2
import datetime

logger = logging.getLogger(__name__)
settings = Settings()

def check_alert(alert_id):
    """Check if query result is different from previous run and create incident if changed"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, query, data_source_id, trigger_condition, schedule,
                       notification_channels, priority, created_by
                FROM alert_config
                WHERE id = %s
            """, (alert_id,))
            alert = cur.fetchone()
            
            if not alert:
                logger.error(f"Alert config {alert_id} not found")
                return
            
            # Execute the query
            current_result = execute_query(alert['query'], alert['data_source_id'])
            logger.info(f"Executed query for alert {alert['name']}: {len(current_result)} rows")
            
            # Get the previous result
            cur.execute("""
                SELECT last_result
                FROM alert_config
                WHERE id = %s
            """, (alert_id,))
            last_result = cur.fetchone()['last_result']
            
            # Convert to sets of tuples for comparison (since dicts aren't hashable)
            current_set = set(tuple(sorted(row.items())) for row in current_result)
            last_set = set(tuple(sorted(row.items())) for row in last_result) if last_result else set()
            
            # Check if results are different and not empty
            if current_set != last_set and current_result:
                logger.info(f"Change detected for alert {alert['name']}: {len(current_result)} rows")
                create_incident(alert, current_result)
            
            # Store the current result for next comparison
            cur.execute("""
                UPDATE alert_config
                SET last_result = %s
                WHERE id = %s
            """, (json.dumps(current_result), alert_id))
            conn.commit()

def execute_query(query, data_source_id):
    """Execute the query against the data source"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()

def create_incident(alert, query_result):
    """Create an incident based on alert trigger"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            serialized_result = serialize_query_result(query_result)
            cur.execute("""
                INSERT INTO incident 
                (title, description, alert_config_id, priority, incident_data)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, title, description, alert_config_id, status, priority,
                          assigned_team, assigned_user, created_at, resolved_at, incident_data
            """, (
                f"Alert {alert['name']} Triggered",
                f"New data detected by alert {alert['name']}",
                alert['id'],
                alert['priority'],
                json.dumps(serialized_result)
            ))
            new_incident = cur.fetchone()
            
            cur.execute("""
                INSERT INTO activity (incident_id, user_id, action, comment)
                VALUES (%s, %s, %s, %s)
            """, (
                new_incident['id'],
                alert['created_by'],
                'CREATE',
                'Incident auto-created by alert trigger'
            ))
            
            conn.commit()
            
            channels = alert['notification_channels']
            if isinstance(channels, str):
                channels = json.loads(channels)
            
            notification_service = NotificationService(settings)
            message = notification_service.create_incident_message(new_incident, serialized_result)
            for channel, recipients in channels.items():
                for recipient in recipients:
                    notification_service.send_notification(
                        new_incident['id'],
                        channel,
                        recipient,
                        message
                    )

def serialize_query_result(result):
    """Convert datetime objects in query result to ISO 8601 strings"""
    def convert(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return obj
    return [{key: convert(value) for key, value in row.items()} for row in result]

def create_alert_dag(alert_id, schedule_interval):
    """Create an Airflow DAG for a specific alert"""
    dag = DAG(
        f'alert_{alert_id}',
        default_args={
            'owner': 'airflow',
            'start_date': days_ago(1),
            'retries': 1,
            'retry_delay': timedelta(minutes=5),
        },
        schedule_interval=schedule_interval,
        catchup=False,
    )
    
    check_alert_task = PythonOperator(
        task_id='check_alert',
        python_callable=check_alert,
        op_args=[alert_id],
        dag=dag,
    )
    
    return dag

def initialize_alerts():
    """Fetch all active alerts and create DAGs for them"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, schedule
                FROM alert_config
                WHERE status = 'ACTIVE'
            """)
            active_alerts = cur.fetchall()
            
            for alert in active_alerts:
                alert_id = alert['id']
                schedule_interval = parse_schedule(alert['schedule'])
                dag = create_alert_dag(alert_id, schedule_interval)
                
                # Add the DAG to Airflow's DagBag
                dag_bag = DagBag()
                dag_bag.dags[dag.dag_id] = dag
                dag_bag.sync_to_db()
                
                # Send initial alert
                check_alert(alert_id)

def parse_schedule(schedule_str):
    """Parse schedule string (e.g., 'interval:15m') into Airflow schedule_interval"""
    if schedule_str.startswith("interval:"):
        value = schedule_str.split(":")[1]
        if value.endswith("m"):
            return f"*/{value[:-1]} * * * *"
        elif value.endswith("h"):
            return f"0 */{value[:-1]} * * *"
        elif value.endswith("s"):
            return f"*/{int(value[:-1]) // 60} * * * *"
    return "*/15 * * * *"

# Initialize alerts when Airflow starts
initialize_alerts()