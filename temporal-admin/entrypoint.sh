#!/bin/sh
# A release task, never a server entrypoint. Fail immediately on SQL or migration errors.
set -eu
case "${1:-schema}" in schema|namespace) ;; *) echo "Expected schema or namespace" >&2; exit 1 ;; esac

if [ "${1:-schema}" = namespace ]; then
  : "${TEMPORAL_ADDRESS:?TEMPORAL_ADDRESS is required}"
  namespaces=$(temporal operator namespace list --address "$TEMPORAL_ADDRESS" --output json)
  exists=$(printf '%s' "$namespaces" | jq -r 'any(.[]; .namespaceInfo.name == "default")')
  if [ "$exists" = false ]; then
    temporal operator namespace create -n default --address "$TEMPORAL_ADDRESS"
  fi
  temporal operator namespace describe -n default --address "$TEMPORAL_ADDRESS"
  exit 0
fi

: "${POSTGRES_SEEDS:?POSTGRES_SEEDS is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PWD:?POSTGRES_PWD is required}"
export PGHOST="$POSTGRES_SEEDS" PGPORT="${DB_PORT:-5432}" PGUSER="$POSTGRES_USER" PGPASSWORD="$POSTGRES_PWD"
export SQL_PASSWORD="$POSTGRES_PWD"
if [ "${SQL_TLS:-false}" = true ]; then export PGSSLMODE=require; else export PGSSLMODE=disable; fi
DBNAME="${DBNAME:-temporal}"
VISIBILITY_DBNAME="${VISIBILITY_DBNAME:-temporal_visibility}"

sql() { temporal-sql-tool --plugin postgres12 --ep "$PGHOST" -u "$PGUSER" -p "$PGPORT" "$@"; }
query() { psql -X -v ON_ERROR_STOP=1 -At "$@"; }

for database in "$DBNAME" "$VISIBILITY_DBNAME"; do
  exists=$(query -d postgres -v database="$database" <<'SQL'
SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database');
SQL
)
  if [ "$exists" = f ]; then sql --db "$database" create; fi
  exists=$(query -d "$database" <<'SQL'
SELECT to_regclass('public.schema_version') IS NOT NULL;
SQL
)
  if [ "$exists" = f ]; then
    # Never initialise over an existing non-empty schema.
    tables=$(query -d "$database" -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
    [ "$tables" = 0 ] || { echo "Refusing to initialise non-empty database $database" >&2; exit 1; }
    sql --db "$database" setup-schema -v 0.0
  fi
  case "$database" in
    "$DBNAME") schema=temporal ;;
    *) schema=visibility ;;
  esac
  sql --db "$database" update-schema -d "/etc/temporal/schema/postgresql/v12/$schema/versioned"
done

# Local Compose uses its existing user; production supplies a dedicated, non-owner runtime role.
if [ -n "${TEMPORAL_RUNTIME_PASSWORD:-}" ]; then
  query -d postgres -v password="$TEMPORAL_RUNTIME_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE temporal_runtime LOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'temporal_runtime') \gexec
-- Aurora's administrator is not a true superuser, so it cannot change the SUPERUSER attribute.
ALTER ROLE temporal_runtime WITH LOGIN PASSWORD :'password' NOCREATEDB NOCREATEROLE;
SQL
  superuser=$(query -d postgres -c "SELECT rolsuper FROM pg_roles WHERE rolname = 'temporal_runtime'")
  [ "$superuser" = f ] || { echo "Refusing to use a superuser as temporal_runtime" >&2; exit 1; }
  for database in "$DBNAME" "$VISIBILITY_DBNAME"; do
    query -d "$database" <<'SQL'
GRANT USAGE ON SCHEMA public TO temporal_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO temporal_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO temporal_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO temporal_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO temporal_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
  done
fi
