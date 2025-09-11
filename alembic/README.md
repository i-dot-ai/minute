# Database

example uses a persistent data store using postgresql, running in a docker container locally (called db), and using aurora when deployed to aws.

Models for the database are kept in `common/database/postgres_models.py`.

Pydantic models for the database interaction are kept in `common/database/pydantic_schemas.py`.

A function interface for interacting with the database is kept in `common/database/postgres_interface.py`.

We use SQLAlchemy for database connections, and alembic for tracking migrations. The `alembic.ini` file at the root of the project handles alembic configuration and the connection string to the db to action against.

*When adding new models, import each model into `alembic/env.py` so that alembic reads it into the config.*

Run `poetry run alembic revision --autogenerate` to generate a new migration, and `poetry run alembic upgrade head` to run the upgrade to apply the new migration.