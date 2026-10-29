ARG TEMPORAL_VERSION=1.32.1
FROM temporalio/admin-tools:${TEMPORAL_VERSION}

USER root
RUN apk add --no-cache postgresql-client jq
COPY --chmod=755 temporal-admin/entrypoint.sh /etc/temporal/minute-admin.sh
USER temporal
ENTRYPOINT ["/etc/temporal/minute-admin.sh"]
