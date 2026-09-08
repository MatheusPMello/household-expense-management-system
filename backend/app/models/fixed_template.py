import uuid
from typing import TYPE_CHECKING, Optional, Any, Dict, List
from sqlalchemy import String, Integer, SmallInteger, Boolean, Uuid, ForeignKey, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.expense import Expense


class FixedExpenseTemplate(Base):
    __tablename__ = "fixed_expense_templates"
    __table_args__ = (
        CheckConstraint("due_day BETWEEN 1 AND 31", name="check_fixed_template_due_day_valid"),
        CheckConstraint("recurrence_type IN ('FIXED', 'VARIABLE')", name="check_fixed_template_recurrence_type_valid"),
        CheckConstraint(
            "(recurrence_type = 'FIXED' AND estimated_amount_cents IS NOT NULL AND estimated_amount_cents > 0) OR (recurrence_type = 'VARIABLE' AND (estimated_amount_cents IS NULL OR estimated_amount_cents >= 0))",
            name="check_fixed_template_amount_valid",
        ),
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
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    recurrence_type: Mapped[str] = mapped_column(String(20), default="FIXED", nullable=False)
    estimated_amount_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    due_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    split_type: Mapped[str] = mapped_column(String(20), default="EQUAL", nullable=False)
    split_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    household: Mapped["Household"] = relationship(
        "Household", back_populates="fixed_templates"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="template"
    )


# Alias for domain clarity
RecurringExpenseTemplate = FixedExpenseTemplate
