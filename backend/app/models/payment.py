import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Integer,
    Text,
    DateTime,
    func,
    Uuid,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.mixins import CyclePersonTransactionMixin

if TYPE_CHECKING:
    from app.models.cycle import BillingCycle
    from app.models.person import Person


class Payment(Base, CyclePersonTransactionMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="check_payment_amount_positive"),
        Index("idx_payments_cycle_person", "billing_cycle_id", "person_id"),
    )

    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proof_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    billing_cycle: Mapped["BillingCycle"] = relationship(
        "BillingCycle", back_populates="payments"
    )
    person: Mapped["Person"] = relationship("Person", back_populates="payments")
