from fastapi import APIRouter, Response

health_router = APIRouter(tags=["Healthcheck"])


@health_router.get("/healthcheck")
def healthcheck():
    return Response(status_code=200)
