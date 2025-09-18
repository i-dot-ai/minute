import asyncio

from worker.worker_service import create_worker_service

if __name__ == "__main__":
    worker_service = create_worker_service()
    asyncio.run(worker_service.run())
