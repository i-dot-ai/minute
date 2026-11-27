from dataclasses import dataclass, field
from uuid import UUID

from .data import Permission


@dataclass(frozen=True)
class ActorPermissions:
    """A snapshot of what an actor can do across every context, resolved at once."""

    user_id: UUID
    personal: frozenset[Permission] = field(default_factory=frozenset)
    by_org: dict[UUID, frozenset[Permission]] = field(default_factory=dict)

    def permissions_for(self, org_id: UUID | None) -> frozenset[Permission]:
        if org_id is None:
            return self.personal
        return self.by_org.get(org_id, frozenset())
