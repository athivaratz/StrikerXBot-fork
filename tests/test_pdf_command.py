"""Checks that /pdf-to-image failures never stay on the public thinking message."""

import asyncio
from collections.abc import Callable

import discord
import pytest

from bot.services.pdf_command import run_pdf_command
from bot.services.pdf_render import PdfRequestError
from bot.utils.discord_send import NO_MENTIONS
from tests.pdf_fakes import FakeFile, FakeInteraction

_PNG = b"\x89PNG"
Render = Callable[[bytes, int, int], bytes]


def _png(_data: bytes, _page: int, _dpi: int) -> bytes:
    return _PNG


def _run(
    interaction: FakeInteraction,
    file: FakeFile,
    render: Render = _png,
) -> None:
    asyncio.run(run_pdf_command(interaction, file, 1, 72, render=render))


def _private(interaction: FakeInteraction) -> dict[str, object]:
    assert len(interaction.followup.calls) == 1
    call = interaction.followup.calls[0]
    assert call["ephemeral"] is True
    assert call["allowed_mentions"] is NO_MENTIONS
    return call


def test_success_posts_the_image_without_deleting() -> None:
    interaction = FakeInteraction()
    _run(interaction, FakeFile("notes.pdf"))
    assert interaction.response.events == ["defer", "followup"]
    assert interaction.response.defer_kwargs.get("ephemeral", False) is False
    call = interaction.followup.calls[0]
    assert call.get("ephemeral", False) is False
    assert isinstance(call["file"], discord.File)
    assert call["allowed_mentions"] is NO_MENTIONS


def test_bad_extension_replies_before_defer() -> None:
    interaction = FakeInteraction()
    _run(interaction, FakeFile("notes.txt"))
    assert interaction.response.events == ["send_message"]
    sent = interaction.response.message_kwargs
    assert sent is not None
    assert sent["ephemeral"] is True
    assert sent["allowed_mentions"] is NO_MENTIONS
    assert interaction.followup.calls == []


def test_read_failure_is_a_private_download_message() -> None:
    interaction = FakeInteraction()
    _run(interaction, FakeFile("notes.pdf", fail_read=True))
    assert interaction.response.events == ["defer", "delete", "followup"]
    call = _private(interaction)
    assert call["args"] == ("I could not download that file. Please try again.",)


def test_render_error_is_private() -> None:
    def render(_data: bytes, _page: int, _dpi: int) -> bytes:
        raise PdfRequestError("That PDF is password protected.")

    interaction = FakeInteraction()
    _run(interaction, FakeFile("notes.pdf"), render)
    assert interaction.response.events == ["defer", "delete", "followup"]
    call = _private(interaction)
    assert call["args"] == ("That PDF is password protected.",)


def test_unexpected_error_stays_private(capsys: pytest.CaptureFixture[str]) -> None:
    def render(_data: bytes, _page: int, _dpi: int) -> bytes:
        raise RuntimeError("disk path /secret")

    interaction = FakeInteraction()
    _run(interaction, FakeFile("notes.pdf"), render)
    call = _private(interaction)
    assert call["args"] == ("Something went wrong while rendering that page.",)
    assert capsys.readouterr().out == "RuntimeError\n"


def test_delete_failure_sends_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    interaction = FakeInteraction(fail_delete=True)
    _run(interaction, FakeFile("notes.pdf", fail_read=True))
    assert interaction.followup.calls == []
    assert interaction.response.events == ["defer", "delete"]
    assert capsys.readouterr().out == "403\n"


def test_upload_failure_sends_a_private_size_message() -> None:
    interaction = FakeInteraction(fail_upload=True)
    _run(interaction, FakeFile("notes.pdf"))
    assert interaction.response.events == ["defer", "upload", "delete", "followup"]
    call = _private(interaction)
    assert call["args"] == ("That image is too large to upload. Try a lower dpi.",)
