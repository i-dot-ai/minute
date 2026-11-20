"""Authorization layer for Minute."""

from common.authz.catalogue import Permission

__all__ = [
    "Permission",
    "context_permissions",
    "user_has_permission",
]

_RESOLVER_EXPORTS = {"context_permissions", "user_has_permission"}


def __getattr__(name: str):
    """Lazily expose resolver functions without importing it at package load.

    ``common.database.postgres_models`` imports ``Permission`` from this package;
    eagerly importing ``resolver`` here (which imports the models) would create a
    circular import. Deferring the resolver import to first attribute access
    breaks that cycle while keeping ``from common.authz import context_permissions``
    working.
    """
    if name in _RESOLVER_EXPORTS:
        from common.authz import resolver

        return getattr(resolver, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
