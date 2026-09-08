import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.household import HouseholdMember
from app.models.fixed_template import FixedExpenseTemplate
from app.schemas.fixed_template import (
    FixedTemplateCreate,
    FixedTemplateUpdate,
    FixedTemplateOut,
)

router = APIRouter(prefix="/fixed-templates", tags=["Fixed Expense Templates"])


async def check_admin_access(
    household_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == user_id,
        HouseholdMember.role == "ADMIN",
    )
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required for managing fixed expense templates.",
        )


async def check_member_access(
    household_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    stmt = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.user_id == user_id,
    )
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this household.",
        )


@router.get("", response_model=List[FixedTemplateOut])
async def list_fixed_templates(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await check_member_access(household_id, current_user.id, db)
    stmt = (
        select(FixedExpenseTemplate)
        .where(FixedExpenseTemplate.household_id == household_id)
        .order_by(FixedExpenseTemplate.due_day)
    )
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=FixedTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_fixed_template(
    household_id: uuid.UUID = Query(...),
    data: FixedTemplateCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await check_admin_access(household_id, current_user.id, db)
    tpl = FixedExpenseTemplate(
        household_id=household_id,
        title=data.title.strip(),
        recurrence_type=data.recurrence_type,
        estimated_amount_cents=data.estimated_amount_cents,
        due_day=data.due_day,
        category=data.category.strip(),
        is_active=data.is_active,
        split_type=data.split_type,
        split_config=data.split_config,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.put("/{template_id}", response_model=FixedTemplateOut)
async def update_fixed_template(
    template_id: uuid.UUID,
    data: FixedTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FixedExpenseTemplate).where(FixedExpenseTemplate.id == template_id)
    tpl = (await db.execute(stmt)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed expense template not found.",
        )

    await check_admin_access(tpl.household_id, current_user.id, db)

    if data.title is not None:
        tpl.title = data.title.strip()
    if data.recurrence_type is not None:
        tpl.recurrence_type = data.recurrence_type
    if data.estimated_amount_cents is not None:
        tpl.estimated_amount_cents = data.estimated_amount_cents
    if data.due_day is not None:
        tpl.due_day = data.due_day
    if data.category is not None:
        tpl.category = data.category.strip()
    if data.is_active is not None:
        tpl.is_active = data.is_active
    if data.split_type is not None:
        tpl.split_type = data.split_type
    if data.split_config is not None:
        tpl.split_config = data.split_config

    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fixed_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FixedExpenseTemplate).where(FixedExpenseTemplate.id == template_id)
    tpl = (await db.execute(stmt)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed expense template not found.",
        )

    await check_admin_access(tpl.household_id, current_user.id, db)

    await db.delete(tpl)
    await db.commit()
    return None
