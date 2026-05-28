"""dedupe users by case-insensitive email and enforce uniqueness

Revision ID: c4f9d2a1b8e3
Revises: 9d080ca9fe6c
Create Date: 2026-05-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c4f9d2a1b8e3"
down_revision: Union[str, None] = "9d080ca9fe6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reassign all FK references from duplicate (case-variant) users to the
    # oldest user row sharing the same lowercase email, then drop the duplicates.
    # The auth refactor may have switched email providers, and the new provider returns
    # emails in a different case than the old one — that silently created a
    # second User row for each affected person, orphaning their transcriptions.

    # first query - update transcription table
    # 1) canonical selects oldest lower case user email
    # 2) remap query finds user IDs in transcription table where the normalised email case matches, but the ID is
    # different
    # 3) we then

    op.execute(
        """
        WITH canonical AS (
            SELECT DISTINCT ON (LOWER(email))
                id AS keep_id,
                LOWER(email) AS lower_email
            FROM "user"
            ORDER BY LOWER(email), created_datetime ASC, id ASC
        ),
        remap AS (
            SELECT u.id AS old_id, c.keep_id
            FROM "user" u
            JOIN canonical c ON LOWER(u.email) = c.lower_email
            WHERE u.id <> c.keep_id
        )
        UPDATE transcription t
        SET user_id = r.keep_id
        FROM remap r
        WHERE t.user_id = r.old_id;
        """
    )
    op.execute(
        """
        WITH canonical AS (
            SELECT DISTINCT ON (LOWER(email))
                id AS keep_id,
                LOWER(email) AS lower_email
            FROM "user"
            ORDER BY LOWER(email), created_datetime ASC, id ASC
        ),
        remap AS (
            SELECT u.id AS old_id, c.keep_id
            FROM "user" u
            JOIN canonical c ON LOWER(u.email) = c.lower_email
            WHERE u.id <> c.keep_id
        )
        UPDATE recording r
        SET user_id = rm.keep_id
        FROM remap rm
        WHERE r.user_id = rm.old_id;
        """
    )
    op.execute(
        """
        WITH canonical AS (
            SELECT DISTINCT ON (LOWER(email))
                id AS keep_id,
                LOWER(email) AS lower_email
            FROM "user"
            ORDER BY LOWER(email), created_datetime ASC, id ASC
        ),
        remap AS (
            SELECT u.id AS old_id, c.keep_id
            FROM "user" u
            JOIN canonical c ON LOWER(u.email) = c.lower_email
            WHERE u.id <> c.keep_id
        )
        UPDATE user_template ut
        SET user_id = r.keep_id
        FROM remap r
        WHERE ut.user_id = r.old_id;
        """
    )
    op.execute(
        """
        DELETE FROM "user" u
        USING (
            SELECT DISTINCT ON (LOWER(email)) id AS keep_id, LOWER(email) AS lower_email
            FROM "user"
            ORDER BY LOWER(email), created_datetime ASC, id ASC
        ) c
        WHERE LOWER(u.email) = c.lower_email AND u.id <> c.keep_id;
        """
    )

    op.execute('UPDATE "user" SET email = LOWER(email) WHERE email <> LOWER(email);')

    op.execute('CREATE UNIQUE INDEX ix_user_email_lower ON "user" (LOWER(email));')


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_email_lower;")
