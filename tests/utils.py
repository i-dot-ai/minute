from contextlib import asynccontextmanager
from enum import StrEnum, auto

from bs4 import BeautifulSoup
from httpx import ASGITransport, AsyncClient

from backend.main import app


@asynccontextmanager
async def get_test_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class FileTypeTests(StrEnum):
    NORMAL = auto()
    ZERO_BYTES = auto()
    CORRUPTED = auto()


def get_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, features="html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text()
