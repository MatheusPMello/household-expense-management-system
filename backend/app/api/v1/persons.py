import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.person import Person
from app.schemas.person import PersonUpdate, PersonOut, PersonLinkUser

router = APIRouter(prefix="/persons", tags=["Persons / Residents"])


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found."
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

    if data.name is not None:
        person.name = data.name.strip()
    if data.is_active is not None:
        person.is_active = data.is_active

    await db.commit()
    await db.refresh(person)
    return await _build_person_out(person, db)


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found."
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found."
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
