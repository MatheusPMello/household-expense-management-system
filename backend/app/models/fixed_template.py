import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, SmallInteger, Boolean, Uuid, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.household import Household


class FixedExpenseTemplate(Base):
    __tablename__ = "fixed_expense_templates"
    __table_args__ = (
        CheckConstraint("estimated_amount_cents > 0", name="check_fixed_template_amount_positive"),
        CheckConstraint("due_day BETWEEN 1 AND 31", name="check_fixed_template_due_day_valid"),
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
    estimated_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    due_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    household: Mapped["Household"] = relationship(
        "Household", back_populates="fixed_templates"
    )
