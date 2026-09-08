import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.person import Person
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment
from app.models.debt_waiver import DebtWaiver
from app.models.cycle import BillingCycle
from app.schemas.person import (
    PersonUpdate,
    PersonOut,
    PersonLinkUser,
    PersonHistoryOut,
    PersonSplitHistoryItem,
    PersonPaymentHistoryItem,
    PersonWaiverHistoryItem,
)

PERSON_NOT_FOUND = "Person not found."

router = APIRouter(prefix="/persons", tags=["Persons / Residents"])


def _build_split_history_items(splits: list) -> tuple[list[PersonSplitHistoryItem], int]:
    splits_out = []
    total_assigned = 0
    sorted_splits = sorted(
        splits, key=lambda x: (x.expense.due_date, x.expense.created_at), reverse=True
    )
    for s in sorted_splits:
        total_assigned += s.assigned_amount_cents
        cycle = s.expense.billing_cycle
        splits_out.append(
            PersonSplitHistoryItem(
                expense_id=s.expense_id,
                billing_cycle_id=s.expense.billing_cycle_id,
                cycle_year=cycle.year if cycle else 0,
                cycle_month=cycle.month if cycle else 0,
                expense_title=s.expense.title,
                category=s.expense.category,
                due_date=s.expense.due_date,
                assigned_amount_cents=s.assigned_amount_cents,
                is_paid=s.expense.is_paid,
            )
        )
    return splits_out, total_assigned


def _build_payment_history_items(payments: list) -> tuple[list[PersonPaymentHistoryItem], int]:
    payments_out = []
    total_paid = 0
    for p in payments:
        total_paid += p.amount_cents
        cycle = p.billing_cycle
        payments_out.append(
            PersonPaymentHistoryItem(
                id=p.id,
                billing_cycle_id=p.billing_cycle_id,
                cycle_year=cycle.year if cycle else 0,
                cycle_month=cycle.month if cycle else 0,
                amount_cents=p.amount_cents,
                paid_at=p.paid_at,
                notes=p.notes,
                proof_url=p.proof_url,
            )
        )
    return payments_out, total_paid


def _build_waiver_history_items(waivers: list) -> tuple[list[PersonWaiverHistoryItem], int]:
    waivers_out = []
    total_waived = 0
    for w in waivers:
        total_waived += w.amount_cents
        cycle = w.billing_cycle
        waivers_out.append(
            PersonWaiverHistoryItem(
                id=w.id,
                billing_cycle_id=w.billing_cycle_id,
                cycle_year=cycle.year if cycle else 0,
                cycle_month=cycle.month if cycle else 0,
                amount_cents=w.amount_cents,
                waived_at=w.waived_at,
                reason=w.reason,
            )
        )
    return waivers_out, total_waived


async def _handle_person_role_update(
    db: AsyncSession, person: Person, new_role: str
) -> None:
    if not person.user_id:
        return
    mem_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == person.user_id,
    )
    target_mem = (await db.execute(mem_stmt)).scalar_one_or_none()
    if not target_mem or target_mem.role == new_role:
        return

    if target_mem.role == "ADMIN" and new_role == "MEMBER":
        other_admins_stmt = select(func.count(HouseholdMember.id)).where(
            HouseholdMember.household_id == person.household_id,
            HouseholdMember.role == "ADMIN",
            HouseholdMember.user_id != person.user_id,
        )
        other_admins = (await db.execute(other_admins_stmt)).scalar() or 0
        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only administrator in the household.",
            )
    target_mem.role = new_role


async def _build_person_out(person: Person, db: AsyncSession) -> PersonOut:
    user_email: Optional[str] = None
    role: Optional[str] = None
    if person.user_id:
        user_stmt = select(User).where(User.id == person.user_id)
        u = (await db.execute(user_stmt)).scalar_one_or_none()
        if u:
            user_email = u.email
        mem_stmt = select(HouseholdMember).where(
            HouseholdMember.household_id == person.household_id,
            HouseholdMember.user_id == person.user_id,
        )
        m = (await db.execute(mem_stmt)).scalar_one_or_none()
        if m:
            role = m.role

    return PersonOut(
        id=person.id,
        household_id=person.household_id,
        user_id=person.user_id,
        user_email=user_email,
        role=role,
        name=person.name,
        is_active=person.is_active,
        is_deleted=person.is_deleted,
        deleted_at=person.deleted_at,
        created_at=person.created_at,
    )


@router.put("/{person_id}", response_model=PersonOut)
async def update_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Only household ADMIN can update resident details
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can update resident details.",
        )

    if person.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a deleted resident. Please restore them first.",
        )

    if data.name is not None:
        person.name = data.name.strip()
    if data.is_active is not None:
        person.is_active = data.is_active

    if data.role is not None:
        await _handle_person_role_update(db, person, data.role)

    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)


@router.delete("/{person_id}", response_model=PersonOut)
async def delete_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Only household ADMIN can delete residents
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can delete residents.",
        )

    if person.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resident is already deleted.",
        )

    # Prevent deleting own profile
    if person.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own resident profile.",
        )

    # If linked to an ADMIN, ensure at least one other ADMIN remains
    if person.user_id:
        mem_stmt = select(HouseholdMember).where(
            HouseholdMember.household_id == person.household_id,
            HouseholdMember.user_id == person.user_id,
            HouseholdMember.role == "ADMIN",
        )
        if (await db.execute(mem_stmt)).scalar_one_or_none():
            other_admins_stmt = select(func.count(HouseholdMember.id)).where(
                HouseholdMember.household_id == person.household_id,
                HouseholdMember.role == "ADMIN",
                HouseholdMember.user_id != person.user_id,
            )
            other_admins = (await db.execute(other_admins_stmt)).scalar() or 0
            if other_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the only administrator of the household.",
                )

    person.is_deleted = True
    person.is_active = False
    person.deleted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)


@router.post("/{person_id}/restore", response_model=PersonOut)
async def restore_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Only household ADMIN can restore residents
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can restore residents.",
        )

    if not person.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resident is not deleted.",
        )

    person.is_deleted = False
    person.is_active = True
    person.deleted_at = None

    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)


@router.get("/{person_id}/history", response_model=PersonHistoryOut)
async def get_person_history(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Check caller is a member of this household
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )

    # 1. Fetch splits with expense and cycle info
    splits_stmt = (
        select(ExpenseSplit)
        .where(ExpenseSplit.person_id == person.id)
        .options(
            selectinload(ExpenseSplit.expense).selectinload(Expense.billing_cycle)
        )
    )
    splits = (await db.execute(splits_stmt)).scalars().all()
    splits_out, total_assigned = _build_split_history_items(splits)

    # 2. Fetch payments with cycle info
    payments_stmt = (
        select(Payment)
        .where(Payment.person_id == person.id)
        .options(selectinload(Payment.billing_cycle))
        .order_by(Payment.paid_at.desc())
    )
    payments = (await db.execute(payments_stmt)).scalars().all()
    payments_out, total_paid = _build_payment_history_items(payments)

    # 3. Fetch debt waivers with cycle info
    waivers_stmt = (
        select(DebtWaiver)
        .where(DebtWaiver.person_id == person.id)
        .options(selectinload(DebtWaiver.billing_cycle))
        .order_by(DebtWaiver.waived_at.desc())
    )
    waivers = (await db.execute(waivers_stmt)).scalars().all()
    waivers_out, total_waived = _build_waiver_history_items(waivers)

    user_email: Optional[str] = None
    role: Optional[str] = None
    if person.user_id:
        user_stmt = select(User).where(User.id == person.user_id)
        u = (await db.execute(user_stmt)).scalar_one_or_none()
        if u:
            user_email = u.email
        mem_stmt = select(HouseholdMember).where(
            HouseholdMember.household_id == person.household_id,
            HouseholdMember.user_id == person.user_id,
        )
        m = (await db.execute(mem_stmt)).scalar_one_or_none()
        if m:
            role = m.role

    return PersonHistoryOut(
        person_id=person.id,
        household_id=person.household_id,
        name=person.name,
        person_name=person.name,
        user_id=person.user_id,
        user_email=user_email,
        role=role,
        is_active=person.is_active,
        is_deleted=person.is_deleted,
        deleted_at=person.deleted_at,
        created_at=person.created_at,
        total_assigned_cents=total_assigned,
        total_paid_cents=total_paid,
        total_waived_cents=total_waived,
        outstanding_balance_cents=total_assigned - (total_paid + total_waived),
        splits=splits_out,
        payments=payments_out,
        debt_waivers=waivers_out,
    )


@router.post("/{person_id}/link-user", response_model=PersonOut)
async def link_user_to_person(
    person_id: uuid.UUID,
    data: PersonLinkUser,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Only household ADMIN can link user accounts
    admin_check = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(admin_check)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can link user accounts.",
        )

    # Find user by email
    user_stmt = select(User).where(User.email == data.email.lower().strip())
    target_user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered user found with email '{data.email}'. Please ask them to register an account first.",
        )

    # Check if target_user is already linked to another person in this household
    exist_link = select(Person).where(
        Person.household_id == person.household_id,
        Person.user_id == target_user.id,
        Person.id != person.id,
    )
    if (await db.execute(exist_link)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{target_user.email}' is already linked to another resident in this household.",
        )

    person.user_id = target_user.id

    # Check or create HouseholdMember
    mem_check = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == target_user.id,
    )
    membership = (await db.execute(mem_check)).scalar_one_or_none()
    if not membership:
        membership = HouseholdMember(
            household_id=person.household_id,
            user_id=target_user.id,
            role=data.role,
        )
        db.add(membership)
    else:
        membership.role = data.role

    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)


@router.post("/{person_id}/unlink-user", response_model=PersonOut)
async def unlink_user_from_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Person).where(Person.id == person_id)
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PERSON_NOT_FOUND
        )

    # Only household ADMIN can unlink user accounts
    admin_check = select(HouseholdMember).where(
        HouseholdMember.household_id == person.household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(admin_check)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can unlink user accounts.",
        )

    person.user_id = None
    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)
