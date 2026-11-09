"""Adds a structured error code to transcription records.

Revision ID: c7e2a9f4d1b6
Revises: b8c4d2e7f1a9
Create Date: 09-11-2026 9:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e2a9f4d1b6"
down_revision: str | None = "b8c4d2e7f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adds the error code column and classifies legacy empty-transcript errors."""
    op.add_column("transcription", sa.Column("error_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # Preserve the existing no-audio message for legacy empty-transcript failures.
    op.execute(
        "UPDATE transcription SET error_code = 'no_speech_detected' "
        "WHERE status = 'FAILED' AND error LIKE '%No transcription phrases found%'"
    )


def downgrade() -> None:
    """Removes the transcription error code column."""
    op.drop_column("transcription", "error_code")
