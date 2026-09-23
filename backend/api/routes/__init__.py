from fastapi import APIRouter

from .chat import chat_router
from .health import health_router
from .minutes import router as minutes_router
from .system_templates import router as system_templates_router
from .transcriptions import transcriptions_router
from .user_templates import router as user_templates_router
from .users import router as users_router

router = APIRouter()

router.include_router(health_router)
router.include_router(transcriptions_router)
router.include_router(users_router)
router.include_router(minutes_router)
router.include_router(system_templates_router)
router.include_router(user_templates_router)

router.include_router(chat_router)
