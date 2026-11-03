import logging
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.dependencies import UserDep
from common.services.linear_client import LinearNotConfiguredError, create_linear_issue
from common.settings import get_settings

support_router = APIRouter(tags=["Support"])

logger = logging.getLogger(__name__)

TITLE_SUMMARY_LENGTH = 80


class SupportCategory(StrEnum):
    ACCESS = "access"
    ISSUE = "issue"
    RECOMMENDATION = "recommendation"
    GENERAL = "general"


class CreateSupportTicketRequest(BaseModel):
    category: SupportCategory
    message: str = Field(min_length=1, max_length=5000)


class CreateSupportTicketResponse(BaseModel):
    reference: str


@support_router.post("/support/tickets")
async def create_support_ticket(
    data: CreateSupportTicketRequest, user: UserDep, request: Request
) -> CreateSupportTicketResponse:
    summary = " ".join(data.message.split())
    if len(summary) > TITLE_SUMMARY_LENGTH:
        summary = summary[:TITLE_SUMMARY_LENGTH].rstrip() + "…"
    description = (
        f"Category: {data.category.capitalize()}\n"
        f"User id: {user.id}\n"
        f"Email: {user.email}\n"
        f"Sent: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC\n"
        f"Browser: {request.headers.get('user-agent', 'unknown')}"
        f"\n\n---\n{data.message}"
    )
    label_id = getattr(get_settings(), f"LINEAR_LABEL_ID_{data.category.upper()}")
    try:
        reference = await create_linear_issue(summary, description, [label_id] if label_id else None)
    except LinearNotConfiguredError as e:
        raise HTTPException(status_code=503, detail="Support tickets are not configured") from e
    except Exception as e:
        logger.exception("Failed to create Linear support ticket")
        raise HTTPException(status_code=502, detail="Failed to create support ticket") from e
    return CreateSupportTicketResponse(reference=reference)
