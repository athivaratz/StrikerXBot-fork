"""Discord stand-ins for the PDF command. They record calls and raise on demand."""

from types import SimpleNamespace

import discord


def http_error(status: int) -> discord.HTTPException:
    response = SimpleNamespace(status=status, reason="x")
    return discord.HTTPException(response, "boom")


class FakeResponse:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.deferred = False
        self.defer_kwargs: dict[str, object] = {}
        self.message_kwargs: dict[str, object] | None = None

    def is_done(self) -> bool:
        return self.deferred or self.message_kwargs is not None

    async def defer(self, **kwargs: object) -> None:
        self.events.append("defer")
        self.deferred = True
        self.defer_kwargs = kwargs

    async def send_message(self, text: str, **kwargs: object) -> None:
        self.events.append("send_message")
        self.message_kwargs = {"text": text, **kwargs}


class FakeFollowup:
    def __init__(self, events: list[str], *, fail_upload: bool) -> None:
        self.events = events
        self.fail_upload = fail_upload
        self.calls: list[dict[str, object]] = []

    async def send(self, *args: object, **kwargs: object) -> None:
        if self.fail_upload and "file" in kwargs:
            self.events.append("upload")
            raise http_error(413)
        self.events.append("followup")
        self.calls.append({"args": args, **kwargs})


class FakeInteraction:
    def __init__(self, *, fail_delete: bool = False, fail_upload: bool = False) -> None:
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response.events, fail_upload=fail_upload)
        self.fail_delete = fail_delete

    async def delete_original_response(self) -> None:
        self.response.events.append("delete")
        if self.fail_delete:
            raise http_error(403)


class FakeFile:
    def __init__(self, filename: str, *, fail_read: bool = False) -> None:
        self.filename = filename
        self.size = 20
        self.fail_read = fail_read

    async def read(self) -> bytes:
        if self.fail_read:
            raise http_error(500)
        return b"%PDF"
