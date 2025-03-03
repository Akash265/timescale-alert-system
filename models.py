
# models.py
from pydantic import BaseModel, UUID4, Field, EmailStr, validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import uuid
from enum import Enum

class PriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class StatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RESOLVED = "RESOLVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"

class NotificationStatusEnum(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"
    PENDING = "PENDING"

class DataSourceCreate(BaseModel):
    name: str
    type: str
    connection_details: Dict[str, Any]

class DataSourceResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    connection_details: Dict[str, Any]
    created_at: datetime

class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TeamResponse(BaseModel):
    id: UUID4
    name: str
    description: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    team_id: Optional[UUID4] = None

class UserResponse(BaseModel):
    id: UUID4
    name: str
    email: EmailStr
    team_id: Optional[UUID4] = None
    created_at: datetime

class AlertConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    query: str
    data_source_id: UUID4
    trigger_condition: Optional[str] = None
    schedule: str
    notification_channels: Dict[str, List[str]]
    priority: PriorityEnum = PriorityEnum.MEDIUM
    created_by: UUID4

    @validator('schedule')
    def validate_schedule(cls, v):
        valid_formats = ['cron:', 'interval:']
        if not any(v.startswith(fmt) for fmt in valid_formats):
            raise ValueError('Schedule must start with either "cron:" or "interval:"')
        return v

class AlertConfigResponse(BaseModel):
    id: UUID4
    name: str
    description: Optional[str] = None
    query: str
    data_source_id: UUID4
    trigger_condition: Optional[str] = None
    schedule: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID4
    notification_channels: Dict[str, List[str]]
    priority: PriorityEnum

class IncidentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    alert_config_id: UUID4
    priority: PriorityEnum
    assigned_team: Optional[UUID4] = None
    assigned_user: Optional[UUID4] = None
    incident_data: Optional[Dict[str, Any]] = None

class IncidentResponse(BaseModel):
    id: UUID4
    title: str
    description: Optional[str] = None
    alert_config_id: UUID4
    status: StatusEnum
    priority: PriorityEnum
    assigned_team: Optional[UUID4] = None
    assigned_user: Optional[UUID4] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    incident_data: Optional[Dict[str, Any]] = None

class NotificationCreate(BaseModel):
    incident_id: UUID4
    channel: str
    recipient: str

class NotificationResponse(BaseModel):
    id: UUID4
    incident_id: UUID4
    channel: str
    status: NotificationStatusEnum
    sent_at: Optional[datetime] = None
    recipient: str
    retry_count: int
    last_retry_at: Optional[datetime] = None

class ActivityCreate(BaseModel):
    incident_id: UUID4
    user_id: UUID4
    action: str
    comment: Optional[str] = None

class ActivityResponse(BaseModel):
    id: UUID4
    incident_id: UUID4
    user_id: UUID4
    action: str
    comment: Optional[str] = None
    created_at: datetime

class IncidentResolveRequest(BaseModel):
    incident_id: UUID4
    resolved_by: UUID4
    resolution_comments: Optional[str] = None

class AiAnalysisCreate(BaseModel):
    incident_id: UUID4
    agent_name: str
    analysis_result: Dict[str, Any]
    confidence: Optional[float] = None

class AiAnalysisResponse(BaseModel):
    id: UUID4
    incident_id: UUID4
    agent_name: str
    analysis_result: Dict[str, Any]
    confidence: Optional[float] = None
    created_at: datetime
