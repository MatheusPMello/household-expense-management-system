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
from app.models.fixed_template import FixedExpenseTemplate
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpensePaymentStatusUpdate,
    ExpenseSetAmount,
    ExpenseOut,
    ExpenseSplitOut,
)
from app.services.split_engine import calculate_splits, SplitEngineError
from app.services.cycle_service import verify_cycle_is_open

EXPENSE_NOT_FOUND = "Expense not found."

router = APIRouter(prefix="/expenses", tags=["Expenses & Splits"])


def _extract_participant_ids(
    data: ExpenseCreate | ExpenseUpdate,
) -> list[uuid.UUID]:
    target_ids: list[uuid.UUID] = []
    if data.participant_ids:
        target_ids.extend(data.participant_ids)
    if data.percentages:
        target_ids.extend(data.percentages.keys())
    if data.exact_amounts:
        target_ids.extend(data.exact_amounts.keys())
    if data.weights:
        target_ids.extend(data.weights.keys())
    return target_ids


async def _verify_household_participants(
    db: AsyncSession, household_id: uuid.UUID, target_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not target_ids:
        return {}
    p_stmt = select(Person).where(
        Person.household_id == household_id,
        Person.id.in_(target_ids),
    )
    household_persons = (await db.execute(p_stmt)).scalars().all()
    if len(household_persons) != len(set(target_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more specified participants do not belong to this household.",
        )
    return {p.id: p.name for p in household_persons}


async def _create_template_from_expense(
    db: AsyncSession, household_id: uuid.UUID, data: ExpenseCreate
) -> tuple[uuid.UUID, bool, str]:
    tpl_split_config: Dict = {}
    if data.participant_ids:
        tpl_split_config["participant_ids"] = [str(pid) for pid in data.participant_ids]
    if data.percentages:
        tpl_split_config["percentages"] = {str(k): v for k, v in data.percentages.items()}
    if data.weights:
        tpl_split_config["weights"] = {str(k): v for k, v in data.weights.items()}

    tpl = FixedExpenseTemplate(
        household_id=household_id,
        title=data.title.strip(),
        recurrence_type=data.recurrence_type,
        estimated_amount_cents=data.total_amount_cents if data.total_amount_cents > 0 else None,
        due_day=data.due_day or data.due_date.day,
        category=data.category.strip(),
        is_active=True,
        split_type=data.split_type,
        split_config=tpl_split_config if tpl_split_config else None,
    )
    db.add(tpl)
    await db.flush()
    is_fixed = data.recurrence_type == "FIXED"
    if data.recurrence_type == "VARIABLE" and data.total_amount_cents == 0:
        target_status = "PENDING_VALUE"
    else:
        target_status = data.status or "READY"
    return tpl.id, is_fixed, target_status


async def _recalculate_and_apply_splits(
    db: AsyncSession,
    expense: Expense,
    new_amount: int,
    new_split_type: str,
    data: ExpenseUpdate,
) -> None:
    participant_ids = data.participant_ids
    if participant_ids is None and not any((data.percentages, data.exact_amounts, data.weights)):
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

    del_stmt = delete(ExpenseSplit).where(ExpenseSplit.expense_id == expense.id)
    await db.execute(del_stmt)

    for s in calculated_splits:
        db.add(
            ExpenseSplit(
                expense_id=expense.id,
                person_id=s.person_id,
                assigned_amount_cents=s.assigned_amount_cents,
            )
        )


async def _resolve_split_rule_participants(
    db: AsyncSession, cycle: BillingCycle, expense: Expense
) -> tuple[str, Optional[list[uuid.UUID]], Optional[dict], Optional[dict]]:
    split_type = expense.split_type
    participant_ids: Optional[List[uuid.UUID]] = None
    percentages: Optional[Dict[uuid.UUID, float]] = None
    weights: Optional[Dict[uuid.UUID, float]] = None

    if expense.template:
        split_type = expense.template.split_type or split_type
        cfg = expense.template.split_config or {}
        raw_pids = cfg.get("participant_ids")
        if raw_pids:
            participant_ids = [uuid.UUID(str(pid)) for pid in raw_pids]
        if cfg.get("percentages"):
            percentages = {
                uuid.UUID(str(k)): float(v) for k, v in cfg["percentages"].items()
            }
        if cfg.get("weights"):
            weights = {
                uuid.UUID(str(k)): float(v) for k, v in cfg["weights"].items()
            }

    if not participant_ids and expense.splits:
        participant_ids = [s.person_id for s in expense.splits]

    if not participant_ids and not percentages and not weights:
        p_stmt = select(Person).where(
            Person.household_id == cycle.household_id,
            Person.is_active == True,
            Person.is_deleted == False,
        )
        active_persons = (await db.execute(p_stmt)).scalars().all()
        participant_ids = [p.id for p in active_persons]

    return split_type, participant_ids, percentages, weights


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
        template_id=expense.template_id,
        title=expense.title,
        total_amount_cents=expense.total_amount_cents,
        is_fixed=expense.is_fixed,
        category=expense.category,
        due_date=expense.due_date,
        is_paid=expense.is_paid,
        split_type=expense.split_type,
        status=expense.status,
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

    all_target_ids = _extract_participant_ids(data)
    if not all_target_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one participant must be specified for expense splitting.",
        )

    person_name_map = await _verify_household_participants(
        db, cycle.household_id, all_target_ids
    )

    template_id = data.template_id
    is_fixed = data.is_fixed
    target_status = data.status or "READY"

    if data.recurrence_type in ("FIXED", "VARIABLE") and not template_id:
        template_id, is_fixed, target_status = await _create_template_from_expense(
            db, cycle.household_id, data
        )

    calculated_splits = []
    if data.total_amount_cents > 0:
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
    else:
        target_status = "PENDING_VALUE"

    expense = Expense(
        billing_cycle_id=cycle.id,
        template_id=template_id,
        title=data.title.strip(),
        total_amount_cents=data.total_amount_cents,
        is_fixed=is_fixed,
        category=data.category.strip(),
        due_date=data.due_date,
        is_paid=False,
        split_type=data.split_type,
        status=target_status,
    )
    db.add(expense)
    await db.flush()

    for s in calculated_splits:
        db.add(
            ExpenseSplit(
                expense_id=expense.id,
                person_id=s.person_id,
                assigned_amount_cents=s.assigned_amount_cents,
            )
        )

    await db.commit()

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
            status_code=status.HTTP_404_NOT_FOUND, detail=EXPENSE_NOT_FOUND
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

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

    all_target_ids = _extract_participant_ids(data)
    await _verify_household_participants(db, cycle.household_id, all_target_ids)

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
        await _recalculate_and_apply_splits(
            db, expense, new_amount, new_split_type, data
        )

    expense.title = new_title
    expense.total_amount_cents = new_amount
    expense.is_fixed = new_is_fixed
    expense.category = new_category
    expense.due_date = new_due_date
    expense.split_type = new_split_type
    if data.status is not None:
        expense.status = data.status

    await db.commit()

    refetch_stmt = (
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.splits))
    )
    expense_loaded = (await db.execute(refetch_stmt)).scalar_one()

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return format_expense_out(expense_loaded, person_map)


@router.patch("/{expense_id}/amount", response_model=ExpenseOut)
async def set_expense_amount(
    expense_id: uuid.UUID,
    data: ExpenseSetAmount,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Expense)
        .where(Expense.id == expense_id)
        .options(selectinload(Expense.splits), selectinload(Expense.template))
    )
    expense = (await db.execute(stmt)).scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=EXPENSE_NOT_FOUND
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    if expense.template_id and data.update_template_default:
        tpl_stmt = select(FixedExpenseTemplate).where(
            FixedExpenseTemplate.id == expense.template_id
        )
        tpl = (await db.execute(tpl_stmt)).scalar_one_or_none()
        if tpl:
            tpl.estimated_amount_cents = data.actual_amount_cents

    split_type, participant_ids, percentages, weights = (
        await _resolve_split_rule_participants(db, cycle, expense)
    )

    try:
        calculated_splits = calculate_splits(
            total_amount_cents=data.actual_amount_cents,
            split_type=split_type,
            participant_ids=participant_ids,
            percentages=percentages,
            exact_amounts=None,
            weights=weights,
        )
    except SplitEngineError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )

    expense.splits.clear()
    for s in calculated_splits:
        expense.splits.append(
            ExpenseSplit(
                person_id=s.person_id,
                assigned_amount_cents=s.assigned_amount_cents,
            )
        )

    expense.total_amount_cents = data.actual_amount_cents
    expense.status = "READY"
    expense.split_type = split_type

    await db.commit()
    await db.refresh(expense, attribute_names=["splits"])

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return format_expense_out(expense, person_map)

    expense.total_amount_cents = data.actual_amount_cents
    expense.status = "READY"
    expense.split_type = split_type

    await db.commit()
    await db.refresh(expense, attribute_names=["splits"])

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return format_expense_out(expense, person_map)


@router.patch("/{expense_id}/payment-status", response_model=ExpenseOut)
async def update_payment_status(
    expense_id: uuid.UUID,
    data: ExpensePaymentStatusUpdate,
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
            status_code=status.HTTP_404_NOT_FOUND, detail=EXPENSE_NOT_FOUND
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )

    expense.is_paid = data.is_paid
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
            status_code=status.HTTP_404_NOT_FOUND, detail=EXPENSE_NOT_FOUND
        )

    cycle = await get_cycle_and_verify_access(
        expense.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    await db.delete(expense)
    await db.commit()
    return None
