import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    SmallInteger,
    DateTime,
    func,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.expense import Expense
    from app.models.payment import Payment
    from app.models.debt_waiver import DebtWaiver

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"


class BillingCycle(Base):
    __tablename__ = "billing_cycles"
    __table_args__ = (
        UniqueConstraint("household_id", "year", "month", name="uq_cycle_household_year_month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="check_cycle_month_valid"),
        CheckConstraint("status IN ('OPEN', 'CLOSED')", name="check_cycle_status_valid"),
        Index("idx_cycles_household", "household_id", "year", "month"),
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
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    household: Mapped["Household"] = relationship(
        "Household", back_populates="billing_cycles"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="billing_cycle", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="billing_cycle", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
    debt_waivers: Mapped[List["DebtWaiver"]] = relationship(
        "DebtWaiver", back_populates="billing_cycle", cascade=CASCADE_ALL_DELETE_ORPHAN
    )
