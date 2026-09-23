"""add_recording_status

Revision ID: 1fd52d2160ff
Revises: b8c4d2e7f1a9
Create Date: 2026-09-21 15:11:42.925370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1fd52d2160ff'
down_revision: Union[str, None] = 'b8c4d2e7f1a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recording_status_enum = sa.Enum('UPLOADED', 'READY_FOR_TRANSCRIPTION', 'FAILED_PROCESSING', name='recordingstatus')
    recording_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.add_column('recording', sa.Column('status', recording_status_enum, nullable=False, server_default='UPLOADED'))


def downgrade() -> None:
    op.drop_column('recording', 'status')
    
    recording_status_enum = sa.Enum('UPLOADED', 'READY_FOR_TRANSCRIPTION', 'FAILED_PROCESSING', name='recordingstatus')
    recording_status_enum.drop(op.get_bind(), checkfirst=True)
