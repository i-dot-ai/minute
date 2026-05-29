"""Integration test for migration c4f9d2a1b8e3 (dedupe users by email case).

Spins up a throwaway Postgres database, runs alembic up to the parent revision,
seeds synthetic case-variant duplicates plus their child rows, applies the
migration, and asserts that the merge, FK reassignment, lowercasing, and
unique-index enforcement all behave correctly.

Requires a running Postgres instance reachable via the POSTGRES_* settings
(e.g. `docker-compose up postgres`). The connecting user needs CREATEDB.
"""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, OperationalError

import common.database.postgres_database as pgdb
from alembic import command
from alembic.config import Config
from common.settings import get_settings

PRE_REVISION = "9d080ca9fe6c"
TARGET_REVISION = "c4f9d2a1b8e3"

settings = get_settings()


def _url(db_name: str) -> str:
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    )


@pytest.fixture
def migration_db(monkeypatch):
    """Create a throwaway DB at PRE_REVISION; yield (engine, alembic Config); drop after."""
    maintenance_engine = sa.create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        with maintenance_engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except OperationalError:
        pytest.skip("Postgres is not reachable; this test requires docker-compose Postgres running.")

    test_db_name = f"minute_mig_test_{uuid.uuid4().hex[:10]}"
    with maintenance_engine.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{test_db_name}"'))

    # Point both the project's engine and alembic env at the throwaway DB.
    test_engine = sa.create_engine(_url(test_db_name))
    monkeypatch.setattr(pgdb, "engine", test_engine)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, PRE_REVISION)

    try:
        yield test_engine, cfg
    finally:
        test_engine.dispose()
        with maintenance_engine.connect() as conn:
            # Kill any lingering connections before dropping.
            conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": test_db_name},
            )
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
        maintenance_engine.dispose()


# Fixed UUIDs make assertions easy to read.
ALICE_OLDEST = uuid.UUID("11111111-1111-1111-1111-111111111111")
ALICE_MIDDLE = uuid.UUID("22222222-2222-2222-2222-222222222222")
ALICE_NEWEST = uuid.UUID("33333333-3333-3333-3333-333333333333")
BOB = uuid.UUID("44444444-4444-4444-4444-444444444444")
CAROL_NO_CHILDREN = uuid.UUID("55555555-5555-5555-5555-555555555555")
CAROL_DUP = uuid.UUID("66666666-6666-6666-6666-666666666666")

TRANS_ON_ALICE_OLDEST = uuid.UUID("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1")
TRANS_ON_ALICE_MIDDLE = uuid.UUID("a2a2a2a2-a2a2-a2a2-a2a2-a2a2a2a2a2a2")
TRANS_ON_ALICE_NEWEST_1 = uuid.UUID("a3a3a3a3-a3a3-a3a3-a3a3-a3a3a3a3a3a3")
TRANS_ON_ALICE_NEWEST_2 = uuid.UUID("a4a4a4a4-a4a4-a4a4-a4a4-a4a4a4a4a4a4")
TRANS_ON_BOB = uuid.UUID("b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1")

REC_ON_ALICE_MIDDLE = uuid.UUID("c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1")
REC_ON_ALICE_NEWEST = uuid.UUID("c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2")
REC_ON_BOB = uuid.UUID("c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3")

TEMPLATE_ON_ALICE_NEWEST = uuid.UUID("d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1")


def _seed(conn: sa.Connection) -> None:
    """Insert the synthetic fixture.

    Three case-variant Alice rows, one Bob (untouched), and a Carol duplicate
    with no child rows (exercises the merge-with-nothing-to-reassign path).
    """
    conn.execute(
        sa.text(
            """
            INSERT INTO "user" (id, email, created_datetime, updated_datetime, data_retention_days) VALUES
              (:a_old,   'Alice@Example.com', '2025-01-01 00:00:00+00', '2025-01-01 00:00:00+00', NULL),
              (:a_mid,   'alice@example.com', '2025-02-01 00:00:00+00', '2025-02-01 00:00:00+00', 30),
              (:a_new,   'ALICE@EXAMPLE.COM', '2025-03-01 00:00:00+00', '2025-03-01 00:00:00+00', 7),
              (:bob,     'bob@example.com',   '2025-01-15 00:00:00+00', '2025-01-15 00:00:00+00', NULL),
              (:carol_a, 'Carol@x.com',       '2024-12-01 00:00:00+00', '2024-12-01 00:00:00+00', NULL),
              (:carol_b, 'carol@x.com',       '2025-04-01 00:00:00+00', '2025-04-01 00:00:00+00', 90);
            """
        ),
        {
            "a_old": ALICE_OLDEST,
            "a_mid": ALICE_MIDDLE,
            "a_new": ALICE_NEWEST,
            "bob": BOB,
            "carol_a": CAROL_NO_CHILDREN,
            "carol_b": CAROL_DUP,
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO transcription (id, user_id, created_datetime, updated_datetime) VALUES
              (:t_old,    :a_old, NOW(), NOW()),
              (:t_mid,    :a_mid, NOW(), NOW()),
              (:t_new_1,  :a_new, NOW(), NOW()),
              (:t_new_2,  :a_new, NOW(), NOW()),
              (:t_bob,    :bob,   NOW(), NOW());
            """
        ),
        {
            "t_old": TRANS_ON_ALICE_OLDEST,
            "t_mid": TRANS_ON_ALICE_MIDDLE,
            "t_new_1": TRANS_ON_ALICE_NEWEST_1,
            "t_new_2": TRANS_ON_ALICE_NEWEST_2,
            "t_bob": TRANS_ON_BOB,
            "a_old": ALICE_OLDEST,
            "a_mid": ALICE_MIDDLE,
            "a_new": ALICE_NEWEST,
            "bob": BOB,
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO recording (id, user_id, s3_file_key, created_datetime) VALUES
              (:r_mid, :a_mid, 'k-mid', NOW()),
              (:r_new, :a_new, 'k-new', NOW()),
              (:r_bob, :bob,   'k-bob', NOW());
            """
        ),
        {
            "r_mid": REC_ON_ALICE_MIDDLE,
            "r_new": REC_ON_ALICE_NEWEST,
            "r_bob": REC_ON_BOB,
            "a_mid": ALICE_MIDDLE,
            "a_new": ALICE_NEWEST,
            "bob": BOB,
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO user_template
              (id, user_id, name, content, description, type, created_datetime, updated_datetime)
            VALUES
              (:t, :u, 'Notes', '<p>x</p>', '', 'DOCUMENT', NOW(), NOW());
            """
        ),
        {"t": TEMPLATE_ON_ALICE_NEWEST, "u": ALICE_NEWEST},
    )


def test_migration_merges_duplicates_reassigns_fks_and_lowercases(migration_db):
    engine, cfg = migration_db

    with engine.begin() as conn:
        _seed(conn)

    command.upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        rows = conn.execute(sa.text('SELECT id, email FROM "user" ORDER BY created_datetime')).all()
        ids_by_email = {r.email: r.id for r in rows}

        # Three users remain: oldest Alice, Bob, oldest Carol.
        assert {r.email for r in rows} == {"alice@example.com", "bob@example.com", "carol@x.com"}
        assert ids_by_email["alice@example.com"] == ALICE_OLDEST
        assert ids_by_email["carol@x.com"] == CAROL_NO_CHILDREN
        assert ids_by_email["bob@example.com"] == BOB

        # All emails are lowercased (even the ones that started lowercase, no-op).
        assert all(r.email == r.email.lower() for r in rows)

        # All four "Alice" transcriptions now point at the kept Alice.
        alice_trans = (
            conn.execute(
                sa.text("SELECT id FROM transcription WHERE user_id = :u ORDER BY id"),
                {"u": ALICE_OLDEST},
            )
            .scalars()
            .all()
        )
        assert set(alice_trans) == {
            TRANS_ON_ALICE_OLDEST,
            TRANS_ON_ALICE_MIDDLE,
            TRANS_ON_ALICE_NEWEST_1,
            TRANS_ON_ALICE_NEWEST_2,
        }

        # Bob's transcription is untouched.
        bob_trans = conn.execute(
            sa.text("SELECT user_id FROM transcription WHERE id = :t"),
            {"t": TRANS_ON_BOB},
        ).scalar_one()
        assert bob_trans == BOB

        # Recordings reassigned to the kept Alice; Bob's untouched.
        recs = conn.execute(sa.text("SELECT id, user_id FROM recording")).all()
        rec_owner = {r.id: r.user_id for r in recs}
        assert rec_owner[REC_ON_ALICE_MIDDLE] == ALICE_OLDEST
        assert rec_owner[REC_ON_ALICE_NEWEST] == ALICE_OLDEST
        assert rec_owner[REC_ON_BOB] == BOB

        # User template reassigned to the kept Alice.
        template_owner = conn.execute(
            sa.text("SELECT user_id FROM user_template WHERE id = :t"),
            {"t": TEMPLATE_ON_ALICE_NEWEST},
        ).scalar_one()
        assert template_owner == ALICE_OLDEST

        # No FK references survive to deleted users.
        # Table/column names are hardcoded in this loop, so the f-string is safe (noqa S608).
        for table, col in [("transcription", "user_id"), ("recording", "user_id"), ("user_template", "user_id")]:
            query = f'SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} NOT IN (SELECT id FROM "user")'  # noqa: S608
            orphans = conn.execute(sa.text(query)).scalar_one()
            assert orphans == 0, f"orphaned {table}.{col} rows after migration"


def test_migration_enforces_case_insensitive_uniqueness(migration_db):
    engine, cfg = migration_db
    command.upgrade(cfg, TARGET_REVISION)

    # Inserting a fresh user is fine.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO "user" (id, email, created_datetime, updated_datetime) '
                "VALUES (gen_random_uuid(), :e, NOW(), NOW())"
            ),
            {"e": "dave@example.com"},
        )

    # A case-variant of the same email is rejected by the functional unique index.
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO "user" (id, email, created_datetime, updated_datetime) '
                "VALUES (gen_random_uuid(), :e, NOW(), NOW())"
            ),
            {"e": "DAVE@Example.com"},
        )


def test_migration_is_a_noop_when_there_are_no_duplicates(migration_db):
    engine, cfg = migration_db

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO "user" (id, email, created_datetime, updated_datetime) ' "VALUES (:i, :e, NOW(), NOW())"
            ),
            {"i": BOB, "e": "bob@example.com"},
        )

    command.upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        rows = conn.execute(sa.text('SELECT id, email FROM "user"')).all()
        assert len(rows) == 1
        assert rows[0].id == BOB
        assert rows[0].email == "bob@example.com"


def test_downgrade_drops_only_the_unique_index(migration_db):
    engine, cfg = migration_db
    command.upgrade(cfg, TARGET_REVISION)

    # Seed a single user so we can verify rows survive the downgrade.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO "user" (id, email, created_datetime, updated_datetime) ' "VALUES (:i, :e, NOW(), NOW())"
            ),
            {"i": BOB, "e": "bob@example.com"},
        )

    command.downgrade(cfg, PRE_REVISION)

    with engine.connect() as conn:
        # The unique index is gone.
        present = conn.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE schemaname = 'public' " "AND indexname = 'ix_user_email_lower'")
        ).first()
        assert present is None

        # The user row is still there — downgrade does not un-merge.
        rows = conn.execute(sa.text('SELECT email FROM "user"')).all()
        assert {r.email for r in rows} == {"bob@example.com"}
