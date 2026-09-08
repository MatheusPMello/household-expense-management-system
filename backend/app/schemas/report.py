import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel
from app.schemas.expense import ExpenseOut


class ResidentCycleBalance(BaseModel):
    person_id: uuid.UUID
    person_name: str
    assigned_cents: int
    paid_cents: int
    waived_cents: int
    remaining_balance_cents: int
    status: str  # "SETTLED", "OWES", "CREDIT"


class CurrentCycleReport(BaseModel):
    cycle_id: uuid.UUID
    year: int
    month: int
    status: str
    total_budget_cents: int
    total_paid_cents: int
    total_collected_cents: int
    total_waived_cents: int
    residents: List[ResidentCycleBalance]
    expenses: List[ExpenseOut]


class ResidentHistoricalSummary(BaseModel):
    person_id: uuid.UUID
    person_name: str
    total_assigned_cents: int
    total_paid_cents: int
    total_waived_cents: int
    compliance_rate_percent: float
    outstanding_historical_balance_cents: int


class DebtWaiverLedgerEntry(BaseModel):
    id: uuid.UUID
    billing_cycle_id: uuid.UUID
    cycle_year: int
    cycle_month: int
    person_id: uuid.UUID
    person_name: str
    amount_cents: int
    waived_at: datetime
    reason: str


class MonthlyTrajectoryPoint(BaseModel):
    cycle_id: uuid.UUID
    year: int
    month: int
    fixed_cents: int
    variable_cents: int
    total_cents: int


class GeneralBalanceReport(BaseModel):
    household_id: uuid.UUID
    residents: List[ResidentHistoricalSummary]
    debt_waiver_ledger: List[DebtWaiverLedgerEntry]
    trajectory: List[MonthlyTrajectoryPoint]
