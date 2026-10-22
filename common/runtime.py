"""The wired-up external dependencies an entry point runs with.

A frozen :class:`Runtime` carries one implementation of each service, is built once
from ``Settings`` at startup, and is passed down explicitly. It replaces the
scattered module-level singletons (``stt = get_transcription_service()``): a
dependency is injected by whoever builds the Runtime, not reached for from a global.
Tests inject fakes the same way, by building a Runtime with substituted providers.

``storage`` is the S3 client factory (``common.services.storage.s3.client``), not a
client: like ``db`` being a sessionmaker, it is called per unit of work so each activity
opens and closes its own client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_sessionmaker

from common.database.postgres_database import async_engine
from common.services.storage.s3 import client
from common.services.stt import STT, Azure

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager
    from typing import Any

    from common.settings import Settings


@dataclass(frozen=True)
class Runtime:
    storage: Callable[[], AbstractAsyncContextManager[Any]]
    stt: STT
    db: async_sessionmaker


def build_runtime(settings: Settings) -> Runtime:  # noqa: ARG001  # providers read get_settings() themselves for now
    return Runtime(
        storage=client,
        stt=Azure(),
        db=async_sessionmaker(async_engine, expire_on_commit=False),
    )
