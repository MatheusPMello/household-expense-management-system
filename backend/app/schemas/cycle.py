import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BillingCycleCreate(BaseModel):
    household_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class BillingCycleOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    year: int
    month: int
    status: str
    closed_at: Optional[datetime] = None
    created_at: datetime
    total_expenses_cents: int = 0
    total_paid_to_vendor_cents: int = 0
    total_collected_cents: int = 0
    total_waived_cents: int = 0

    model_config = ConfigDict(from_attributes=True)
