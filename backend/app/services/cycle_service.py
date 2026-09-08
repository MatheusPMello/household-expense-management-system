import calendar
import uuid
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cycle import BillingCycle
from app.models.fixed_template import FixedExpenseTemplate
from app.models.person import Person
from app.models.expense import Expense, ExpenseSplit
from app.services.split_engine import calculate_splits


def get_safe_due_date(year: int, month: int, due_day: int) -> date:
    """Returns valid date clamped to the max days in given year and month."""
    _, max_days = calendar.monthrange(year, month)
    valid_day = min(due_day, max_days)
    return date(year, month, valid_day)


async def _instantiate_template_expense(
    db: AsyncSession,
    cycle: BillingCycle,
    tpl: FixedExpenseTemplate,
    participant_ids: list[uuid.UUID],
    year: int,
    month: int,
) -> None:
    due_date = get_safe_due_date(year, month, tpl.due_day)
    is_fixed_type = getattr(tpl, "recurrence_type", "FIXED") == "FIXED"
    split_type_val = getattr(tpl, "split_type", "EQUAL") or "EQUAL"

    if is_fixed_type:
        total_cents = tpl.estimated_amount_cents or 0
        status_val = "READY"
    else:
        total_cents = 0
        status_val = "PENDING_VALUE"

    expense = Expense(
        billing_cycle_id=cycle.id,
        template_id=tpl.id,
        title=tpl.title,
        total_amount_cents=total_cents,
        is_fixed=is_fixed_type,
        category=tpl.category,
        due_date=due_date,
        is_paid=False,
        split_type=split_type_val,
        status=status_val,
    )
    db.add(expense)
    await db.flush()

    # For READY fixed expenses with an amount, calculate splits immediately
    if status_val == "READY" and total_cents > 0:
        cfg = getattr(tpl, "split_config", None) or {}
        raw_pids = cfg.get("participant_ids")
        if raw_pids:
            tpl_pids = [uuid.UUID(str(pid)) for pid in raw_pids]
            valid_pids = [pid for pid in tpl_pids if pid in participant_ids] or participant_ids
        else:
            valid_pids = participant_ids

        pcts = (
            {uuid.UUID(str(k)): float(v) for k, v in cfg.get("percentages", {}).items()}
            if cfg.get("percentages")
            else None
        )
        wts = (
            {uuid.UUID(str(k)): float(v) for k, v in cfg.get("weights", {}).items()}
            if cfg.get("weights")
            else None
        )

        splits = calculate_splits(
            total_amount_cents=total_cents,
            split_type=split_type_val,
            participant_ids=valid_pids,
            percentages=pcts,
            weights=wts,
        )
        for s in splits:
            db.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    person_id=s.person_id,
                    assigned_amount_cents=s.assigned_amount_cents,
                )
            )


async def create_billing_cycle(
    db: AsyncSession, household_id: uuid.UUID, year: int, month: int
) -> BillingCycle:
    # 1. Check for duplicate cycle
    stmt = select(BillingCycle).where(
        BillingCycle.household_id == household_id,
        BillingCycle.year == year,
        BillingCycle.month == month,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Billing cycle for {year}-{month:02d} already exists in this household.",
        )

    # 2. Instantiate new cycle
    cycle = BillingCycle(
        household_id=household_id,
        year=year,
        month=month,
        status="OPEN",
    )
    db.add(cycle)
    await db.flush()  # to obtain cycle.id

    # 3. Retrieve active recurring templates for this household
    stmt_templates = select(FixedExpenseTemplate).where(
        FixedExpenseTemplate.household_id == household_id,
        FixedExpenseTemplate.is_active == True,
    )
    templates = (await db.execute(stmt_templates)).scalars().all()

    # 4. Retrieve active persons in household
    stmt_persons = select(Person).where(
        Person.household_id == household_id,
        Person.is_active == True,
        Person.is_deleted == False,
    )
    active_persons = (await db.execute(stmt_persons)).scalars().all()
    participant_ids = [p.id for p in active_persons]

    # 5. Automatically instantiate recurring expenses if active persons exist
    if templates and participant_ids:
        for tpl in templates:
            await _instantiate_template_expense(
                db, cycle, tpl, participant_ids, year, month
            )

    await db.commit()
    await db.refresh(cycle)
    return cycle


def verify_cycle_is_open(cycle: BillingCycle) -> None:
    if cycle.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing cycle is CLOSED. Modifications, payments, and waivers are locked.",
        )
