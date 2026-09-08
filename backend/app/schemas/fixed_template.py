import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class FixedTemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    recurrence_type: str = Field(default="FIXED", pattern="^(FIXED|VARIABLE)$")
    estimated_amount_cents: Optional[int] = Field(default=None, ge=0)
    due_day: int = Field(ge=1, le=31)
    category: str = Field(min_length=1, max_length=50)
    is_active: bool = True
    split_type: str = Field(default="EQUAL", pattern="^(EQUAL|PERCENTAGE|WEIGHTED)$")
    split_config: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_fixed_amount(self) -> "FixedTemplateCreate":
        if self.recurrence_type == "FIXED" and (self.estimated_amount_cents is None or self.estimated_amount_cents <= 0):
            raise ValueError("Fixed recurring templates require an estimated_amount_cents greater than 0.")
        return self


class FixedTemplateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    recurrence_type: Optional[str] = Field(default=None, pattern="^(FIXED|VARIABLE)$")
    estimated_amount_cents: Optional[int] = Field(default=None, ge=0)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    split_type: Optional[str] = Field(default=None, pattern="^(EQUAL|PERCENTAGE|WEIGHTED)$")
    split_config: Optional[Dict[str, Any]] = None


class FixedTemplateOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    title: str
    recurrence_type: str = "FIXED"
    estimated_amount_cents: Optional[int] = None
    due_day: int
    category: str
    is_active: bool
    split_type: str = "EQUAL"
    split_config: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
