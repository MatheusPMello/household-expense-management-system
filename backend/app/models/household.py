import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, func, Uuid, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.person import Person
    from app.models.fixed_template import FixedExpenseTemplate
    from app.models.cycle import BillingCycle


CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[List["HouseholdMember"]] = relationship(
        "HouseholdMember", back_populates="household", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
    persons: Mapped[List["Person"]] = relationship(
        "Person", back_populates="household", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
    fixed_templates: Mapped[List["FixedExpenseTemplate"]] = relationship(
        "FixedExpenseTemplate", back_populates="household", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
    billing_cycles: Mapped[List["BillingCycle"]] = relationship(
        "BillingCycle", back_populates="household", cascade=CASCADE_ALL_DELETE_ORPHAN
    )


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (
        UniqueConstraint("household_id", "user_id", name="uq_household_user"),
        CheckConstraint("role IN ('ADMIN', 'MEMBER')", name="check_household_member_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), default="MEMBER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    household: Mapped["Household"] = relationship("Household", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="household_memberships")
