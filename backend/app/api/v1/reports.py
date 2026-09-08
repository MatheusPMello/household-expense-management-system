import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.cycle import BillingCycle
from app.schemas.report import CurrentCycleReport, GeneralBalanceReport
from app.services.balance_service import (
    calculate_cycle_report,
    calculate_general_balance_report,
)

router = APIRouter(prefix="/reports", tags=["Balances & Financial Reports"])


@router.get("/current-cycle", response_model=CurrentCycleReport)
async def get_current_cycle_report(
    cycle_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(BillingCycle).where(BillingCycle.id == cycle_id)
    cycle = (await db.execute(stmt)).scalar_one_or_none()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing cycle not found."
        )

    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == cycle.household_id,
        HouseholdMember.user_id == current_user.id,
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )

    return await calculate_cycle_report(db, cycle_id)


@router.get("/general-balance", response_model=GeneralBalanceReport)
async def get_general_balance_report(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == current_user.id,
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )

    return await calculate_general_balance_report(db, household_id)
