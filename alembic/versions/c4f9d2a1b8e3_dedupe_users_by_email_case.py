"""dedupe users by case-insensitive email and enforce uniqueness

Revision ID: c4f9d2a1b8e3
Revises: 9d080ca9fe6c
Create Date: 2026-05-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4f9d2a1b8e3"
down_revision: Union[str, None] = "9d080ca9fe6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables with a user_id FK that we need to re-point at the canonical user.
TABLES_WITH_USER_FK = ("transcription", "recording", "user_template")


def upgrade() -> None:
    # Reassign all FK references from duplicate (case-variant) users to the
    # oldest user row sharing the same lowercase email, then drop the duplicates.
    # The auth refactor may have switched email providers, and the new provider returns
    # emails in a different case than the old one — that silently created a
    # second User row for each affected person, orphaning their transcriptions.

    # Build a remap (old_id -> keep_id) once, in a temp table, then reuse it
    # for every FK update below. The ON COMMIT DROP removes the temp table at the end of the migration
    # 1) canonical picks the oldest row for each lowercase email as the "keeper"
    # 2) user_remap lists every non-keeper user paired with its keeper

    op.execute(
        """
        CREATE TEMP TABLE user_remap ON COMMIT DROP AS
        WITH canonical AS (
            SELECT DISTINCT ON (LOWER(email))
                id AS keep_id,
                LOWER(email) AS lower_email
            FROM "user"
            ORDER BY LOWER(email), created_datetime ASC, id ASC
        )
        SELECT u.id AS old_id, c.keep_id
        FROM "user" u
        JOIN canonical c ON LOWER(u.email) = c.lower_email
        WHERE u.id <> c.keep_id;
        """
    )

    for table in TABLES_WITH_USER_FK:
        op.execute(
            f"""
            UPDATE {table}
            SET user_id = user_remap.keep_id
            FROM user_remap
            WHERE {table}.user_id = user_remap.old_id;
            """
        )

    op.execute('DELETE FROM "user" WHERE id IN (SELECT old_id FROM user_remap);')

    op.execute('UPDATE "user" SET email = LOWER(email) WHERE email <> LOWER(email);')

    # Matches the Index declared on User.__table_args__ in common/database/postgres_models.py
    op.create_index("ix_user_email_lower", "user", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_email_lower", table_name="user")
