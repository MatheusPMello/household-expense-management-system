from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.models.user import User
from app.models.household import Household, HouseholdMember
from app.models.person import Person
from app.models.refresh_token import RefreshToken
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenPair,
    TokenRefreshRequest,
    UserOut,
    HouseholdMembershipInfo,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    # Check if email exists
    stmt = select(User).where(User.email == data.email.lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Create user
    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )
    db.add(user)
    await db.flush()

    # Automatically initialize a default household for the user
    household = Household(name=f"{user.full_name}'s Home")
    db.add(household)
    await db.flush()

    # Add as ADMIN member
    membership = HouseholdMember(
        household_id=household.id,
        user_id=user.id,
        role="ADMIN",
    )
    db.add(membership)

    # Add as initial resident person
    person = Person(
        household_id=household.id,
        user_id=user.id,
        name=user.full_name,
        is_active=True,
    )
    db.add(person)

    await db.commit()
    await db.refresh(user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        households=[
            HouseholdMembershipInfo(
                household_id=household.id,
                household_name=household.name,
                role="ADMIN",
            )
        ],
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit("20/minute")
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == data.email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))
    raw_refresh, token_hash, expires_at = create_refresh_token()

    # Save refresh token in DB
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=request.headers.get("user-agent", "unknown")[:250],
    )
    db.add(db_token)
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: Request,
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    raw_token = data.refresh_token
    token_hash = hash_token(raw_token)

    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
    )
    token_record = (await db.execute(stmt)).scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has been revoked. Please log in again.",
        )

    now = datetime.now(timezone.utc)
    exp_at = token_record.expires_at
    if exp_at.tzinfo is None:
        exp_at = exp_at.replace(tzinfo=timezone.utc)

    if exp_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired. Please log in again.",
        )

    # Invalidate current token (Token Rotation)
    token_record.revoked = True

    # Generate new pair
    user_id = token_record.user_id
    new_access_token = create_access_token(subject=str(user_id))
    new_raw_refresh, new_token_hash, new_expires_at = create_refresh_token()

    new_db_token = RefreshToken(
        user_id=user_id,
        token_hash=new_token_hash,
        expires_at=new_expires_at,
        device_info=data.device_info or request.headers.get("user-agent", "unknown")[:250],
    )
    db.add(new_db_token)
    await db.commit()

    return TokenPair(
        access_token=new_access_token,
        refresh_token=new_raw_refresh,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_hash = hash_token(data.refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.user_id == current_user.id,
    )
    token_record = (await db.execute(stmt)).scalar_one_or_none()
    if token_record:
        token_record.revoked = True
        await db.commit()

    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(HouseholdMember)
        .where(HouseholdMember.user_id == current_user.id)
        .options(selectinload(HouseholdMember.household))
    )
    memberships = (await db.execute(stmt)).scalars().all()

    households_info = [
        HouseholdMembershipInfo(
            household_id=m.household_id,
            household_name=m.household.name,
            role=m.role,
        )
        for m in memberships
    ]

    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        households=households_info,
    )
