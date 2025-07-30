"""add news_items table

Revision ID: 48112c0b27e2
Revises: dbe18c4fbc2e
Create Date: 2025-07-30 23:56:53.865296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48112c0b27e2'
down_revision: Union[str, Sequence[str], None] = 'dbe18c4fbc2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
