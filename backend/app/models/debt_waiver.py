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

if TYPE_CHECKING:
    from app.models.cycle import BillingCycle
    from app.models.person import Person


class DebtWaiver(Base):
    __tablename__ = "debt_waivers"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="check_debt_waiver_amount_positive"),
        Index("idx_waivers_cycle_person", "billing_cycle_id", "person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    billing_cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("billing_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    waived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    billing_cycle: Mapped["BillingCycle"] = relationship(
        "BillingCycle", back_populates="debt_waivers"
    )
    person: Mapped["Person"] = relationship("Person", back_populates="debt_waivers")
