from contextlib import asynccontextmanager
from enum import StrEnum, auto

from bs4 import BeautifulSoup
from httpx import ASGITransport, AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.main import app
from common.database.postgres_models import User


@asynccontextmanager
async def get_test_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def get_or_create_user(session: AsyncSession, email: str) -> User:
    """Fetch the user for `email`, creating it if absent — idempotent across runs."""
    user = (await session.exec(select(User).where(User.email == email))).first()
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


class FileTypeTests(StrEnum):
    NORMAL = auto()
    ZERO_BYTES = auto()
    CORRUPTED = auto()


def get_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, features="html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text()
