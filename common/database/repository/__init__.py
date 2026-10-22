"""Database statements used outside the backend routes.

Ported from chore/idempotency-refactor (same style: async functions that take the caller's
AsyncSession and never commit; the caller owns the transaction). Trivial one-off CRUD stays
local to its route.

Not ported: B's claims.py (claim CAS on a `claimed_at` lease column, which needs a schema
change). The existing fencing-token claims stay in common/services/job_claim.py until the
Ray AI-edit path moves to Temporal.
"""

from common.database.repository.minute_versions import (
    get_only_version_for_minute,
    get_version_with_transcription,
    mark_version_completed,
    mark_version_failed,
    reset_version_for_retry,
)
from common.database.repository.recordings import add_recording, find_orphan_recordings
from common.database.repository.templates import get_user_template_with_questions
from common.database.repository.transcriptions import (
    finalize_stale_in_progress,
    find_expired_transcriptions,
    get_transcription,
    get_transcription_for_minute,
    get_transcription_with_recordings,
    mark_transcription_completed,
    mark_transcription_failed,
    reset_transcription_for_retry,
    update_in_progress_transcription,
)

__all__ = [
    "add_recording",
    "finalize_stale_in_progress",
    "find_expired_transcriptions",
    "find_orphan_recordings",
    "get_only_version_for_minute",
    "get_transcription",
    "get_transcription_for_minute",
    "get_transcription_with_recordings",
    "get_user_template_with_questions",
    "get_version_with_transcription",
    "mark_transcription_completed",
    "mark_transcription_failed",
    "mark_version_completed",
    "mark_version_failed",
    "reset_transcription_for_retry",
    "reset_version_for_retry",
    "update_in_progress_transcription",
]
