"""Role hierarchy rules, without Discord."""

from dataclasses import dataclass

from bot.services.roles import check_role_change, plan_replace


@dataclass
class Role:
    id: int
    position: int
    name: str = "role"
    managed: bool = False
    default: bool = False

    def is_default(self) -> bool:
        return self.default


@dataclass
class Member:
    id: int
    top_role: Role
    roles: list[Role]


@dataclass
class Guild:
    owner_id: int
    default_role: Role


def _people() -> tuple[Guild, Member, Member, Member]:
    everyone = Role(1, 0, name="@everyone", default=True)
    guild = Guild(99, everyone)
    actor = Member(10, Role(2, 5, name="mod"), [])
    target = Member(11, Role(3, 2, name="member"), [])
    bot_member = Member(12, Role(4, 10, name="bot"), [])
    return guild, actor, target, bot_member


def test_allows_a_lower_role() -> None:
    guild, actor, target, bot_member = _people()
    role = Role(20, 3, name="helper")
    assert check_role_change(actor, target, role, bot_member, guild) is None


def test_refuses_everyone_and_the_default_role_object() -> None:
    guild, actor, target, bot_member = _people()
    assert check_role_change(actor, target, guild.default_role, bot_member, guild) == (
        "That role is @everyone."
    )
    plain = Role(1, 0, name="@everyone", default=False)
    guild.default_role = plain
    assert check_role_change(actor, target, plain, bot_member, guild) == (
        "That role is @everyone."
    )


def test_refuses_managed_roles() -> None:
    guild, actor, target, bot_member = _people()
    role = Role(20, 3, name="integration", managed=True)
    assert check_role_change(actor, target, role, bot_member, guild) == (
        "That role is managed by an integration."
    )


def test_refuses_roles_at_or_above_the_actor_or_the_bot() -> None:
    guild, actor, target, bot_member = _people()
    at_actor = Role(20, actor.top_role.position, name="equal")
    assert "your highest role" in (
        check_role_change(actor, target, at_actor, bot_member, guild) or ""
    )
    owner = Member(guild.owner_id, Role(2, 1), [])
    at_bot = Role(21, bot_member.top_role.position, name="bot-high")
    assert "my highest role" in (
        check_role_change(owner, target, at_bot, bot_member, guild) or ""
    )


def test_refuses_a_target_at_or_above_the_actor_unless_owner() -> None:
    guild, actor, target, bot_member = _people()
    target.top_role = Role(3, actor.top_role.position, name="peer")
    role = Role(20, 1, name="low")
    assert "highest role is at or above yours" in (
        check_role_change(actor, target, role, bot_member, guild) or ""
    )
    owner = Member(guild.owner_id, Role(2, 1), [])
    assert check_role_change(owner, target, role, bot_member, guild) is None


def test_refuses_changing_the_owner_unless_you_are_the_owner() -> None:
    guild, actor, target, bot_member = _people()
    target.id = guild.owner_id
    target.top_role = Role(3, 1, name="owner-role")
    role = Role(20, 1, name="low")
    assert check_role_change(actor, target, role, bot_member, guild) == (
        "You cannot change the server owner's roles."
    )
    owner = Member(guild.owner_id, Role(2, 1), [])
    assert check_role_change(owner, target, role, bot_member, guild) is None


def test_plan_replace_skips_managed_and_high_roles() -> None:
    everyone = Role(1, 0, name="@everyone", default=True)
    low = Role(2, 1, name="low")
    managed = Role(3, 2, name="integration", managed=True)
    high = Role(4, 8, name="admin")
    guild = Guild(99, everyone)
    actor = Member(10, Role(5, 5, name="mod"), [])
    bot_member = Member(12, Role(6, 6, name="bot"), [])
    target = Member(11, high, [everyone, low, managed, high])
    remove, skip = plan_replace(actor, target, bot_member, guild)
    assert [item.name for item in remove] == ["low"]
    assert [item.name for item in skip] == ["integration", "admin"]


def test_plan_replace_owner_can_remove_roles_above_them() -> None:
    everyone = Role(1, 0, name="@everyone", default=True)
    low = Role(2, 1, name="low")
    managed = Role(3, 2, name="integration", managed=True)
    above_owner = Role(4, 8, name="admin")
    above_bot = Role(7, 12, name="over-bot")
    guild = Guild(10, everyone)
    actor = Member(10, Role(5, 4, name="owner"), [])
    bot_member = Member(12, Role(6, 10, name="bot"), [])
    target = Member(11, above_owner, [everyone, low, managed, above_owner, above_bot])
    remove, skip = plan_replace(actor, target, bot_member, guild)
    assert [item.name for item in remove] == ["low", "admin"]
    assert [item.name for item in skip] == ["integration", "over-bot"]
