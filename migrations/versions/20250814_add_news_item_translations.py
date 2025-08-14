"""add news_item_translations table

Revision ID: 20250814_add_translations
Revises: add_techcrunch_source_20250812
Create Date: 2025-08-14
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250814_add_translations'
down_revision: Union[str, Sequence[str], None] = 'add_techcrunch_source_20250812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'news_item_translations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('news_item_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('news_items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('language', sa.String(length=8), sa.ForeignKey('languages.code'), nullable=False, index=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('summary_translated', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        constraint_name='uq_news_item_translations_item_lang',
        table_name='news_item_translations',
        columns=['news_item_id', 'language'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_news_item_translations_item_lang',
        'news_item_translations',
        type_='unique',
    )
    op.drop_table('news_item_translations')


