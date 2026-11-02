"""Namespace search attributes, registered manually via the Temporal CLI before deployment."""

from temporalio.common import SearchAttributeKey

USER_ID = SearchAttributeKey.for_keyword("UserId")
TRANSCRIPTION_ID = SearchAttributeKey.for_keyword("TranscriptionId")
MINUTE_ID = SearchAttributeKey.for_keyword("MinuteId")
MINUTE_VERSION_ID = SearchAttributeKey.for_keyword("MinuteVersionId")
