import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


ROLE_PATTERN = r"^(ADMIN|MEMBER)$"


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: str = Field(default="MEMBER", pattern=ROLE_PATTERN)


class PersonLinkUser(BaseModel):
    email: EmailStr
    role: str = Field(default="MEMBER", pattern=ROLE_PATTERN)


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(default=None, pattern=ROLE_PATTERN)


class PersonOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_email: Optional[str] = None
    role: Optional[str] = None
    name: str
    is_active: bool
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonSplitHistoryItem(BaseModel):
    expense_id: uuid.UUID
    billing_cycle_id: uuid.UUID
    cycle_year: int
    cycle_month: int
    expense_title: str
    category: str
    due_date: date
    assigned_amount_cents: int
    is_paid: bool


class PersonPaymentHistoryItem(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    cycle_year: int
    cycle_month: int
    amount_cents: int
    paid_at: datetime
    notes: Optional[str] = None
    proof_url: Optional[str] = None


class PersonWaiverHistoryItem(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    cycle_year: int
    cycle_month: int
    amount_cents: int
    waived_at: datetime
    reason: str


class PersonHistoryOut(BaseModel):
    person_id: uuid.UUID
    household_id: uuid.UUID
    name: str
    person_name: str
    user_id: Optional[uuid.UUID] = None
    user_email: Optional[str] = None
    role: Optional[str] = None
    is_active: bool
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    total_assigned_cents: int
    total_paid_cents: int
    total_waived_cents: int
    outstanding_balance_cents: int
    splits: List[PersonSplitHistoryItem]
    payments: List[PersonPaymentHistoryItem]
    debt_waivers: List[PersonWaiverHistoryItem]

