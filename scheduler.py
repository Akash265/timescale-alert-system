# scheduler.py
import datetime
import time
import threading
import schedule
import json
import psycopg2
import psycopg2.extras
import select
import re
from database import get_db_connection
from notification import NotificationService
from config import Settings
import logging

logger = logging.getLogger(__name__)

class AlertScheduler:
    def __init__(self, settings):
        self.settings = settings
        self.notification_service = NotificationService(settings)
        self.running = False
        self.alert_configs = {}  # Store alert configs and their last results
        self.listened_channels = set()  # Track channels we’re listening to
    
    def start(self):
        """Start the scheduler and listener in background threads"""
        if self.running:
            return
        
        self.running = True
        
        # Initialize alerts and set up triggers
        self._initialize_alerts()
        
        # Start scheduler thread
        threading.Thread(target=self._run_scheduler, daemon=True).start()
        
        # Start listener thread
        threading.Thread(target=self._listen_for_inserts, daemon=True).start()
        
        logger.info("Alert scheduler started")
    
    def _initialize_alerts(self):
        """Load all active alert configs, execute them, and set up triggers"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, query, data_source_id, trigger_condition, schedule,
                           notification_channels, priority, created_by
                    FROM alert_config
                    WHERE status = 'ACTIVE'
                """)
                active_alerts = cur.fetchall()
                
                for alert in active_alerts:
                    alert_id = str(alert['id'])
                    schedule_minutes = self._parse_schedule(alert['schedule'])
                    
                    # Set up triggers for tables in the query
                    self._setup_triggers(alert['query'], cur)
                    
                    # Execute immediately and notify
                    logger.info(f"Executing initial check for alert {alert['name']} on startup")
                    current_result = self._execute_query(alert['query'], alert['data_source_id'])
                    logger.info(f"Initial run for alert {alert['name']}: {len(current_result)} rows")
                    self._notify_initial_result(alert, current_result)
                    
                    # Schedule future runs
                    logger.info(f"Scheduling alert {alert['name']} every {schedule_minutes} minutes")
                    schedule.every(schedule_minutes).minutes.do(self._check_alert, alert=alert)
                    self.alert_configs[alert_id] = {
                        'last_result': current_result,
                        'alert': alert
                    }
    
    def _setup_triggers(self, query, cursor):
        """Set up triggers for all tables referenced in the query"""
        # Simple regex to extract table names after FROM/JOIN
        table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query, re.IGNORECASE)
        
        for table in set(tables):  # Avoid duplicates
            channel_name = f"{table}_insert"
            if channel_name not in self.listened_channels:
                try:
                    # Create notification function
                    cursor.execute(f"""
                        CREATE OR REPLACE FUNCTION notify_{table}_insert() RETURNS TRIGGER AS $$
                        BEGIN
                            PERFORM pg_notify('{channel_name}', NEW.order_number::text);
                            RETURN NEW;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)
                    
                    # Create trigger
                    cursor.execute(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 
                                FROM pg_trigger 
                                WHERE tgname = '{table}_insert_trigger' 
                                AND tgrelid = '{table}'::regclass
                            ) THEN
                                CREATE TRIGGER {table}_insert_trigger
                                AFTER INSERT ON {table}
                                FOR EACH ROW
                                EXECUTE FUNCTION notify_{table}_insert();
                            END IF;
                        END;
                        $$;
                    """)
                    self.listened_channels.add(channel_name)
                    logger.info(f"Set up trigger for table {table}")
                except psycopg2.Error as e:
                    logger.error(f"Failed to set up trigger for {table}: {e}")
                    cursor.connection.rollback()
                else:
                    cursor.connection.commit()
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        schedule.every(self.settings.RETRY_DELAY_MINUTES).minutes.do(self._retry_failed_notifications)
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _parse_schedule(self, schedule_str):
        """Parse schedule string (e.g., 'interval:15m') into minutes"""
        if schedule_str.startswith("interval:"):
            value = schedule_str.split(":")[1]
            if value.endswith("m"):
                return int(value[:-1])
            elif value.endswith("h"):
                return int(value[:-1]) * 60
            elif value.endswith("s"):
                return int(value[:-1]) // 60 or 1
        return 15
    
    def _execute_query(self, query, data_source_id):
        """Execute the query against the data source"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query)
                return cur.fetchall()
    
    def _listen_for_inserts(self):
        """Listen for new row insertions across all tables"""
        conn = psycopg2.connect(self.settings.DB_CONNECTION)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Listen to all channels set up
        for channel in self.listened_channels:
            cur.execute(f"LISTEN {channel};")
        
        logger.info(f"Listening for inserts on channels: {self.listened_channels}")
        while self.running:
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                logger.info(f"Received notification on {notify.channel}: {notify.payload}")
                self._handle_insert_event(notify.channel.split('_insert')[0])
    
    def _handle_insert_event(self, table_name):
        """Handle new row insertion by running alerts referencing the table"""
        for alert_id, config in self.alert_configs.items():
            alert = config['alert']
            if table_name in alert['query'].lower():  # Check if table is in query
                logger.info(f"Running query for alert {alert['name']} due to insert in {table_name}")
                self._check_alert(alert)
    
    def _check_alert(self, alert):
        """Check alert condition and create incident if triggered"""
        alert_id = str(alert['id'])
        try:
            current_result = self._execute_query(alert['query'], alert['data_source_id'])
            logger.info(f"Executed query for alert {alert['name']}: {len(current_result)} rows")
            
            last_result = self.alert_configs.get(alert_id, {}).get('last_result', [])
            current_orders = {row['order_number'] for row in current_result}
            last_orders = {row['order_number'] for row in last_result} if last_result else set()
            
            if current_orders != last_orders:
                new_orders = current_orders - last_orders
                logger.info(f"New order numbers detected for alert {alert['name']}: {new_orders}")
                self._create_incident(alert, current_result)
            
            self.alert_configs[alert_id]['last_result'] = current_result
        except Exception as e:
            logger.error(f"Error checking alert {alert['name']}: {str(e)}")
    
    def _serialize_query_result(self, result):
        """Convert datetime objects in query result to ISO 8601 strings"""
        def convert(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return obj
        return [{key: convert(value) for key, value in row.items()} for row in result]
    
    def _notify_initial_result(self, alert, query_result):
        """Send initial query result to notification channels"""
        serialized_result = self._serialize_query_result(query_result)
        message = f"Initial run for alert {alert['name']}:\nRows: {len(query_result)}\nData:\n{json.dumps(serialized_result, indent=2)}"
        
        channels = alert['notification_channels']
        if isinstance(channels, str):
            channels = json.loads(channels)
        
        for channel, recipients in channels.items():
            for recipient in recipients:
                self.notification_service.send_notification(
                    None,  # No incident_id for initial run
                    channel,
                    recipient,
                    message
                )
    
    def _create_incident(self, alert, query_result):
        """Create an incident based on alert trigger"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                serialized_result = self._serialize_query_result(query_result)
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
                
                message = self.notification_service.create_incident_message(new_incident, serialized_result)
                for channel, recipients in channels.items():
                    for recipient in recipients:
                        self.notification_service.send_notification(
                            new_incident['id'],
                            channel,
                            recipient,
                            message
                        )
    
    def _retry_failed_notifications(self):
        """Retry failed notifications"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT n.id, n.incident_id, n.channel, n.recipient, n.retry_count,
                           i.title, i.incident_data
                    FROM notification n
                    JOIN incident i ON n.incident_id = i.id
                    WHERE n.status = 'FAILED' 
                      AND n.retry_count < %s
                      AND n.last_retry_at < (CURRENT_TIMESTAMP - INTERVAL '%s minutes')
                """, (self.settings.MAX_RETRIES, self.settings.RETRY_DELAY_MINUTES))
                
                failed_notifications = cur.fetchall()
                
                for notification in failed_notifications:
                    cur.execute("""
                        UPDATE notification
                        SET status = 'RETRY', last_retry_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (notification['id'],))
                    conn.commit()
                    
                    message = self.notification_service.create_incident_message(
                        {
                            "title": notification["title"],
                            "id": notification["incident_id"],
                            "priority": "MEDIUM",
                            "status": "ACTIVE",
                            "created_at": datetime.datetime.now()
                        },
                        notification["incident_data"]
                    )
                    
                    if notification["channel"] == "email":
                        self.notification_service.send_email(
                            [notification["recipient"]], 
                            f"Incident Alert: {notification['incident_id']} (Retry)", 
                            message,
                            notification["incident_id"],
                            notification["id"]
                        )
                    elif notification["channel"] == "whatsapp":
                        self.notification_service.send_whatsapp(
                            [notification["recipient"]],
                            message,
                            notification["incident_id"],
                            notification["id"]
                        )

if __name__ == "__main__":
    scheduler = AlertScheduler(Settings())
    scheduler.start()