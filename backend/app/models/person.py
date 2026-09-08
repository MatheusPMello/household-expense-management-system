import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.user import User
    from app.models.expense import ExpenseSplit
    from app.models.payment import Payment
    from app.models.debt_waiver import DebtWaiver


class Person(Base):
    """
    Managed resident within the household. May optionally link to a registered User.
    """
    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    household: Mapped["Household"] = relationship("Household", back_populates="persons")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="persons")
    expense_splits: Mapped[List["ExpenseSplit"]] = relationship(
        "ExpenseSplit", back_populates="person"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="person"
    )
    debt_waivers: Mapped[List["DebtWaiver"]] = relationship(
        "DebtWaiver", back_populates="person"
    )
