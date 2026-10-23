from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

Role = Literal["admin", "support_engineer", "user"]


class RegisterRequest(BaseModel):
    name: str = Field(max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8)
    user_type: str = Field(max_length=100)


class AdminUserCreateRequest(BaseModel):
    name: str = Field(max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8)
    role: Role = "support_engineer"
    user_type: Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _require_user_type_for_user_role(self):
        if self.role == "user" and not self.user_type:
            raise ValueError("user_type is required when role is 'user'.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    user_type: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)
