import uuid
from datetime import datetime
from typing import TYPE_CHECKING
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


class DebtWaiver(Base, CyclePersonTransactionMixin):
    __tablename__ = "debt_waivers"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="check_debt_waiver_amount_positive"),
        Index("idx_waivers_cycle_person", "billing_cycle_id", "person_id"),
    )

    waived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    billing_cycle: Mapped["BillingCycle"] = relationship(
        "BillingCycle", back_populates="debt_waivers"
    )
    person: Mapped["Person"] = relationship("Person", back_populates="debt_waivers")
