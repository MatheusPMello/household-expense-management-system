import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import Household, HouseholdMember
from app.models.person import Person
from app.schemas.household import (
    HouseholdCreate,
    HouseholdOut,
    HouseholdMemberAdd,
    HouseholdMemberOut,
)
from app.schemas.person import PersonCreate, PersonOut

router = APIRouter(prefix="/households", tags=["Households & Residents"])


@router.post("", response_model=HouseholdOut, status_code=status.HTTP_201_CREATED)
async def create_household(
    data: HouseholdCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    household = Household(name=data.name.strip())
    db.add(household)
    await db.flush()

    membership = HouseholdMember(
        household_id=household.id,
        user_id=current_user.id,
        role="ADMIN",
    )
    db.add(membership)

    person = Person(
        household_id=household.id,
        user_id=current_user.id,
        name=current_user.full_name,
        is_active=True,
    )
    db.add(person)

    await db.commit()
    await db.refresh(household)

    return HouseholdOut(
        id=household.id,
        name=household.name,
        created_at=household.created_at,
        role="ADMIN",
    )


@router.get("/{household_id}", response_model=HouseholdOut)
async def get_household(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == current_user.id,
    ).options(selectinload(HouseholdMember.household))
    membership = (await db.execute(stmt)).scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )

    return HouseholdOut(
        id=membership.household.id,
        name=membership.household.name,
        created_at=membership.household.created_at,
        role=membership.role,
    )


@router.get("/{household_id}/members", response_model=List[HouseholdMemberOut])
async def list_household_members(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check access
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == current_user.id,
    )
    if not (await db.execute(check_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )

    stmt = (
        select(HouseholdMember)
        .where(HouseholdMember.household_id == household_id)
        .options(selectinload(HouseholdMember.user))
        .order_by(HouseholdMember.created_at)
    )
    members = (await db.execute(stmt)).scalars().all()

    return [
        HouseholdMemberOut(
            id=m.id,
            household_id=m.household_id,
            user_id=m.user_id,
            role=m.role,
            full_name=m.user.full_name,
            email=m.user.email,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    "/{household_id}/members",
    response_model=HouseholdMemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_household_member(
    household_id: uuid.UUID,
    data: HouseholdMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only ADMIN can invite/add members
    admin_check = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(admin_check)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can add members.",
        )

    # Find user by email
    user_stmt = select(User).where(User.email == data.email.lower())
    target_user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered user found with email '{data.email}'. The user must register first.",
        )

    # Check if already a member
    exist_check = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == target_user.id,
    )
    if (await db.execute(exist_check)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{target_user.email}' is already a member of this household.",
        )

    new_membership = HouseholdMember(
        household_id=household_id,
        user_id=target_user.id,
        role=data.role,
    )
    db.add(new_membership)

    # Check if person record already exists with this user_id or matching name
    person_by_user = (await db.execute(
        select(Person).where(
            Person.household_id == household_id,
            Person.user_id == target_user.id,
        )
    )).scalars().first()

    if person_by_user:
        existing_person = person_by_user
    else:
        existing_person = (await db.execute(
            select(Person).where(
                Person.household_id == household_id,
                Person.name == target_user.full_name,
                Person.user_id.is_(None),
            )
        )).scalars().first()

    if not existing_person:
        new_person = Person(
            household_id=household_id,
            user_id=target_user.id,
            name=target_user.full_name,
            is_active=True,
            is_deleted=False,
        )
        db.add(new_person)
    else:
        if existing_person.user_id is None:
            existing_person.user_id = target_user.id
        if existing_person.is_deleted:
            existing_person.is_deleted = False
            existing_person.is_active = True
            existing_person.deleted_at = None

    await db.commit()
    await db.refresh(new_membership)

    return HouseholdMemberOut(
        id=new_membership.id,
        household_id=new_membership.household_id,
        user_id=new_membership.user_id,
        role=new_membership.role,
        full_name=target_user.full_name,
        email=target_user.email,
        created_at=new_membership.created_at,
    )


@router.get("/{household_id}/persons", response_model=List[PersonOut])
async def list_household_persons(
    household_id: uuid.UUID,
    include_deleted: bool = False,
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

    stmt = (
        select(Person)
        .where(Person.household_id == household_id)
        .options(selectinload(Person.user))
    )
    if not include_deleted:
        stmt = stmt.where(Person.is_deleted == False)

    stmt = stmt.order_by(Person.is_deleted.asc(), Person.name.asc())
    persons = (await db.execute(stmt)).scalars().all()

    # Query members to resolve household roles
    mem_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id
    )
    members = (await db.execute(mem_stmt)).scalars().all()
    role_map = {m.user_id: m.role for m in members}

    return [
        PersonOut(
            id=p.id,
            household_id=p.household_id,
            user_id=p.user_id,
            user_email=p.user.email if p.user else None,
            role=role_map.get(p.user_id) if p.user_id else None,
            name=p.name,
            is_active=p.is_active,
            is_deleted=p.is_deleted,
            deleted_at=p.deleted_at,
            created_at=p.created_at,
        )
        for p in persons
    ]


@router.post(
    "/{household_id}/persons",
    response_model=PersonOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_household_person(
    household_id: uuid.UUID,
    data: PersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only household ADMIN can add resident persons
    check_stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.role == "ADMIN",
    )
    caller_mem = (await db.execute(check_stmt)).scalar_one_or_none()
    if not caller_mem:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only household administrators can add residents.",
        )

    target_user: Optional[User] = None
    target_role: Optional[str] = None

    if data.email:
        # Search for registered user by email
        user_stmt = select(User).where(User.email == data.email.lower().strip())
        target_user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No registered user found with email '{data.email}'. You can add this resident without an email, and link their account later once they register.",
            )

        target_role = data.role

        # Check if already a member of household, if not add them
        mem_check = select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == target_user.id,
        )
        existing_mem = (await db.execute(mem_check)).scalar_one_or_none()
        if not existing_mem:
            new_mem = HouseholdMember(
                household_id=household_id,
                user_id=target_user.id,
                role=target_role,
            )
            db.add(new_mem)
        else:
            target_role = existing_mem.role

    person = Person(
        household_id=household_id,
        user_id=target_user.id if target_user else None,
        name=data.name.strip(),
        is_active=True,
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)

    return PersonOut(
        id=person.id,
        household_id=person.household_id,
        user_id=person.user_id,
        user_email=target_user.email if target_user else None,
        role=target_role,
        name=person.name,
        is_active=person.is_active,
        is_deleted=person.is_deleted,
        deleted_at=person.deleted_at,
        created_at=person.created_at,
    )
