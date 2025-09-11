from contextlib import asynccontextmanager
from enum import StrEnum, auto

from bs4 import BeautifulSoup
from httpx import ASGITransport, AsyncClient

from backend.app.llm.client import ChatBot, create_default_chatbot
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


def create_test_chatbot(messages: list[dict[str, str]]) -> ChatBot:
    chatbot = create_default_chatbot()
    chatbot.messages = messages
    return chatbot
