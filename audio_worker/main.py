import asyncio

from audio_worker.worker_service import AudioWorkerService
from common.sentry import init_sentry

if __name__ == "__main__":
    init_sentry()
    audio_worker_service = AudioWorkerService()
    asyncio.run(audio_worker_service.run())
