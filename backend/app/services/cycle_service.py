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
    )
    active_persons = (await db.execute(stmt_persons)).scalars().all()
    participant_ids = [p.id for p in active_persons]

    # 5. Automatically instantiate recurring expenses if active persons exist
    if templates and participant_ids:
        for tpl in templates:
            due_date = get_safe_due_date(year, month, tpl.due_day)
            expense = Expense(
                billing_cycle_id=cycle.id,
                title=tpl.title,
                total_amount_cents=tpl.estimated_amount_cents,
                is_fixed=True,
                category=tpl.category,
                due_date=due_date,
                paid_to_vendor=False,
                split_type="EQUAL",
            )
            db.add(expense)
            await db.flush()

            # Penny-perfect equal split among active persons
            splits = calculate_splits(
                total_amount_cents=tpl.estimated_amount_cents,
                split_type="EQUAL",
                participant_ids=participant_ids,
            )
            for s in splits:
                split_record = ExpenseSplit(
                    expense_id=expense.id,
                    person_id=s.person_id,
                    assigned_amount_cents=s.assigned_amount_cents,
                )
                db.add(split_record)

    await db.commit()
    await db.refresh(cycle)
    return cycle


def verify_cycle_is_open(cycle: BillingCycle) -> None:
    if cycle.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing cycle is CLOSED. Modifications, payments, and waivers are locked.",
        )
