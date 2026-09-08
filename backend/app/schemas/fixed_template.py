import uuid
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FixedTemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    estimated_amount_cents: int = Field(gt=0)
    due_day: int = Field(ge=1, le=31)
    category: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class FixedTemplateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    estimated_amount_cents: Optional[int] = Field(default=None, gt=0)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class FixedTemplateOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    title: str
    estimated_amount_cents: int
    due_day: int
    category: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
