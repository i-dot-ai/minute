import logging

from fastapi import APIRouter

users_router = APIRouter(tags=["Users"])

logger = logging.getLogger(__name__)
