"""Temporal activities for processing and daily cleanup.

Grouped by task queue (see common/workflows/transcription.py); each group is one Worker.
The submodules are imported here (not the functions), so `activities.prepare_audio` is the
module.
"""

from common.workflows.activities import (
    cleanup,
    complete_transcription,
    edit_minute,
    fail_minute,
    fail_transcription,
    generate_minute,
    generate_title,
    identify_speakers,
    prepare_audio,
    summarise,
    transcribe,
)

STT_ACTIVITIES = [prepare_audio.prepare_audio, transcribe.transcribe]  # ffmpeg + the STT provider callers

LLM_ACTIVITIES = [  # the only LLM callers
    identify_speakers.identify_speakers,
    generate_title.generate_title,
    summarise.summarise,
    generate_minute.generate_minute,
    edit_minute.edit_minute,
]
WORKFLOW_QUEUE_ACTIVITIES = [
    complete_transcription.complete_transcription,
    fail_transcription.fail_transcription,
    fail_minute.fail_minute_version,
    fail_minute.fail_summarise,
    cleanup.cleanup_old_records,
    cleanup.delete_orphan_records,
    cleanup.cleanup_failed_records,
]
