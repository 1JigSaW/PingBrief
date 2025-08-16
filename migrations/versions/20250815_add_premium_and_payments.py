"""add premium_until and payments

Revision ID: 20250815_add_premium_and_payments
Revises: 20250814_add_news_item_translations
Create Date: 2025-08-16 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250815_premium_payments'
down_revision: Union[str, Sequence[str], None] = '20250814_add_translations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('premium_until', sa.DateTime(), nullable=True))

    op.create_table(
        'payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('telegram_payment_charge_id', sa.String(length=128), nullable=False),
        sa.Column('provider_payment_charge_id', sa.String(length=128), nullable=True),
        sa.Column('payload', sa.String(length=128), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='XTR'),
        sa.Column('amount_stars', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PAID', 'FAILED', name='paymentstatus'), nullable=False, server_default='PAID'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_telegram_payment_charge_id'), 'payments', ['telegram_payment_charge_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_telegram_payment_charge_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_column('users', 'premium_until')


