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
    total_amount_cents: int = Field(gt=0)
    is_fixed: bool = False
    category: str = Field(min_length=1, max_length=50)
    due_date: date
    split_type: str = Field(pattern="^(EQUAL|PERCENTAGE|EXACT|WEIGHTED)$")
    participant_ids: Optional[List[uuid.UUID]] = None
    percentages: Optional[Dict[uuid.UUID, float]] = None
    exact_amounts: Optional[Dict[uuid.UUID, int]] = None
    weights: Optional[Dict[uuid.UUID, float]] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    total_amount_cents: Optional[int] = Field(default=None, gt=0)
    is_fixed: Optional[bool] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    due_date: Optional[date] = None
    split_type: Optional[str] = Field(default=None, pattern="^(EQUAL|PERCENTAGE|EXACT|WEIGHTED)$")
    participant_ids: Optional[List[uuid.UUID]] = None
    percentages: Optional[Dict[uuid.UUID, float]] = None
    exact_amounts: Optional[Dict[uuid.UUID, int]] = None
    weights: Optional[Dict[uuid.UUID, float]] = None


class ExpenseVendorStatusUpdate(BaseModel):
    paid_to_vendor: bool


class ExpenseOut(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    title: str
    total_amount_cents: int
    is_fixed: bool
    category: str
    due_date: date
    paid_to_vendor: bool
    split_type: str
    created_at: datetime
    splits: List[ExpenseSplitOut] = []

    model_config = ConfigDict(from_attributes=True)
