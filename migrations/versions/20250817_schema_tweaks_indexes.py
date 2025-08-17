"""schema tweaks: indexes and fields

Revision ID: 20250817_schema_tweaks_indexes
Revises: 20250815_premium_payments
Create Date: 2025-08-17 20:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20250817_schema_tweaks_indexes'
down_revision: Union[str, Sequence[str], None] = '20250815_premium_payments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('preferred_language', sa.String(length=8), nullable=True))
    op.create_foreign_key(None, 'users', 'languages', ['preferred_language'], ['code'])
    op.add_column('users', sa.Column('timezone', sa.String(length=64), nullable=True))

    op.add_column('payments', sa.Column('price_stars', sa.Integer(), nullable=True))
    op.add_column('payments', sa.Column('term_days', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_payments_user_id'), 'payments', ['user_id'], unique=False)

    op.add_column('digests', sa.Column('telegram_message_id', sa.Integer(), nullable=True))
    op.create_index('ix_digests_status_scheduled_for', 'digests', ['status', 'scheduled_for'], unique=False)

    op.create_unique_constraint('uq_subscription_user_source', 'subscriptions', ['user_id', 'source_id'])
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=False)

    op.create_unique_constraint('uq_news_item_source_external', 'news_items', ['source_id', 'external_id'])
    op.create_index('ix_news_items_source_fetched', 'news_items', ['source_id', 'fetched_at'], unique=False)

    op.create_unique_constraint('uq_news_item_translation', 'news_item_translations', ['news_item_id', 'language', 'provider'])


def downgrade() -> None:
    op.drop_constraint('uq_news_item_translation', 'news_item_translations', type_='unique')

    op.drop_index('ix_news_items_source_fetched', table_name='news_items')
    op.drop_constraint('uq_news_item_source_external', 'news_items', type_='unique')

    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.drop_constraint('uq_subscription_user_source', 'subscriptions', type_='unique')

    op.drop_index('ix_digests_status_scheduled_for', table_name='digests')
    op.drop_column('digests', 'telegram_message_id')

    op.drop_index(op.f('ix_payments_user_id'), table_name='payments')
    op.drop_column('payments', 'term_days')
    op.drop_column('payments', 'price_stars')

    op.drop_column('users', 'timezone')
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'preferred_language')


