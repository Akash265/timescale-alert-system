
# api.py
from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import psycopg2.extras
from database import get_db_connection, init_db
from models import (
    DataSourceCreate, DataSourceResponse,
    TeamCreate, TeamResponse,
    UserCreate, UserResponse,
    AlertConfigCreate, AlertConfigResponse,
    IncidentCreate, IncidentResponse,
    NotificationCreate, NotificationResponse,
    ActivityCreate, ActivityResponse,
    IncidentResolveRequest,
    StatusEnum, PriorityEnum
)
from notification import NotificationService
from config import Settings

app = FastAPI(title="Alert Notification System")
settings = Settings()

@app.on_event("startup")
async def startup_event():
    init_db()

# Data Source Endpoints
@app.post("/data-sources/", response_model=DataSourceResponse)
def create_data_source(data_source: DataSourceCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO data_source (name, type, connection_details)
                VALUES (%s, %s, %s)
                RETURNING id, name, type, connection_details, created_at;
            """, (
                data_source.name,
                data_source.type,
                json.dumps(data_source.connection_details)
            ))
            conn.commit()
            return cur.fetchone()

@app.get("/data-sources/", response_model=List[DataSourceResponse])
def list_data_sources():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, type, connection_details, created_at FROM data_source")
            return cur.fetchall()

# Team Endpoints
@app.post("/teams/", response_model=TeamResponse)
def create_team(team: TeamCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO team (name, description)
                VALUES (%s, %s)
                RETURNING id, name, description;
            """, (
                team.name,
                team.description
            ))
            conn.commit()
            return cur.fetchone()

@app.get("/teams/", response_model=List[TeamResponse])
def list_teams():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, description FROM team")
            return cur.fetchall()

# User Endpoints
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO users (name, email, team_id)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, team_id, created_at;
            """, (
                user.name,
                user.email,
                str(user.team_id) if user.team_id else None  # Convert UUID to string
            ))
            conn.commit()
            return cur.fetchone()

@app.get("/users/", response_model=List[UserResponse])
def list_users():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, email, team_id, created_at FROM users")
            return cur.fetchall()

# Alert Config Endpoints
@app.post("/alert-configs/", response_model=AlertConfigResponse)
def create_alert_config(alert_config: AlertConfigCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            now = datetime.now()
            cur.execute("""
                INSERT INTO alert_config 
                (name, description, query, data_source_id, trigger_condition, 
                schedule, created_at, updated_at, created_by, notification_channels, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, query, data_source_id, 
                          trigger_condition, schedule, created_at, updated_at, 
                          created_by, notification_channels, priority;
            """, (
                alert_config.name,
                alert_config.description,
                alert_config.query,
                str(alert_config.data_source_id) if alert_config.data_source_id else None,  # Convert UUID to string
                alert_config.trigger_condition,
                alert_config.schedule,
                now,
                now,
                str(alert_config.created_by) if alert_config.created_by else None,  # Convert UUID to string
                json.dumps(alert_config.notification_channels),
                alert_config.priority
            ))
            conn.commit()
            result = cur.fetchone()
            
            # Register this alert with Airflow (this would be handled by the Airflow DAG generator)
            # In a real implementation, you might want to trigger an Airflow API call here
            # or have a separate process that syncs alert configs with Airflow
            
            return result

@app.get("/alert-configs/", response_model=List[AlertConfigResponse])
def list_alert_configs(
    status: Optional[StatusEnum] = None,
    priority: Optional[PriorityEnum] = None,
    skip: int = 0,
    limit: int = 100
):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = """
                SELECT id, name, description, query, data_source_id, trigger_condition, 
                       schedule, created_at, updated_at, created_by, status, 
                       notification_channels, priority
                FROM alert_config
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND status = %s"
                params.append(status)
            if priority:
                query += " AND priority = %s"
                params.append(priority)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            
            cur.execute(query, params)
            return cur.fetchall()

@app.get("/alert-configs/{alert_id}", response_model=AlertConfigResponse)
def get_alert_config(alert_id: uuid.UUID):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, description, query, data_source_id, trigger_condition, 
                       schedule, created_at, updated_at, created_by, status, 
                       notification_channels, priority
                FROM alert_config
                WHERE id = %s
            """, (str(alert_id),))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Alert config not found")
            return result

@app.put("/alert-configs/{alert_id}/status", response_model=AlertConfigResponse)
def update_alert_config_status(alert_id: uuid.UUID, status: StatusEnum):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                UPDATE alert_config 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, name, description, query, data_source_id, trigger_condition, 
                          schedule, created_at, updated_at, created_by, status, 
                          notification_channels, priority;
            """, (status, alert_id))
            conn.commit()
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Alert config not found")
            return result

# Incident Endpoints
@app.post("/incidents/", response_model=IncidentResponse)
def create_incident(incident: IncidentCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Create the incident
            cur.execute("""
                INSERT INTO incident 
                (title, description, alert_config_id, priority, assigned_team, 
                assigned_user, incident_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, title, description, alert_config_id, status, priority, 
                          assigned_team, assigned_user, created_at, resolved_at, incident_data;
            """, (
                incident.title,
                incident.description,
                str(incident.alert_config_id),
                incident.priority,
                str(incident.assigned_team),
                str(incident.assigned_user),
                json.dumps(incident.incident_data) if incident.incident_data else None
            ))
            new_incident = cur.fetchone()
            
            # Get alert config to send notifications
            cur.execute("""
                SELECT notification_channels
                FROM alert_config
                WHERE id = %s
            """, (str(incident.alert_config_id),))
            alert_config = cur.fetchone()
            
            # Record activity
            cur.execute("""
                INSERT INTO activity (incident_id, user_id, action, comment)
                VALUES (%s, %s, %s, %s)
            """, (
                str(new_incident['id']),
                str(incident.assigned_user) if incident.assigned_user else str(uuid.UUID('00000000-0000-0000-0000-000000000000')),
                'CREATE',
                'Incident created'
            ))
            
            conn.commit()
            
            # Send notifications (this would be async in a real implementation)
            if alert_config and 'notification_channels' in alert_config:
                notification_service = NotificationService(settings)
                message = notification_service.create_incident_message(
                    new_incident, 
                    incident.incident_data
                )
                
                channels = alert_config['notification_channels']
                if isinstance(channels, str):
                    channels = json.loads(channels)
                
                for channel, recipients in channels.items():
                    for recipient in recipients:
                        notification_service.send_notification(
                            new_incident['id'],
                            channel,
                            recipient,
                            message
                        )
            
            return new_incident

@app.get("/incidents/", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[StatusEnum] = None,
    priority: Optional[PriorityEnum] = None,
    assigned_team: Optional[uuid.UUID] = None,
    assigned_user: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = """
                SELECT id, title, description, alert_config_id, status, priority, 
                       assigned_team, assigned_user, created_at, resolved_at, incident_data
                FROM incident
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND status = %s"
                params.append(status)
            if priority:
                query += " AND priority = %s"
                params.append(priority)
            if assigned_team:
                query += " AND assigned_team = %s"
                params.append(assigned_team)
            if assigned_user:
                query += " AND assigned_user = %s"
                params.append(assigned_user)
            if start_date and end_date:
                query += " AND created_at BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            
            cur.execute(query, params)
            return cur.fetchall()

@app.post("/incidents/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_incident(incident_id: uuid.UUID, resolution: IncidentResolveRequest):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Update incident status
            cur.execute("""
                UPDATE incident 
                SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, title, description, alert_config_id, status, priority, 
                          assigned_team, assigned_user, created_at, resolved_at, incident_data;
            """, (incident_id,))
            updated_incident = cur.fetchone()
            
            if not updated_incident:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            # Record resolution activity
            cur.execute("""
                INSERT INTO activity (incident_id, user_id, action, comment)
                VALUES (%s, %s, %s, %s)
            """, (
                incident_id,
                resolution.resolved_by,
                'RESOLVE',
                resolution.resolution_comments or 'Incident resolved'
            ))
            
            conn.commit()
            return updated_incident

# Activity Endpoints
@app.post("/activities/", response_model=ActivityResponse)
def create_activity(activity: ActivityCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO activity (incident_id, user_id, action, comment)
                VALUES (%s, %s, %s, %s)
                RETURNING id, incident_id, user_id, action, comment, created_at;
            """, (
                activity.incident_id,
                activity.user_id,
                activity.action,
                activity.comment
            ))
            conn.commit()
            return cur.fetchone()

# Continuing api.py from where it was cut off
@app.get("/incidents/{incident_id}/activities", response_model=List[ActivityResponse])
def list_incident_activities(incident_id: uuid.UUID):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, incident_id, user_id, action, comment, created_at
                FROM activity
                WHERE incident_id = %s
                ORDER BY created_at DESC
            """, (incident_id,))
            return cur.fetchall()
'''
# AI Analysis Endpoints
@app.post("/incidents/{incident_id}/ai-analysis", response_model=AiAnalysisResponse)
def create_ai_analysis(incident_id: uuid.UUID, analysis: AiAnalysisCreate):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO ai_analysis (incident_id, agent_name, analysis_result, confidence)
                VALUES (%s, %s, %s, %s)
                RETURNING id, incident_id, agent_name, analysis_result, confidence, created_at;
            """, (
                incident_id,
                analysis.agent_name,
                json.dumps(analysis.analysis_result),
                analysis.confidence
            ))
            conn.commit()
            return cur.fetchone()

@app.get("/incidents/{incident_id}/ai-analysis", response_model=List[AiAnalysisResponse])
def list_incident_ai_analysis(incident_id: uuid.UUID):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, incident_id, agent_name, analysis_result, confidence, created_at
                FROM ai_analysis
                WHERE incident_id = %s
                ORDER BY created_at DESC
            """, (incident_id,))
            return cur.fetchall()
'''
# Notification Endpoints
@app.get("/notifications/", response_model=List[NotificationResponse])
def list_notifications(
    status: Optional[str] = None,
    incident_id: Optional[uuid.UUID] = None,
    channel: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = """
                SELECT id, incident_id, channel, status, sent_at, recipient, retry_count, last_retry_at
                FROM notification
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND status = %s"
                params.append(status)
            if incident_id:
                query += " AND incident_id = %s"
                params.append(incident_id)
            if channel:
                query += " AND channel = %s"
                params.append(channel)
            
            query += " ORDER BY sent_at DESC NULLS FIRST LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            
            cur.execute(query, params)
            return cur.fetchall()

@app.post("/notifications/retry/{notification_id}", response_model=NotificationResponse)
def retry_notification(notification_id: uuid.UUID):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get notification details
            cur.execute("""
                SELECT n.id, n.incident_id, n.channel, n.recipient, i.title, i.incident_data
                FROM notification n
                JOIN incident i ON n.incident_id = i.id
                WHERE n.id = %s AND n.status = 'FAILED'
            """, (notification_id,))
            notification = cur.fetchone()
            
            if not notification:
                raise HTTPException(status_code=404, detail="Failed notification not found")
            
            # Update notification to RETRY status
            cur.execute("""
                UPDATE notification
                SET status = 'RETRY', retry_count = retry_count + 1, last_retry_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, incident_id, channel, status, sent_at, recipient, retry_count, last_retry_at
            """, (notification_id,))
            conn.commit()
            updated_notification = cur.fetchone()
            
            # Send notification again
            notification_service = NotificationService(settings)
            message = notification_service.create_incident_message(
                {"title": notification["title"], "id": notification["incident_id"], "priority": "MEDIUM", "status": "ACTIVE", "created_at": datetime.now()},
                notification["incident_data"]
            )
            
            if notification["channel"] == "email":
                notification_service.send_email(
                    [notification["recipient"]], 
                    f"Incident Alert: {notification['incident_id']}", 
                    message,
                    notification["incident_id"],
                    notification_id
                )
            elif notification["channel"] == "whatsapp":
                notification_service.send_whatsapp(
                    [notification["recipient"]],
                    message,
                    notification["incident_id"],
                    notification_id
                )
            
            return updated_notification

# Dashboard Endpoints
@app.get("/dashboard/summary")
def get_dashboard_summary():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get count of active incidents by priority
            cur.execute("""
                SELECT priority, COUNT(*) as count
                FROM incident
                WHERE status = 'ACTIVE'
                GROUP BY priority
                ORDER BY CASE 
                    WHEN priority = 'CRITICAL' THEN 1
                    WHEN priority = 'HIGH' THEN 2
                    WHEN priority = 'MEDIUM' THEN 3
                    WHEN priority = 'LOW' THEN 4
                END
            """)
            active_by_priority = cur.fetchall()
            
            # Get count of incidents by status
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM incident
                GROUP BY status
            """)
            by_status = cur.fetchall()
            
            # Get recent incidents
            cur.execute("""
                SELECT id, title, status, priority, created_at
                FROM incident
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent_incidents = cur.fetchall()
            
            # Get notification success rate
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
                FROM notification
                WHERE status IN ('SUCCESS', 'FAILED')
            """)
            notification_stats = cur.fetchone()
            
            success_rate = 0
            if notification_stats and notification_stats["total"] > 0:
                success_rate = (notification_stats["success"] / notification_stats["total"]) * 100
            
            return {
                "active_incidents_by_priority": active_by_priority,
                "incidents_by_status": by_status,
                "recent_incidents": recent_incidents,
                "notification_success_rate": round(success_rate, 2),
                "total_alerts": get_count(cur, "alert_config"),
                "total_incidents": get_count(cur, "incident"),
                "total_users": get_count(cur, "users"),
                "total_teams": get_count(cur, "team")
            }

def get_count(cursor, table):
    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
    result = cursor.fetchone()
    return result["count"] if result else 0
