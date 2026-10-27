# Keep the CLI for readiness checks only; schema tools run in the separate admin task.
# Both images use temporal/version.env, supplied by Make and Compose.
ARG TEMPORAL_VERSION=1.32.1

FROM temporalio/admin-tools:${TEMPORAL_VERSION} AS tools
FROM temporalio/server:${TEMPORAL_VERSION}

COPY --from=tools --chmod=755 /usr/local/bin/temporal /usr/local/bin/temporal

# The server image expects a dynamic-config file at this path; keep it minimal (no overrides).
COPY temporal/dynamicconfig/docker.yaml /etc/temporal/config/dynamicconfig/docker.yaml
