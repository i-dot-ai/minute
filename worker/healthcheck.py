import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

HEARTBEAT_DIR = "/tmp/worker_heartbeats"  # noqa: S108
HEARTBEAT_TIMEOUT = 1200  # 20 minutes
Path(HEARTBEAT_DIR).mkdir(exist_ok=True)


@app.get("/healthcheck")
async def healthcheck():
    current_time = time.time()
    heartbeat_files = list(Path(HEARTBEAT_DIR).glob("worker_*.heartbeat"))
    if not heartbeat_files:
        return JSONResponse(content={"status": "unhealthy", "reason": "no workers found"}, status_code=503)

    stale_workers = []
    for hb_file in heartbeat_files:
        last_heartbeat = hb_file.stat().st_mtime
        age = current_time - last_heartbeat

        if age > HEARTBEAT_TIMEOUT:
            stale_workers.append(hb_file.stem)

    if stale_workers:
        return JSONResponse(
            content={"status": "unhealthy", "reason": f"stale workers: {stale_workers}"}, status_code=503
        )

    return JSONResponse(content={"status": "healthy", "workers": len(heartbeat_files)}, status_code=200)
