from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    filename: str
    url: str
    content_type: Optional[str] = ""
    uploaded_at: datetime


class ActivityLogEntryResponse(BaseModel):
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


class NoteResponse(BaseModel):
    author_id: str
    author_name: str
    note: str
    created_at: datetime


class TicketListItemResponse(BaseModel):
    id: str
    ticket_id: str
    title: str
    user_type: str
    platform: str
    category: Optional[str] = None
    priority: str
    status: str
    assigned_to_snapshot: Optional[dict] = None
    created_by_snapshot: Optional[dict] = None
    reopened_count: int
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketListItemResponse):
    description: str
    login_credentials: Optional[str] = None
    attachments: list[AttachmentResponse]
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    internal_notes: list[NoteResponse]
    csat_status: Optional[str] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class AssignRequest(BaseModel):
    engineer_id: str


class StatusUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None


class NoteCreateRequest(BaseModel):
    note: str


class CSATResponseRequest(BaseModel):
    satisfied: bool
