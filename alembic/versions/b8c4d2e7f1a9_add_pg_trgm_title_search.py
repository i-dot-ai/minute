"""Add pg_trgm extension and trigram index for transcription title search

Revision ID: b8c4d2e7f1a9
Revises: a3f7c1e9b2d4
Create Date: 2026-07-09 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c4d2e7f1a9"
down_revision: str | None = "a3f7c1e9b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_transcription_title_trgm",
        "transcription",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_transcription_title_trgm", table_name="transcription")
    # Extension left in place: other objects may depend on it.
