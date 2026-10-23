from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationLogResponse(BaseModel):
    id: str
    ticket_id: Optional[str] = None
    template_key: str
    to_phone: Optional[str] = None
    status: str
    karix_message_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


class KarixWebhookRequest(BaseModel):
    source: str
    text: Optional[str] = ""
