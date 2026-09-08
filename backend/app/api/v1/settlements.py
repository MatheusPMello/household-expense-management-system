import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.cycle import BillingCycle
from app.models.person import Person
from app.models.payment import Payment
from app.models.debt_waiver import DebtWaiver
from app.schemas.settlement import (
    PaymentCreate,
    PaymentUpdate,
    PaymentOut,
    DebtWaiverCreate,
    DebtWaiverUpdate,
    DebtWaiverOut,
)
from app.services.cycle_service import verify_cycle_is_open

router = APIRouter(prefix="/settlements", tags=["Settlements & Debt Waivers"])


async def get_cycle_and_member(
    cycle_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> tuple[BillingCycle, HouseholdMember]:
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
    membership = (await db.execute(check_stmt)).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )
    return cycle, membership


async def verify_person_in_household(
    person_id: uuid.UUID, household_id: uuid.UUID, db: AsyncSession
) -> Person:
    stmt = select(Person).where(
        Person.id == person_id,
        Person.household_id == household_id,
    )
    person = (await db.execute(stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resident does not belong to this household.",
        )
    return person


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle, membership = await get_cycle_and_member(
        data.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    person = await verify_person_in_household(data.person_id, cycle.household_id, db)

    # If member is not admin, they can only register payments for their own person record
    if membership.role != "ADMIN" and person.user_id != current_user.id:
        # Check if person is linked to current user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members can only register payments for themselves.",
        )

    payment = Payment(
        billing_cycle_id=cycle.id,
        person_id=person.id,
        amount_cents=data.amount_cents,
        notes=data.notes,
        proof_url=data.proof_url,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return PaymentOut(
        id=payment.id,
        billing_cycle_id=payment.billing_cycle_id,
        person_id=payment.person_id,
        person_name=person.name,
        amount_cents=payment.amount_cents,
        paid_at=payment.paid_at,
        notes=payment.notes,
        proof_url=payment.proof_url,
    )


@router.get("/payments", response_model=List[PaymentOut])
async def list_payments(
    billing_cycle_id: uuid.UUID = Query(...),
    person_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle, _ = await get_cycle_and_member(billing_cycle_id, current_user.id, db)

    stmt = select(Payment).where(Payment.billing_cycle_id == billing_cycle_id)
    if person_id is not None:
        stmt = stmt.where(Payment.person_id == person_id)
    stmt = stmt.order_by(Payment.paid_at.desc())
    payments = (await db.execute(stmt)).scalars().all()

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return [
        PaymentOut(
            id=p.id,
            billing_cycle_id=p.billing_cycle_id,
            person_id=p.person_id,
            person_name=person_map.get(p.person_id, "Unknown"),
            amount_cents=p.amount_cents,
            paid_at=p.paid_at,
            notes=p.notes,
            proof_url=p.proof_url,
        )
        for p in payments
    ]


@router.patch("/payments/{payment_id}", response_model=PaymentOut)
async def update_payment(
    payment_id: uuid.UUID,
    data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Payment).where(Payment.id == payment_id)
    payment = (await db.execute(stmt)).scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found."
        )

    cycle, membership = await get_cycle_and_member(
        payment.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    person_stmt = select(Person).where(Person.id == payment.person_id)
    person = (await db.execute(person_stmt)).scalar_one_or_none()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resident record not found."
        )

    if membership.role != "ADMIN" and person.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members can only edit payments for themselves.",
        )

    if data.amount_cents is not None:
        payment.amount_cents = data.amount_cents
    if data.notes is not None:
        payment.notes = data.notes
    if data.proof_url is not None:
        payment.proof_url = data.proof_url

    await db.commit()
    await db.refresh(payment)

    return PaymentOut(
        id=payment.id,
        billing_cycle_id=payment.billing_cycle_id,
        person_id=payment.person_id,
        person_name=person.name,
        amount_cents=payment.amount_cents,
        paid_at=payment.paid_at,
        notes=payment.notes,
        proof_url=payment.proof_url,
    )


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Payment).where(Payment.id == payment_id)
    payment = (await db.execute(stmt)).scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found."
        )

    cycle, membership = await get_cycle_and_member(
        payment.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required to delete a payment record.",
        )

    await db.delete(payment)
    await db.commit()
    return None


@router.post("/waivers", response_model=DebtWaiverOut, status_code=status.HTTP_201_CREATED)
async def record_debt_waiver(
    data: DebtWaiverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle, membership = await get_cycle_and_member(
        data.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can grant debt waivers.",
        )

    person = await verify_person_in_household(data.person_id, cycle.household_id, db)

    waiver = DebtWaiver(
        billing_cycle_id=cycle.id,
        person_id=person.id,
        amount_cents=data.amount_cents,
        reason=data.reason.strip(),
    )
    db.add(waiver)
    await db.commit()
    await db.refresh(waiver)

    return DebtWaiverOut(
        id=waiver.id,
        billing_cycle_id=waiver.billing_cycle_id,
        person_id=waiver.person_id,
        person_name=person.name,
        amount_cents=waiver.amount_cents,
        waived_at=waiver.waived_at,
        reason=waiver.reason,
    )


@router.get("/waivers", response_model=List[DebtWaiverOut])
async def list_waivers(
    billing_cycle_id: uuid.UUID = Query(...),
    person_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle, _ = await get_cycle_and_member(billing_cycle_id, current_user.id, db)

    stmt = select(DebtWaiver).where(DebtWaiver.billing_cycle_id == billing_cycle_id)
    if person_id is not None:
        stmt = stmt.where(DebtWaiver.person_id == person_id)
    stmt = stmt.order_by(DebtWaiver.waived_at.desc())
    waivers = (await db.execute(stmt)).scalars().all()

    p_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p.name for p in persons}

    return [
        DebtWaiverOut(
            id=w.id,
            billing_cycle_id=w.billing_cycle_id,
            person_id=w.person_id,
            person_name=person_map.get(w.person_id, "Unknown"),
            amount_cents=w.amount_cents,
            waived_at=w.waived_at,
            reason=w.reason,
        )
        for w in waivers
    ]


@router.patch("/waivers/{waiver_id}", response_model=DebtWaiverOut)
async def update_debt_waiver(
    waiver_id: uuid.UUID,
    data: DebtWaiverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(DebtWaiver).where(DebtWaiver.id == waiver_id)
    waiver = (await db.execute(stmt)).scalar_one_or_none()
    if not waiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Debt waiver record not found."
        )

    cycle, membership = await get_cycle_and_member(
        waiver.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can edit debt waiver records.",
        )

    person_stmt = select(Person).where(Person.id == waiver.person_id)
    person = (await db.execute(person_stmt)).scalar_one_or_none()
    person_name = person.name if person else "Unknown"

    if data.amount_cents is not None:
        waiver.amount_cents = data.amount_cents
    if data.reason is not None:
        waiver.reason = data.reason.strip()

    await db.commit()
    await db.refresh(waiver)

    return DebtWaiverOut(
        id=waiver.id,
        billing_cycle_id=waiver.billing_cycle_id,
        person_id=waiver.person_id,
        person_name=person_name,
        amount_cents=waiver.amount_cents,
        waived_at=waiver.waived_at,
        reason=waiver.reason,
    )


@router.delete("/waivers/{waiver_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt_waiver(
    waiver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(DebtWaiver).where(DebtWaiver.id == waiver_id)
    waiver = (await db.execute(stmt)).scalar_one_or_none()
    if not waiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Debt waiver record not found."
        )

    cycle, membership = await get_cycle_and_member(
        waiver.billing_cycle_id, current_user.id, db
    )
    verify_cycle_is_open(cycle)

    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete debt waiver records.",
        )

    await db.delete(waiver)
    await db.commit()
    return None
