"""add news_items table

Revision ID: d79ca4303dfb
Revises: 48112c0b27e2
Create Date: 2025-07-30 23:59:45.366201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd79ca4303dfb'
down_revision: Union[str, Sequence[str], None] = '48112c0b27e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
