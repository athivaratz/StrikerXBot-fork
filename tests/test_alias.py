import pytest

from bot.ai.alias import INTRO_REMINDER, AliasError, add_reminder, validate_alias


def test_validate_alias_trims_and_collapses_spaces() -> None:
    assert validate_alias("  Pim   Narak  ") == "Pim Narak"
    assert validate_alias("  พิม  ") == "พิม"


def test_validate_alias_rejects_empty_long_and_markup() -> None:
    with pytest.raises(AliasError):
        validate_alias("")
    with pytest.raises(AliasError):
        validate_alias("   ")
    with pytest.raises(AliasError):
        validate_alias("a" * 33)
    assert validate_alias("a" * 32) == "a" * 32
    for bad in ("@everyone", "<@1>", "Pim`code`", "Ann\nBee", "Ann\rBee"):
        with pytest.raises(AliasError):
            validate_alias(bad)


def test_add_reminder_appends_to_the_last_chunk() -> None:
    chunks = ["hello", "there"]
    result = add_reminder(chunks)
    assert result == ["hello", "there\n" + INTRO_REMINDER]
    assert chunks == ["hello", "there"]


def test_add_reminder_starts_a_chunk_when_the_last_is_full() -> None:
    extra = "\n" + INTRO_REMINDER
    last = "x" * (2000 - len(extra) + 1)
    chunks = ["keep", last]
    result = add_reminder(chunks)
    assert result == ["keep", last, INTRO_REMINDER]
    assert chunks == ["keep", last]
