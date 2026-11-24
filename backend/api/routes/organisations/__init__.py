from fastapi import APIRouter

from backend.api.routes.organisations.crud import crud_router
from backend.api.routes.organisations.members import members_router

orgs_router = APIRouter()
orgs_router.include_router(crud_router)
orgs_router.include_router(members_router)

__all__ = ["orgs_router"]
