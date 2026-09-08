import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: str = Field(default="MEMBER", pattern="^(ADMIN|MEMBER)$")


class PersonLinkUser(BaseModel):
    email: EmailStr
    role: str = Field(default="MEMBER", pattern="^(ADMIN|MEMBER)$")


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class PersonOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_email: Optional[str] = None
    role: Optional[str] = None
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
