"""Namespace search attributes, registered by the temporal-namespace release task (temporal-admin/entrypoint.sh)."""

from temporalio.common import SearchAttributeKey

USER_ID = SearchAttributeKey.for_keyword("UserId")
TRANSCRIPTION_ID = SearchAttributeKey.for_keyword("TranscriptionId")
MINUTE_ID = SearchAttributeKey.for_keyword("MinuteId")
MINUTE_VERSION_ID = SearchAttributeKey.for_keyword("MinuteVersionId")
