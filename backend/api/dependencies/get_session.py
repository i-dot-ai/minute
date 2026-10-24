from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine


async def get_session():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


SQLSessionDep = Annotated[AsyncSession, Depends(get_session)]
