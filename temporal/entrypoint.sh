#!/bin/sh
# Replaces the deprecated temporalio/auto-setup image: prepares the Postgres schema and registers the
# default namespace, then hands off to the server's own entrypoint. Safe to run on every task start.
set -eu

: "${POSTGRES_SEEDS:?POSTGRES_SEEDS is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PWD:?POSTGRES_PWD is required}"
DB_PORT="${DB_PORT:-5432}"
# temporal-sql-tool reads its password from SQL_PASSWORD (the server reads POSTGRES_PWD).
SQL_PASSWORD="$POSTGRES_PWD"
export SQL_PASSWORD
DBNAME="${DBNAME:-temporal}"
VISIBILITY_DBNAME="${VISIBILITY_DBNAME:-temporal_visibility}"
SCHEMA_ROOT=/etc/temporal/schema/postgresql/v12
# BIND_ON_IP=0.0.0.0 (set in terraform) makes the frontend answer on loopback too.
ADDRESS="127.0.0.1:7233"

sql() { temporal-sql-tool --plugin postgres12 --ep "$POSTGRES_SEEDS" -u "$POSTGRES_USER" -p "$DB_PORT" "$@"; }

# `create` and `setup-schema` are not idempotent, so tolerate their failures; `update-schema` is
# idempotent and is retried until the database is reachable (it also applies future migrations).
prepare() {
  db="$1"
  dir="$2"
  sql --db "$db" create || true
  sql --db "$db" setup-schema -v 0.0 || true
  attempt=0
  until sql --db "$db" update-schema -d "$dir"; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
      echo "database $db not reachable after $attempt attempts" >&2
      exit 1
    fi
    echo "waiting for database $db ($attempt)..." >&2
    sleep 2
  done
}

prepare "$DBNAME" "$SCHEMA_ROOT/temporal/versioned"
prepare "$VISIBILITY_DBNAME" "$SCHEMA_ROOT/visibility/versioned"

# The server does not create the default namespace for us. Register it once the server answers, in
# the background so the server stays the foreground process and keeps handling SIGTERM.
(
  attempt=0
  until temporal operator cluster health --address "$ADDRESS" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 90 ]; then
      echo "server never became healthy; skipping namespace creation" >&2
      exit 0
    fi
    sleep 2
  done
  if ! temporal operator namespace describe -n default --address "$ADDRESS" >/dev/null 2>&1; then
    temporal operator namespace create -n default --address "$ADDRESS"
  fi
) &

exec /etc/temporal/entrypoint.sh
