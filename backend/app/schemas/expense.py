import uuid
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExpenseSplitOut(BaseModel):
    id: uuid.UUID
    expense_id: uuid.UUID
    person_id: uuid.UUID
    person_name: str
    assigned_amount_cents: int

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    billing_cycle_id: uuid.UUID
    title: str = Field(min_length=1, max_length=150)
    total_amount_cents: int = Field(ge=0, default=0)
    is_fixed: bool = False
    category: str = Field(min_length=1, max_length=50)
    due_date: date
    split_type: str = Field(pattern="^(EQUAL|PERCENTAGE|EXACT|WEIGHTED)$")
    participant_ids: Optional[List[uuid.UUID]] = None
    percentages: Optional[Dict[uuid.UUID, float]] = None
    exact_amounts: Optional[Dict[uuid.UUID, int]] = None
    weights: Optional[Dict[uuid.UUID, float]] = None
    recurrence_type: Optional[str] = Field(default=None, pattern="^(ONE_OFF|FIXED|VARIABLE)$")
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    template_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default="READY", pattern="^(PENDING_VALUE|READY|SETTLED)$")


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    total_amount_cents: Optional[int] = Field(default=None, ge=0)
    is_fixed: Optional[bool] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    due_date: Optional[date] = None
    split_type: Optional[str] = Field(default=None, pattern="^(EQUAL|PERCENTAGE|EXACT|WEIGHTED)$")
    participant_ids: Optional[List[uuid.UUID]] = None
    percentages: Optional[Dict[uuid.UUID, float]] = None
    exact_amounts: Optional[Dict[uuid.UUID, int]] = None
    weights: Optional[Dict[uuid.UUID, float]] = None
    status: Optional[str] = Field(default=None, pattern="^(PENDING_VALUE|READY|SETTLED)$")


class ExpensePaymentStatusUpdate(BaseModel):
    is_paid: bool


class ExpenseSetAmount(BaseModel):
    actual_amount_cents: int = Field(gt=0)
    update_template_default: bool = False


class ExpenseOut(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    template_id: Optional[uuid.UUID] = None
    title: str
    total_amount_cents: int
    is_fixed: bool
    category: str
    due_date: date
    is_paid: bool
    split_type: str
    status: str = "READY"
    created_at: datetime
    splits: List[ExpenseSplitOut] = []

    model_config = ConfigDict(from_attributes=True)
