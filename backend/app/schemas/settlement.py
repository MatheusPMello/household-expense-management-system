import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PaymentCreate(BaseModel):
    billing_cycle_id: uuid.UUID
    person_id: uuid.UUID
    amount_cents: int = Field(gt=0)
    notes: Optional[str] = None
    proof_url: Optional[str] = None


class PaymentOut(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    person_id: uuid.UUID
    person_name: str
    amount_cents: int
    paid_at: datetime
    notes: Optional[str] = None
    proof_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DebtWaiverCreate(BaseModel):
    billing_cycle_id: uuid.UUID
    person_id: uuid.UUID
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=3, description="Audited explanation for debt forgiveness")


class DebtWaiverOut(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    person_id: uuid.UUID
    person_name: str
    amount_cents: int
    waived_at: datetime
    reason: str

    model_config = ConfigDict(from_attributes=True)


class PaymentUpdate(BaseModel):
    amount_cents: Optional[int] = Field(default=None, gt=0)
    notes: Optional[str] = None
    proof_url: Optional[str] = None


class DebtWaiverUpdate(BaseModel):
    amount_cents: Optional[int] = Field(default=None, gt=0)
    reason: Optional[str] = Field(default=None, min_length=3)

