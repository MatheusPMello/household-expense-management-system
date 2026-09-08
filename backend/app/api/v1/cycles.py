import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.cycle import BillingCycle
from app.models.expense import Expense
from app.models.payment import Payment
from app.models.debt_waiver import DebtWaiver
from app.schemas.cycle import BillingCycleCreate, BillingCycleOut
from app.services.cycle_service import create_billing_cycle

router = APIRouter(prefix="/cycles", tags=["Billing Cycles"])


async def check_member_access(
    household_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> HouseholdMember:
    stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == user_id,
    )
    m = (await db.execute(stmt)).scalar_one_or_none()
    if not m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )
    return m


async def check_admin_access(
    household_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> HouseholdMember:
    m = await check_member_access(household_id, user_id, db)
    if m.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required in this household.",
        )
    return m


@router.get("", response_model=List[BillingCycleOut])
async def list_cycles(
    household_id: uuid.UUID = Query(...),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await check_member_access(household_id, current_user.id, db)

    query = (
        select(BillingCycle)
        .where(BillingCycle.household_id == household_id)
        .options(
            selectinload(BillingCycle.expenses),
            selectinload(BillingCycle.payments),
            selectinload(BillingCycle.debt_waivers),
        )
        .order_by(BillingCycle.year.desc(), BillingCycle.month.desc())
    )
    if year is not None:
        query = query.where(BillingCycle.year == year)
    if month is not None:
        query = query.where(BillingCycle.month == month)

    cycles = (await db.execute(query)).scalars().all()

    results = []
    for c in cycles:
        total_exp = sum(e.total_amount_cents for e in c.expenses)
        total_paid = sum(
            e.total_amount_cents for e in c.expenses if e.is_paid
        )
        total_collected = sum(p.amount_cents for p in c.payments)
        total_waived = sum(w.amount_cents for w in c.debt_waivers)

        results.append(
            BillingCycleOut(
                id=c.id,
                household_id=c.household_id,
                year=c.year,
                month=c.month,
                status=c.status,
                closed_at=c.closed_at,
                created_at=c.created_at,
                total_expenses_cents=total_exp,
                total_paid_cents=total_paid,
                total_collected_cents=total_collected,
                total_waived_cents=total_waived,
            )
        )
    return results


async def _build_cycle_out(cycle_id: uuid.UUID, db: AsyncSession) -> BillingCycleOut:
    stmt = (
        select(BillingCycle)
        .where(BillingCycle.id == cycle_id)
        .options(
            selectinload(BillingCycle.expenses),
            selectinload(BillingCycle.payments),
            selectinload(BillingCycle.debt_waivers),
        )
    )
    cycle_full = (await db.execute(stmt)).scalar_one()

    total_exp = sum(e.total_amount_cents for e in cycle_full.expenses)
    total_paid = sum(
        e.total_amount_cents for e in cycle_full.expenses if e.is_paid
    )
    total_collected = sum(p.amount_cents for p in cycle_full.payments)
    total_waived = sum(w.amount_cents for w in cycle_full.debt_waivers)

    return BillingCycleOut(
        id=cycle_full.id,
        household_id=cycle_full.household_id,
        year=cycle_full.year,
        month=cycle_full.month,
        status=cycle_full.status,
        closed_at=cycle_full.closed_at,
        created_at=cycle_full.created_at,
        total_expenses_cents=total_exp,
        total_paid_cents=total_paid,
        total_collected_cents=total_collected,
        total_waived_cents=total_waived,
    )


@router.post("", response_model=BillingCycleOut, status_code=status.HTTP_201_CREATED)
async def create_cycle(
    data: BillingCycleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await check_admin_access(data.household_id, current_user.id, db)

    cycle = await create_billing_cycle(
        db=db,
        household_id=data.household_id,
        year=data.year,
        month=data.month,
    )

    return await _build_cycle_out(cycle.id, db)


@router.post("/{cycle_id}/close", response_model=BillingCycleOut)
async def close_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(BillingCycle).where(BillingCycle.id == cycle_id)
    cycle = (await db.execute(stmt)).scalar_one_or_none()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing cycle not found."
        )

    await check_admin_access(cycle.household_id, current_user.id, db)

    # Ensure no expenses remain in PENDING_VALUE before closing the cycle
    pending_stmt = select(Expense).where(
        Expense.billing_cycle_id == cycle_id,
        Expense.status == "PENDING_VALUE",
    )
    pending_expenses = (await db.execute(pending_stmt)).scalars().all()
    if pending_expenses:
        titles = ", ".join(f'"{e.title}"' for e in pending_expenses[:3])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot close billing cycle with pending recurring expenses ({titles}). Please enter their actual invoice amounts or remove them before closing.",
        )

    cycle.status = "CLOSED"
    cycle.closed_at = datetime.now(timezone.utc)
    await db.commit()

    return await _build_cycle_out(cycle.id, db)


@router.post("/{cycle_id}/reopen", response_model=BillingCycleOut)
async def reopen_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(BillingCycle).where(BillingCycle.id == cycle_id)
    cycle = (await db.execute(stmt)).scalar_one_or_none()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing cycle not found."
        )

    await check_admin_access(cycle.household_id, current_user.id, db)

    cycle.status = "OPEN"
    cycle.closed_at = None
    await db.commit()

    return await _build_cycle_out(cycle.id, db)
