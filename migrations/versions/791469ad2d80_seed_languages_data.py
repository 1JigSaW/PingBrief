"""seed languages data

Revision ID: 791469ad2d80
Revises: 20250817_schema_tweaks_indexes
Create Date: 2025-10-22 22:13:52.672210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '791469ad2d80'
down_revision: Union[str, Sequence[str], None] = '20250817_schema_tweaks_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LANGS = [
    ('en', 'English'),
    ('ru', 'Russian'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
    ('zh', 'Chinese'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('it', 'Italian'),
    ('pt', 'Portuguese'),
    ('ar', 'Arabic'),
    ('hi', 'Hindi'),
    ('tr', 'Turkish'),
    ('nl', 'Dutch'),
    ('sv', 'Swedish'),
]


def upgrade() -> None:
    """Insert default languages if missing (idempotent)."""
    conn = op.get_bind()
    now = datetime.utcnow()
    for code, name in LANGS:
        conn.execute(
            sa.text(
                'INSERT INTO languages (code, name, is_active, created_at, updated_at)\n'
                'VALUES (:code, :name, true, :now, :now)\n'
                'ON CONFLICT (code) DO NOTHING'
            ),
            {
                'code': code,
                'name': name,
                'now': now,
            },
        )


def downgrade() -> None:
    """Remove seeded languages (safe to run)."""
    conn = op.get_bind()
    placeholders = ','.join([f"'{c}'" for c, _ in LANGS])
    conn.execute(
        sa.text(
            f"DELETE FROM languages WHERE code IN ({placeholders})"
        )
    )
