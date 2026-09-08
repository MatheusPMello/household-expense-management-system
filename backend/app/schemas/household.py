import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class HouseholdUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class HouseholdOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HouseholdMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="MEMBER", pattern="^(ADMIN|MEMBER)$")


class HouseholdMemberOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    full_name: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
