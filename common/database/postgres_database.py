import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, create_engine

from common.settings import get_settings

logger = logging.getLogger(__name__)

# Only create the settings object once

settings = get_settings()


# Get database connection details from environment variables
DB_USER = settings.POSTGRES_USER
DB_PASSWORD = settings.POSTGRES_PASSWORD
DB_HOST = settings.POSTGRES_HOST
DB_PORT = settings.POSTGRES_PORT
DB_NAME = settings.POSTGRES_DB

# Use psycopg2 for synchronous operations
SYNC_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Use asyncpg for asynchronous operations
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SYNC_DATABASE_URL, pool_size=20, max_overflow=30, pool_timeout=60, pool_pre_ping=True)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    pool_pre_ping=True,
    # Sets the cutoff for the pg_trgm `%` operator used by transcription title search. It is a
    # GUC rather than a query argument, so it is applied once per connection at startup instead
    # of costing a round-trip per search. asyncpg sends these in the connection startup packet.
    connect_args={"server_settings": {"pg_trgm.similarity_threshold": str(settings.SEARCH_SIMILARITY_THRESHOLD)}},
)


def SessionLocal() -> Session:  # noqa: N802
    return Session(engine)
