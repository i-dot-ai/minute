"""Status transitions and invariant-bearing database statements.

Every status transition and claim lives here so the claim CAS, lease semantics and
enum binding (native pg enum labels are the UPPERCASE member names) exist exactly
once. Functions never commit: the caller owns the transaction. Trivial one-off
CRUD stays local to its route/action - do not move it here.

Claim model (two-level, deliberate): a job is a MinuteVersion whose pipeline has two
independently-failable long phases. The transcription phase is guarded by a claim on
the transcription row, the compose/edit phase by a claim on the version row. This
gives phase-level crash resumption, keeps the "who is transcribing" fact authoritative
on the transcription row (multiple versions can exist per transcription, and user
retry resets both rows), and lets the stale sweep judge each row's liveness via its
own claimed_at. The heartbeat renews whichever leases are live (refresh_job_leases),
so while a worker is alive its claims cannot be stolen by duplicate messages.
"""

from common.database.repository.minute_versions import (
    claim_version_for_processing,
    finalize_stale_versions,
    get_version_with_transcription,
    mark_version_completed,
    mark_version_failed,
    reset_version_for_retry,
)
from common.database.repository.shared import ClaimState, refresh_job_leases
from common.database.repository.transcriptions import (
    claim_transcription_for_processing,
    finalize_stale_transcriptions,
    get_transcription_with_recordings,
    mark_transcription_completed,
    mark_transcription_failed,
    reset_transcription_for_retry,
)

__all__ = [
    "ClaimState",
    "claim_transcription_for_processing",
    "claim_version_for_processing",
    "finalize_stale_transcriptions",
    "finalize_stale_versions",
    "get_transcription_with_recordings",
    "get_version_with_transcription",
    "mark_transcription_completed",
    "mark_transcription_failed",
    "mark_version_completed",
    "mark_version_failed",
    "refresh_job_leases",
    "reset_transcription_for_retry",
    "reset_version_for_retry",
]
