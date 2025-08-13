"""add TechCrunch source

Revision ID: add_techcrunch_source_20250812
Revises: 65d4d955c335_add_content_field_to_news_items
Create Date: 2025-08-12
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_techcrunch_source_20250812'
down_revision = '65d4d955c335'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Check if already exists by name or URL
    exists = bind.execute(
        sa.text(
            "SELECT 1 FROM sources WHERE name = :name OR url = :url LIMIT 1"
        ),
        {
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
        },
    ).fetchone()
    if exists:
        return

    source_id = str(uuid.uuid4())
    bind.execute(
        sa.text(
            """
            INSERT INTO sources (id, name, url, default_language, is_active, created_at, updated_at)
            VALUES (:id, :name, :url, :lang, TRUE, NOW(), NOW())
            """
        ),
        {
            "id": source_id,
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
            "lang": "en",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM sources WHERE name = :name OR url = :url"
        ),
        {
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
        },
    )

