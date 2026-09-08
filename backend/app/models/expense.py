import uuid
from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Date,
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
    from app.models.cycle import BillingCycle
    from app.models.person import Person
    from app.models.fixed_template import FixedExpenseTemplate


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("total_amount_cents >= 0", name="check_expense_amount_non_negative"),
        CheckConstraint(
            "total_amount_cents > 0 OR status = 'PENDING_VALUE'",
            name="check_expense_amount_positive_or_pending",
        ),
        CheckConstraint(
            "split_type IN ('EQUAL', 'PERCENTAGE', 'EXACT', 'WEIGHTED')",
            name="check_expense_split_type_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING_VALUE', 'READY', 'SETTLED')",
            name="check_expense_status_valid",
        ),
        Index("idx_expenses_cycle", "billing_cycle_id"),
        Index("idx_expenses_template", "template_id"),
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
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fixed_expense_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    split_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="READY", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    billing_cycle: Mapped["BillingCycle"] = relationship(
        "BillingCycle", back_populates="expenses"
    )
    template: Mapped[Optional["FixedExpenseTemplate"]] = relationship(
        "FixedExpenseTemplate", back_populates="expenses"
    )
    splits: Mapped[List["ExpenseSplit"]] = relationship(
        "ExpenseSplit", back_populates="expense", cascade="all, delete-orphan"
    )


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "person_id", name="uq_split_expense_person"),
        CheckConstraint("assigned_amount_cents >= 0", name="check_split_assigned_non_negative"),
        Index("idx_splits_person", "person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    expense_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    expense: Mapped["Expense"] = relationship("Expense", back_populates="splits")
    person: Mapped["Person"] = relationship("Person", back_populates="expense_splits")
