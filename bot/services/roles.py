"""Role hierarchy checks that do not need a Discord connection.

None means the change is allowed. Any other return is a one-line refusal.
"""

from typing import Protocol


class RoleLike(Protocol):
    id: int
    position: int
    managed: bool
    name: str

    def is_default(self) -> bool: ...


class MemberLike(Protocol):
    id: int
    top_role: RoleLike


class RosterMember(MemberLike, Protocol):
    roles: list[RoleLike]


class GuildLike(Protocol):
    owner_id: int
    default_role: RoleLike


def _is_everyone(role: RoleLike, guild: GuildLike) -> bool:
    if role.is_default():
        return True
    return role == guild.default_role


def _is_owner(actor: MemberLike, guild: GuildLike) -> bool:
    return guild.owner_id == actor.id


def check_role_change(
    actor: MemberLike,
    target: MemberLike,
    role: RoleLike,
    bot_member: MemberLike,
    guild: GuildLike,
) -> str | None:
    if _is_everyone(role, guild):
        return "That role is @everyone."
    if role.managed:
        return "That role is managed by an integration."
    owner = _is_owner(actor, guild)
    if not owner and role.position >= actor.top_role.position:
        return "That role is at or above your highest role."
    if role.position >= bot_member.top_role.position:
        return "That role is at or above my highest role."
    if target.id == guild.owner_id and not owner:
        return "You cannot change the server owner's roles."
    if not owner and target.top_role.position >= actor.top_role.position:
        return "That member's highest role is at or above yours."
    return None


def plan_replace(
    actor: MemberLike,
    target: RosterMember,
    new_role: RoleLike,
    bot_member: MemberLike,
    guild: GuildLike,
) -> tuple[list[RoleLike], list[RoleLike]]:
    """Split current roles into ones we can remove and ones we must leave."""
    remove: list[RoleLike] = []
    skip: list[RoleLike] = []
    owner = _is_owner(actor, guild)
    for role in target.roles:
        if _is_everyone(role, guild):
            continue
        # The caller adds this role after the removals, so it must stay put.
        if role.id == new_role.id:
            continue
        above_bot = role.position >= bot_member.top_role.position
        above_actor = role.position >= actor.top_role.position
        if role.managed or above_bot or (above_actor and not owner):
            skip.append(role)
            continue
        remove.append(role)
    return remove, skip
