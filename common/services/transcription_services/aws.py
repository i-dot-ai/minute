import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

import boto3

from common.database.postgres_models import DialogueEntry, Recording
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

settings = get_settings()
logger = logging.getLogger(__name__)


class AWSTranscribeAdapter(TranscriptionAdapter):
    """Adapter for AWS Transcribe service. Note, no tenacity is configured as boto3 does this automagically"""

    max_audio_length = 14400
    name = "aws_transcribe"
    adapter_type = AdapterType.ASYNC

    @classmethod
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """
        Async version of transcribe audio using Azure Speech-to-Text API
        """
        transcribe = boto3.client("transcribe", region_name=settings.AWS_REGION)
        file_name = uuid.uuid4()
        job_name = f"minute-{settings.ENVIRONMENT}-transcription-job-{file_name}"
        s3_uri = f"s3://{settings.DATA_S3_BUCKET}/{audio_file_path_or_recording.s3_file_key}"
        # Start transcription job
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_uri},
            OutputBucketName=settings.DATA_S3_BUCKET,
            OutputKey=f"app_data/transcribe-output/{file_name}/",
            LanguageCode="en-GB",
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 30},
        )

        return TranscriptionJobMessageData(transcription_service=cls.name, job_name=job_name)

    @classmethod
    async def check(
        cls, data: TranscriptionJobMessageData, retry_count: int = 5, retry_delay: int = 5
    ) -> TranscriptionJobMessageData:
        # Poll for completion
        for _ in range(retry_count):
            s3 = boto3.client("s3", region_name=settings.AWS_REGION)
            transcribe = boto3.client("transcribe", region_name=settings.AWS_REGION)
            status = transcribe.get_transcription_job(TranscriptionJobName=data.job_name)
            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

            if job_status == "COMPLETED":
                transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                transcript_key = transcript_uri.split(f"{settings.DATA_S3_BUCKET}/")[1]

                # Get the transcript JSON from S3
                response = s3.get_object(Bucket=settings.DATA_S3_BUCKET, Key=transcript_key)
                transcript_content = json.loads(response["Body"].read().decode("utf-8"))

                # Extract and group audio segments
                audio_segments = transcript_content.get("results", {}).get("audio_segments", [])

                try:
                    s3.delete_object(Bucket=settings.DATA_S3_BUCKET, Key=transcript_key)
                except Exception as cleanup_error:  # noqa: BLE001
                    logger.warning("Failed to delete transcript: %s", cleanup_error)

                dialogue_entries = cls.convert_to_dialogue_entries(audio_segments)
                return data.model_copy(update={"transcript": dialogue_entries})

            elif job_status == "FAILED":
                failure_reason = status["TranscriptionJob"].get("FailureReason", "Unknown error")
                msg = f"Transcription job failed: {failure_reason}"
                raise ValueError(msg)
            else:
                await asyncio.sleep(retry_delay)

        return data

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.AWS_ACCOUNT_ID and settings.AWS_REGION)

    @classmethod
    def convert_to_dialogue_entries(cls, phrases: Any) -> list[DialogueEntry]:
        return [
            DialogueEntry(
                speaker=segment["speaker_label"],
                text=segment["transcript"],
                start_time=float(segment["start_time"]),
                end_time=float(segment["end_time"]),
            )
            for segment in phrases
        ]
