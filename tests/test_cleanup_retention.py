"""Check DBT retention before cleanup, rolling back all database changes afterwards."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession
from temporalio.testing import ActivityEnvironment

from common.database.postgres_database import async_engine
from common.database.postgres_models import Transcription, User
from common.workflows.activities import cleanup


@pytest.mark.asyncio(loop_scope="session")
async def test_cleanup_fixes_inactive_dbt_users_and_preserves_other_domains(monkeypatch):
    cases = [
        ("businessandtrade.gov.uk", None, 30, [29]),
        ("BUSINESSANDTRADE.GOV.UK", 90, 30, [29]),
        ("businessandtrade.gov.uk", 7, 30, [29]),
        ("dsit.gov.uk", None, None, [29, 31]),
        ("sub.businessandtrade.gov.uk", 90, 90, [29, 31]),
        ("businessandtrade.gov.uk.example.com", None, None, [29, 31]),
    ]
    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        # Activity commits release savepoints; the outer rollback keeps existing data safe.
        monkeypatch.setattr(
            cleanup, "AsyncSession", lambda _: AsyncSession(connection, join_transaction_mode="create_savepoint")
        )
        try:
            users = []
            expected_transcriptions = set()
            now = datetime.now(UTC)
            async with AsyncSession(connection, expire_on_commit=False) as session:
                for domain, days, _, remaining_ages in cases:
                    user = User(email=f"cleanup-retention-{uuid4().hex}@{domain}", data_retention_days=days)
                    session.add(user)
                    users.append(user)
                    await session.flush()
                    await session.exec(update(User).where(User.id == user.id).values(data_retention_days=days))
                    for age in (29, 31):
                        transcription = Transcription(user_id=user.id, created_datetime=now - timedelta(days=age))
                        session.add(transcription)
                        if age in remaining_ages:
                            expected_transcriptions.add(transcription.id)
                await session.flush()

            for _ in range(2):
                await ActivityEnvironment().run(cleanup.cleanup_old_records)
                async with AsyncSession(connection) as session:
                    for user, (_, _, expected_days, _) in zip(users, cases, strict=True):
                        stored = await session.get(User, user.id)
                        assert stored.data_retention_days == expected_days
                    remaining = await session.exec(
                        select(Transcription.id).where(col(Transcription.user_id).in_([user.id for user in users]))
                    )
                    assert set(remaining.all()) == expected_transcriptions
        finally:
            await transaction.rollback()
