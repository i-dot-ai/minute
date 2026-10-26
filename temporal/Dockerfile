# temporalio/auto-setup is deprecated. The supported images split the server (temporalio/server)
# from the schema/CLI tooling (temporalio/admin-tools), so rebuild the one-container behaviour on top
# of them: the server, plus the sql-tool and CLI it needs, plus our entrypoint (temporal/entrypoint.sh).
# Bump TEMPORAL_VERSION to the current server release when you upgrade; both stages must match.
ARG TEMPORAL_VERSION=1.32.1

FROM temporalio/admin-tools:${TEMPORAL_VERSION} AS tools
FROM temporalio/server:${TEMPORAL_VERSION}

COPY --from=tools --chmod=755 /usr/local/bin/temporal-sql-tool /usr/local/bin/temporal-sql-tool
COPY --from=tools --chmod=755 /usr/local/bin/temporal /usr/local/bin/temporal
COPY --from=tools --chmod=755 /etc/temporal/schema /etc/temporal/schema

# The server image expects a dynamic-config file at this path; keep it minimal (no overrides).
COPY temporal/dynamicconfig/docker.yaml /etc/temporal/config/dynamicconfig/docker.yaml

COPY --chmod=755 temporal/entrypoint.sh /etc/temporal/minute-entrypoint.sh

ENTRYPOINT ["/etc/temporal/minute-entrypoint.sh"]
