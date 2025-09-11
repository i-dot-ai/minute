from fastapi import APIRouter

from .chat import chat_router
from .health import health_router
from .minutes import minutes_router
from .templates import templates_router
from .transcriptions import transcriptions_router
from .users import users_router

router = APIRouter()

router.include_router(health_router)
router.include_router(transcriptions_router)
router.include_router(users_router)
router.include_router(minutes_router)
router.include_router(templates_router)

router.include_router(chat_router)
