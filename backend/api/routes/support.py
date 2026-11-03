import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, StringConstraints

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
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CreateSupportTicketResponse(BaseModel):
    reference: str


def _title(message: str) -> str:
    summary = " ".join(message.split())
    if len(summary) <= TITLE_SUMMARY_LENGTH:
        return summary
    return summary[:TITLE_SUMMARY_LENGTH].rstrip() + "…"


@support_router.post("/support/tickets")
async def create_support_ticket(
    data: CreateSupportTicketRequest, user: UserDep, request: Request
) -> CreateSupportTicketResponse:
    description = (
        f"Category: {data.category.capitalize()}\n"
        f"User id: {user.id}\n"
        f"Email: {user.email}\n"
        f"Sent: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC\n"
        f"Browser: {request.headers.get('user-agent', 'unknown')}\n\n"
        f"---\n{data.message}"
    )
    label_id = getattr(get_settings(), f"LINEAR_LABEL_ID_{data.category.upper()}")

    try:
        reference = await create_linear_issue(_title(data.message), description, [label_id] if label_id else None)
    except LinearNotConfiguredError as e:
        raise HTTPException(status_code=503, detail="Support tickets are not configured") from e
    except Exception as e:
        logger.exception("Failed to create Linear support ticket")
        raise HTTPException(status_code=502, detail="Failed to create support ticket") from e

    return CreateSupportTicketResponse(reference=reference)
