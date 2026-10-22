"""Temporal activities for the transcription workflow: one module per activity.

Grouped by task queue (see common/workflows/transcription.py); each group is one Worker.
The submodules are imported here (not the functions), so `activities.prepare_audio` is the
module. The STT group takes a Runtime (build_stt_activities) and is built by the worker, so
those activities use the runtime's providers instead of globals; the other groups are plain
module-level activity functions.
"""

from common.runtime import Runtime
from common.workflows.activities import (
    complete_transcription,
    fail_transcription,
    generate_title,
    identify_speakers,
    prepare_audio,
    summarize,
    transcribe,
)


def build_stt_activities(runtime: Runtime) -> list:
    """STT-queue activities (ffmpeg + the only Azure caller), bound to the runtime's storage/stt/db."""
    return [prepare_audio.build_prepare_audio(runtime), transcribe.build_transcribe(runtime)]


LLM_ACTIVITIES = [  # the only Gemini callers
    identify_speakers.identify_speakers,
    generate_title.generate_title,
    summarize.summarize,
]
WORKFLOW_QUEUE_ACTIVITIES = [complete_transcription.complete_transcription, fail_transcription.fail_transcription]
