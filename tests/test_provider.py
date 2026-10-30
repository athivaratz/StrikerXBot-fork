import asyncio

import pytest

from bot.ai.provider import AIError, BUSY, NO_ANSWER, TOO_LONG, chat

SECRET_KEY = "SECRET_API_KEY"
PROMPT = "SECRET_PROMPT_TEXT"
MESSAGES = [{"role": "user", "content": PROMPT}]


class FakeResponse:
    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def read(self) -> bytes:
        return b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> bool:
        return False


class FakeSession:
    def __init__(self, items: list) -> None:
        self._items = list(items)
        self.calls = 0
        self.headers = None
        self.bodies: list = []

    def post(self, url: str, **kwargs):
        self.calls += 1
        self.headers = kwargs.get("headers")
        self.bodies.append(kwargs.get("json"))
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _ok(text: str, usage: dict | None = None) -> FakeResponse:
    payload: dict = {"choices": [{"message": {"content": text}}]}
    if usage is not None:
        payload["usage"] = usage
    return FakeResponse(200, payload)


def _status(code: int) -> FakeResponse:
    return FakeResponse(code, {})


def _run(session: FakeSession, slept: list[float], **extra: object):
    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    return asyncio.run(
        chat(
            MESSAGES,
            "test-model",
            session=session,
            api_key=SECRET_KEY,
            sleep=sleep,
            **extra,
        )
    )


def test_retries_429_then_succeeds(capsys):
    session = FakeSession(
        [_status(429), _ok("hello", {"prompt_tokens": 2, "completion_tokens": 3})]
    )
    slept: list[float] = []
    reply = _run(session, slept)
    assert reply.text == "hello"
    assert (reply.prompt_tokens, reply.completion_tokens) == (2, 3)
    assert session.calls == 2
    assert slept == [1.0]
    assert session.headers["Authorization"] == f"Bearer {SECRET_KEY}"
    captured = capsys.readouterr().out
    assert SECRET_KEY not in captured
    assert PROMPT not in captured


def test_retries_twice_on_server_errors():
    session = FakeSession(
        [
            _status(500),
            _status(502),
            _ok("ok", {"prompt_tokens": 1, "completion_tokens": 1}),
        ]
    )
    slept: list[float] = []
    reply = _run(session, slept)
    assert reply.text == "ok"
    assert session.calls == 3
    assert slept == [1.0, 2.0]


def test_raises_after_two_retries():
    session = FakeSession([_status(500), _status(500), _status(500)])
    slept: list[float] = []
    with pytest.raises(AIError) as caught:
        _run(session, slept)
    assert str(caught.value) == BUSY
    assert session.calls == 3
    assert slept == [1.0, 2.0]


def test_bad_request_does_not_retry():
    session = FakeSession([_status(400)])
    slept: list[float] = []
    with pytest.raises(AIError) as caught:
        _run(session, slept)
    assert str(caught.value) == NO_ANSWER
    assert session.calls == 1
    assert slept == []


def test_timeout_does_not_retry():
    session = FakeSession([TimeoutError()])
    slept: list[float] = []
    with pytest.raises(AIError) as caught:
        _run(session, slept)
    assert str(caught.value) == TOO_LONG
    assert session.calls == 1
    assert slept == []


def test_missing_usage_estimates_completion_tokens():
    text = "abcd" * 3
    session = FakeSession([_ok(text)])
    reply = _run(session, [])
    assert reply.prompt_tokens == 0
    assert reply.completion_tokens == len(text) // 4


def test_empty_choices_raise():
    session = FakeSession([FakeResponse(200, {"choices": []})])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == NO_ANSWER


def test_null_content_raises():
    payload = {"choices": [{"message": {"content": None}}]}
    session = FakeSession([FakeResponse(200, payload)])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == NO_ANSWER


def test_empty_content_raises():
    payload = {"choices": [{"message": {"content": ""}}]}
    session = FakeSession([FakeResponse(200, payload)])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == NO_ANSWER
