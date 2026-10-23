"""Integration test for migration 2f6c1b8a9d04 (30-day retention for
businessandtrade.gov.uk users).

Spins up a throwaway Postgres database, runs alembic up to the parent revision,
seeds users inside and outside the target domain, applies the migration, and
asserts only the target-domain users are changed.

Requires a running Postgres instance reachable via the POSTGRES_* settings
(e.g. `docker-compose up db`). The connecting user needs CREATEDB.
"""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

import common.database.postgres_database as pgdb
from alembic import command
from alembic.config import Config
from common.settings import get_settings

PRE_REVISION = "b8c4d2e7f1a9"
TARGET_REVISION = "2f6c1b8a9d04"

settings = get_settings()


def _url(db_name: str) -> str:
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    )


@pytest.fixture
def migration_db(monkeypatch):
    maintenance_engine = sa.create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        with maintenance_engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except OperationalError:
        pytest.skip("Postgres is not reachable; this test requires docker-compose Postgres running.")

    test_db_name = f"minute_mig_test_{uuid.uuid4().hex[:10]}"
    with maintenance_engine.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{test_db_name}"'))

    test_engine = sa.create_engine(_url(test_db_name))
    monkeypatch.setattr(pgdb, "engine", test_engine)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, PRE_REVISION)

    try:
        yield test_engine, cfg
    finally:
        test_engine.dispose()
        with maintenance_engine.connect() as conn:
            conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": test_db_name},
            )
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
        maintenance_engine.dispose()


def _seed(conn: sa.Connection) -> None:
    conn.execute(
        sa.text(
            """
            INSERT INTO "user" (id, email, created_datetime, updated_datetime, data_retention_days) VALUES
              (gen_random_uuid(), 'alice@businessandtrade.gov.uk',   NOW(), NOW(), 365),
              (gen_random_uuid(), 'Bob@BusinessAndTrade.gov.uk',     NOW(), NOW(), NULL),
              (gen_random_uuid(), 'carol@other.gov.uk',              NOW(), NOW(), 90),
              (gen_random_uuid(), 'frank@dsit.gov.uk',               NOW(), NOW(), 200),
              (gen_random_uuid(), 'dave@sub.businessandtrade.gov.uk', NOW(), NOW(), 14),
              (gen_random_uuid(), 'eve@notbusinessandtrade.gov.uk',  NOW(), NOW(), 7);
            """
        )
    )


def test_only_target_domain_users_get_30_days(migration_db):
    engine, cfg = migration_db

    with engine.begin() as conn:
        _seed(conn)

    command.upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        retention = {
            r.email: r.data_retention_days
            for r in conn.execute(sa.text('SELECT email, data_retention_days FROM "user"')).all()
        }

        # Target domain (any case) set to 30.
        assert retention["alice@businessandtrade.gov.uk"] == 42
        assert retention["Bob@BusinessAndTrade.gov.uk"] == 42

        assert retention["frank@dsit.gov.uk"] == 42

        # Subdomain and lookalike domains are untouched.
        assert retention["carol@other.gov.uk"] == 90
        assert retention["dave@sub.businessandtrade.gov.uk"] == 14
        assert retention["eve@notbusinessandtrade.gov.uk"] == 7
