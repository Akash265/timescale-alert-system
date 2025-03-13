
# notification.py
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Settings
import json
from database import get_db_connection
import psycopg2.extras
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, settings):
        self.settings = settings
        self.twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    def send_email(self, to_emails, subject, body, incident_id=None, notification_id=None):
        msg = MIMEMultipart()
        msg['From'] = self.settings.SMTP_USERNAME
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            self._update_notification_status(notification_id, 'SUCCESS')
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            self._update_notification_status(notification_id, 'FAILED')
            return False
    
    def send_whatsapp(self, to_numbers, body, incident_id=None, notification_id=None):
        success = True
        for number in to_numbers:
            try:
                self.twilio_client.messages.create(
                    body=body,
                    from_=f"whatsapp:{self.settings.TWILIO_FROM_NUMBER}",
                    to=f"whatsapp:+91{number}"
                )
            except Exception as e:
                logger.error(f"WhatsApp sending failed to {number}: {str(e)}")
                success = False
        
        self._update_notification_status(notification_id, 'SUCCESS' if success else 'FAILED')
        return success
    
    def _update_notification_status(self, notification_id, status):
        if not notification_id:
            return
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if status == 'FAILED':
                    cur.execute("""
                        UPDATE notification 
                        SET status = %s, 
                            retry_count = retry_count + 1,
                            last_retry_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, notification_id))
                else:
                    cur.execute("""
                        UPDATE notification 
                        SET status = %s, 
                            sent_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, notification_id))
                conn.commit()
    
    def create_incident_message(self, incident, query_result):
        template = f"""
        ALERT: {incident['title']}
        Priority: {incident['priority']}
        Status: {incident['status']}
        Created at: {incident['created_at']}

        {incident.get('description', '')}

        Query Results:
        {json.dumps(query_result, indent=2)}

        Please review and take necessary action.
        To mark this incident as resolved, please use the resolution endpoint.
                """
        return template.strip()
    
    def send_notification(self, incident_id, channel, recipient, message):
        # Create notification record
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO notification 
                    (incident_id, channel, recipient, status) 
                    VALUES (%s, %s, %s, 'PENDING')
                    RETURNING id
                """, (incident_id, channel, recipient))
                notification_id = cur.fetchone()['id']
                conn.commit()
        
        # Send based on channel type
        if channel == 'email':
            return self.send_email(
                [recipient], 
                f"Incident Alert: {incident_id}", 
                message,
                incident_id,
                notification_id
            )
        elif channel == 'whatsapp':
            return self.send_whatsapp(
                [recipient],
                message,
                incident_id,
                notification_id
            )
        else:
            logger.error(f"Unsupported notification channel: {channel}")
            return False
