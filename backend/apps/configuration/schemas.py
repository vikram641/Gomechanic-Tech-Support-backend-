from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OptionResponse(BaseModel):
    id: str
    name: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OptionCreate(BaseModel):
    name: str = Field(max_length=150)
    is_active: bool = True


class OptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    is_active: Optional[bool] = None


class PriorityResponse(BaseModel):
    id: str
    name: str
    level: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PriorityCreate(BaseModel):
    name: str = Field(max_length=150)
    level: int
    is_active: bool = True


class PriorityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    level: Optional[int] = None
    is_active: Optional[bool] = None


class WhatsAppTemplateResponse(BaseModel):
    id: str
    key: str
    karix_template_id: Optional[str] = None
    description: Optional[str] = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WhatsAppTemplateCreate(BaseModel):
    key: str = Field(max_length=100)
    karix_template_id: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = ""
    is_active: bool = True


class WhatsAppTemplateUpdate(BaseModel):
    key: Optional[str] = Field(default=None, max_length=100)
    karix_template_id: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SLARuleResponse(BaseModel):
    id: str
    priority: str
    response_time_minutes: int
    resolution_time_minutes: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SLARuleCreate(BaseModel):
    priority: str = Field(max_length=150)
    response_time_minutes: int = Field(ge=1)
    resolution_time_minutes: int = Field(ge=1)
    is_active: bool = True


class SLARuleUpdate(BaseModel):
    priority: Optional[str] = Field(default=None, max_length=150)
    response_time_minutes: Optional[int] = Field(default=None, ge=1)
    resolution_time_minutes: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None
