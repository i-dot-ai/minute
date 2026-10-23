"""Single source of truth for department-forced data-retention periods.

Must stay in step with the backfill in alembic revision 2f6c1b8a9d04.
"""

FORCED_RETENTION_DOMAINS: dict[str, int] = {
    "businessandtrade.gov.uk": 42,
    "dsit.gov.uk": 42,
}


def forced_retention_days(email: str) -> int | None:
    """Return the retention period fixed for this email's domain, else None."""
    domain = email.rsplit("@", 1)[-1].lower()
    return FORCED_RETENTION_DOMAINS.get(domain)
