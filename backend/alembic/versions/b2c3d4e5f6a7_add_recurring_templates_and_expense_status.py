"""Add recurring templates support and expense status

Revision ID: b2c3d4e5f6a7
Revises: e6418dfaad75
Create Date: 2026-09-08 15:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'e6418dfaad75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('fixed_expense_templates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recurrence_type', sa.String(length=20), server_default='FIXED', nullable=False))
        batch_op.alter_column('estimated_amount_cents', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('split_type', sa.String(length=20), server_default='EQUAL', nullable=False))
        batch_op.add_column(sa.Column('split_config', sa.JSON(), nullable=True))

    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('template_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='READY', nullable=False))
        batch_op.create_foreign_key('fk_expenses_template_id', 'fixed_expense_templates', ['template_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('idx_expenses_template', ['template_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.drop_index('idx_expenses_template')
        batch_op.drop_constraint('fk_expenses_template_id', type_='foreignkey')
        batch_op.drop_column('status')
        batch_op.drop_column('template_id')

    with op.batch_alter_table('fixed_expense_templates', schema=None) as batch_op:
        batch_op.drop_column('split_config')
        batch_op.drop_column('split_type')
        batch_op.alter_column('estimated_amount_cents', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column('recurrence_type')
