"""Migrate legacy minutes

Revision ID: fb31a5107160
Revises: 5008f0ccc24e
Create Date: 2025-07-14 13:55:23.532567

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb31a5107160"
down_revision: str | None = "5008f0ccc24e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
WITH
	new_minute AS (
		INSERT INTO
			minute (transcription_id, template_name)
		SELECT
			t.id AS transcription_id,
			'Legacy' AS template_name
		FROM
			transcription t
		WHERE
			CASE
				WHEN jsonb_typeof(t.minute_versions) = 'array' THEN CASE
					WHEN jsonb_array_length(t.minute_versions) > 0 THEN TRUE
				END
			END
		RETURNING
			id,
			transcription_id
	)
INSERT INTO
	minute_version (minute_id, html_content, status, created_datetime)
SELECT
	m.id AS minute_id,
	version ->> 'html_content' AS html_content,
	'COMPLETED' AS status,
	t.created_datetime + ord * INTERVAL '1 minute' AS created_datetime
FROM
	new_minute m
	JOIN transcription t ON m.transcription_id = t.id
	CROSS JOIN jsonb_array_elements(t.minute_versions)
WITH
	ORDINALITY AS v (version, ord)
WHERE
	version ->> 'html_content' IS NOT NULL;
""")


def downgrade() -> None:
    op.execute("""
DELETE FROM minute where minute.template_name = 'Legacy';
""")
