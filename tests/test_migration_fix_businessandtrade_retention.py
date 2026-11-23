"""Exercise the backfill against an isolated temporary Postgres table."""

import sqlalchemy as sa

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from common.database.postgres_database import engine


def test_backfill_sets_only_exact_dbt_domain_to_30_days():
    users = [
        {"email": "alice@businessandtrade.gov.uk", "days": None},
        {"email": "Bob@BUSINESSANDTRADE.GOV.UK", "days": 90},
        {"email": "carol@businessandtrade.gov.uk", "days": 7},
        {"email": "dave@dsit.gov.uk", "days": None},
        {"email": "eve@sub.businessandtrade.gov.uk", "days": 90},
        {"email": "frank@notbusinessandtrade.gov.uk", "days": 7},
        {"email": "grace@businessandtrade.gov.uk.example.com", "days": None},
    ]
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    migration = scripts.get_revision("3e91a7c2d6b4")

    with engine.begin() as connection:
        # The temporary table shadows the real user table only on this connection.
        connection.execute(sa.text('CREATE TEMP TABLE "user" (email TEXT, data_retention_days INTEGER) ON COMMIT DROP'))
        connection.execute(sa.text('INSERT INTO "user" (email, data_retention_days) VALUES (:email, :days)'), users)
        with Operations.context(MigrationContext.configure(connection)):
            migration.module.upgrade()

        actual = dict(connection.execute(sa.text('SELECT email, data_retention_days FROM "user"')).all())
        assert actual == {user["email"]: 30 if index < 3 else user["days"] for index, user in enumerate(users)}

        with Operations.context(MigrationContext.configure(connection)):
            migration.module.downgrade()
        assert dict(connection.execute(sa.text('SELECT email, data_retention_days FROM "user"')).all()) == actual
