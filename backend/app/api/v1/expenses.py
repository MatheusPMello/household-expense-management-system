import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.cycle import BillingCycle
from app.models.person import Person
from app.models.expense import Expense, ExpenseSplit
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseVendorStatusUpdate,
    ExpenseOut,
    ExpenseSplitOut,
)
from app.services.split_engine import calculate_splits, SplitEngineError
from app.services.cycle_service import verify_cycle_is_open

router = APIRouter(prefix="/expenses", tags=["Expenses & Splits"])


async def get_cycle_and_verify_access(
    cycle_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> BillingCycle:
    stmt = select(BillingCycle).where(BillingCycle.id == cycle_id)
    cycle = (await db.execute(stmt)).scalar_one_or_none()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing cycle not found."
        )

    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == cycle.household_id,
        HouseholdMember.user_id == user_id,
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )
    return cycle


def format_expense_out(expense: Expense, person_map: Dict[uuid.UUID, str]) -> ExpenseOut:
    splits_out = [
        ExpenseSplitOut(
            id=s.id,
            expense_id=s.expense_id,
            person_id=s.person_id,
            person_name=person_map.get(s.person_id, "Unknown"),
            assigned_amount_cents=s.assigned_amount_cents,
        )
        for s in expense.splits
    ]
    return ExpenseOut(
        id=expense.id,
        billing_cycle_id=expense.billing_cycle_id,
        title=expense.title,
        total_amount_cents=expense.total_amount_cents,
        is_fixed=expense.is_fixed,
        category=expense.category,
        due_date=expense.due_date,
        paid_to_vendor=expense.paid_to_vendor,
        split_type=expense.split_type,
        created_at=expense.created_at,
        splits=splits_out,
    )


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = await get_cycle_and_verify_access(data.billing_cycle_id, current_user.id, db)
    verify_cycle_is_open(cycle)

    # Validate that all involved persons belong to this household
    all_target_ids: List[uuid.UUID] = []
    if data.participant_ids:
        all_target_ids.extend(data.participant_ids)
    if data.percentages:
        all_target_ids.extend(data.percentages.keys())
    if data.exact_amounts:
        all_target_ids.extend(data.exact_amounts.keys())
    if data.weights:
        all_target_ids.extend(data.weights.keys())

    if not all_target_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one participant must be specified for expense splitting.",
        )

    p_stmt = select(Person).where(
        Person.household_id == cycle.household_id,
        Person.id.in_(all_target_ids),
    )
    household_persons = (await db.execute(p_stmt)).scalars().all()
    if len(household_persons) != len(set(all_target_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more specified participants do not belong to this household.",
        )

    person_name_map = {p.id: p.name for p in household_persons}

    # Execute split calculation
    try:
        calculated_splits = calculate_splits(
            total_amount_cents=data.total_amount_cents,
            split_type=data.split_type,
            participant_ids=data.participant_ids,
            percentages=data.percentages,
            exact_amounts=data.exact_amounts,
            weights=data.weights,
        )
    except SplitEngineError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    expense = Expense(
        billing_cycle_id=cycle.id,
        title=data.title.strip(),
        total_amount_cents=data.total_amount_cents,
        is_fixed=data.is_fixed,
        category=data.category.strip(),
        due_date=data.due_date,
        paid_to_vendor=False,
        split_type=data.split_type,
    )
    db.add(expense)
    await db.flush()

    for s in calculated_splits:
        split_record = ExpenseSplit(
            expense_id=expense.id,
            person_id=s.person_id,
            assigned_amount_cents=s.assigned_amount_cents,
        )
        db.add(split_record)

    await db.commit()

    # Re-fetch with loaded splits
    refetch_stmt = (
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.splits))
    )
    expense_loaded = (await db.execute(refetch_stmt)).scalar_one()

    return format_expense_out(expense_loaded, person_name_map)


@router.put("/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Expense)
        .where(Expense.id == expense_id)
        .options(selectinload(Expense.splits))
    )
    expense = (await db.execute(stmt)).scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found."
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    # Determine updated values
    new_title = data.title.strip() if data.title is not None else expense.title
    new_amount = (
        data.total_amount_cents
        if data.total_amount_cents is not None
        else expense.total_amount_cents
    )
    new_is_fixed = data.is_fixed if data.is_fixed is not None else expense.is_fixed
    new_category = (
        data.category.strip() if data.category is not None else expense.category
    )
    new_due_date = data.due_date if data.due_date is not None else expense.due_date
    new_split_type = data.split_type or expense.split_type

    # Validate that any provided participants belong to this household
    all_target_ids: List[uuid.UUID] = []
    if data.participant_ids:
        all_target_ids.extend(data.participant_ids)
    if data.percentages:
        all_target_ids.extend(data.percentages.keys())
    if data.exact_amounts:
        all_target_ids.extend(data.exact_amounts.keys())
    if data.weights:
        all_target_ids.extend(data.weights.keys())

    if all_target_ids:
        p_stmt = select(Person).where(
            Person.household_id == cycle.household_id,
            Person.id.in_(all_target_ids),
        )
        household_persons = (await db.execute(p_stmt)).scalars().all()
        if len(household_persons) != len(set(all_target_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more specified participants do not belong to this household.",
            )

    has_split_data = any(
        x is not None
        for x in (
            data.participant_ids,
            data.percentages,
            data.exact_amounts,
            data.weights,
        )
    )
    amount_changed = (
        data.total_amount_cents is not None
        and data.total_amount_cents != expense.total_amount_cents
    )
    type_changed = (
        data.split_type is not None and data.split_type != expense.split_type
    )

    if has_split_data or amount_changed or type_changed:
        participant_ids = data.participant_ids
        if participant_ids is None and not any(
            (data.percentages, data.exact_amounts, data.weights)
        ):
            # Retain existing participants if split type is EQUAL
            if new_split_type == "EQUAL":
                participant_ids = [s.person_id for s in expense.splits]
            elif new_split_type == "PERCENTAGE" and not data.percentages:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Updating amount or switching to PERCENTAGE split requires providing percentages.",
                )
            elif new_split_type == "EXACT" and not data.exact_amounts:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Updating amount or switching to EXACT split requires providing exact amounts.",
                )
            elif new_split_type == "WEIGHTED" and not data.weights:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Updating amount or switching to WEIGHTED split requires providing weights.",
                )

        try:
            calculated_splits = calculate_splits(
                total_amount_cents=new_amount,
                split_type=new_split_type,
                participant_ids=participant_ids,
                percentages=data.percentages,
                exact_amounts=data.exact_amounts,
                weights=data.weights,
            )
        except SplitEngineError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )

        # Remove existing splits
        del_stmt = delete(ExpenseSplit).where(ExpenseSplit.expense_id == expense.id)
        await db.execute(del_stmt)

        for s in calculated_splits:
            new_split = ExpenseSplit(
                expense_id=expense.id,
                person_id=s.person_id,
                assigned_amount_cents=s.assigned_amount_cents,
            )
            db.add(new_split)

    expense.title = new_title
    expense.total_amount_cents = new_amount
    expense.is_fixed = new_is_fixed
    expense.category = new_category
    expense.due_date = new_due_date
    expense.split_type = new_split_type

    await db.commit()

    # Re-fetch
    refetch_stmt = (
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.splits))
    )
    expense_loaded = (await db.execute(refetch_stmt)).scalar_one()

    # Persons map
    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return format_expense_out(expense_loaded, person_map)


@router.patch("/{expense_id}/vendor-status", response_model=ExpenseOut)
async def update_vendor_status(
    expense_id: uuid.UUID,
    data: ExpenseVendorStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Expense)
        .where(Expense.id == expense_id)
        .options(selectinload(Expense.splits))
    )
    expense = (await db.execute(stmt)).scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found."
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )

    expense.paid_to_vendor = data.paid_to_vendor
    await db.commit()
    await db.refresh(expense)

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return format_expense_out(expense, person_map)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Expense).where(Expense.id == expense_id)
    expense = (await db.execute(stmt)).scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found."
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    await db.delete(expense)
    await db.commit()
    return None
