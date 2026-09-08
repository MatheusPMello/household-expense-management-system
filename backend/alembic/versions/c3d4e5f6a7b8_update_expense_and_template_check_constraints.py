"""Update expense and template check constraints
Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-08 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('fixed_expense_templates', schema=None) as batch_op:
        batch_op.drop_constraint('check_fixed_template_amount_positive', type_='check')
        batch_op.create_check_constraint('check_fixed_template_recurrence_type_valid', "recurrence_type IN ('FIXED', 'VARIABLE')")
        batch_op.create_check_constraint(
            'check_fixed_template_amount_valid',
            "(recurrence_type = 'FIXED' AND estimated_amount_cents IS NOT NULL AND estimated_amount_cents > 0) OR (recurrence_type = 'VARIABLE' AND (estimated_amount_cents IS NULL OR estimated_amount_cents >= 0))",
        )

    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.drop_constraint('check_expense_amount_positive', type_='check')
        batch_op.create_check_constraint('check_expense_amount_non_negative', 'total_amount_cents >= 0')
        batch_op.create_check_constraint('check_expense_amount_positive_or_pending', "total_amount_cents > 0 OR status = 'PENDING_VALUE'")
        batch_op.create_check_constraint('check_expense_status_valid', "status IN ('PENDING_VALUE', 'READY', 'SETTLED')")


def downgrade() -> None:
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.drop_constraint('check_expense_status_valid', type_='check')
        batch_op.drop_constraint('check_expense_amount_positive_or_pending', type_='check')
        batch_op.drop_constraint('check_expense_amount_non_negative', type_='check')
        batch_op.create_check_constraint('check_expense_amount_positive', 'total_amount_cents > 0')

    with op.batch_alter_table('fixed_expense_templates', schema=None) as batch_op:
        batch_op.drop_constraint('check_fixed_template_amount_valid', type_='check')
        batch_op.drop_constraint('check_fixed_template_recurrence_type_valid', type_='check')
        batch_op.create_check_constraint('check_fixed_template_amount_positive', 'estimated_amount_cents > 0')
