from fastapi import APIRouter

from .crud import crud_router
from .members import members_router

orgs_router = APIRouter()
orgs_router.include_router(crud_router)
orgs_router.include_router(members_router)
