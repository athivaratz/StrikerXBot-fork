import pytest

from bot.ai.provider import AIError, CUT_OFF, MAX_OUTPUT_TOKENS, NO_ANSWER
from bot.ai.reasoning import reasoning_field
from bot.config import _choice
from tests.test_provider import (
    PROMPT,
    SECRET_KEY,
    FakeResponse,
    FakeSession,
    _ok,
    _run,
    _status,
)

_EFFORTS = ("off", "low", "medium", "high")


def _printed(capsys: pytest.CaptureFixture[str]) -> str:
    text = capsys.readouterr().out
    assert SECRET_KEY not in text
    assert PROMPT not in text
    return text


def test_reasoning_field_maps_each_effort() -> None:
    assert reasoning_field("off") == {"enabled": False}
    assert reasoning_field("low") == {"effort": "low"}
    assert reasoning_field("medium") == {"effort": "medium"}
    assert reasoning_field("high") == {"effort": "high"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("off", "off"), (" LOW ", "low"), ("Medium", "medium"), ("high", "high")],
)
def test_choice_accepts_known_efforts(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: str,
) -> None:
    monkeypatch.setenv("AI_REASONING_EFFORT", raw)
    assert _choice("AI_REASONING_EFFORT", _EFFORTS, "low") == expected


def test_choice_rejects_an_unknown_effort(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("AI_REASONING_EFFORT", "max")
    assert _choice("AI_REASONING_EFFORT", _EFFORTS, "low") == "low"
    assert _printed(capsys) == (
        "AI_REASONING_EFFORT must be one of off, low, medium, high. Using low.\n"
    )


def test_request_uses_max_tokens_and_reasoning() -> None:
    session = FakeSession([_ok("hi")])
    _run(session, [], max_tokens=300, reasoning={"effort": "low"})
    assert session.bodies[0]["max_tokens"] == 300
    assert session.bodies[0]["reasoning"] == {"effort": "low"}


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_effort_is_sent_as_given(effort: str) -> None:
    session = FakeSession([_ok("hi")])
    _run(session, [], max_tokens=40, reasoning=reasoning_field(effort))
    assert session.bodies[0]["reasoning"] == {"effort": effort}
    assert session.bodies[0]["max_tokens"] == 40


def test_off_disables_reasoning() -> None:
    session = FakeSession([_ok("hi")])
    _run(session, [], max_tokens=40, reasoning=reasoning_field("off"))
    assert session.bodies[0]["reasoning"] == {"enabled": False}
    assert session.bodies[0]["max_tokens"] == 40


def test_omits_reasoning_when_unset() -> None:
    session = FakeSession([_ok("hi")])
    _run(session, [], reasoning=None)
    assert "reasoning" not in session.bodies[0]
    assert session.bodies[0]["max_tokens"] == MAX_OUTPUT_TOKENS


def _empty(reason: str) -> dict:
    return {"choices": [{"message": {"content": ""}, "finish_reason": reason}]}


def test_length_with_missing_content_is_cut_off() -> None:
    payload = {"choices": [{"message": {"content": None}, "finish_reason": "length"}]}
    session = FakeSession([FakeResponse(200, payload)])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == CUT_OFF


def test_length_with_empty_content_is_cut_off() -> None:
    session = FakeSession([FakeResponse(200, _empty("length"))])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == CUT_OFF


def test_stop_with_empty_content_is_no_answer() -> None:
    session = FakeSession([FakeResponse(200, _empty("stop"))])
    with pytest.raises(AIError) as caught:
        _run(session, [])
    assert str(caught.value) == NO_ANSWER


def test_400_with_reasoning_retries_without_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = FakeSession([_status(400), _ok("hello")])
    slept: list[float] = []
    reply = _run(session, slept, max_tokens=80, reasoning={"effort": "low"})
    assert reply.text == "hello"
    assert session.calls == 2
    assert slept == []
    assert session.bodies[0]["reasoning"] == {"effort": "low"}
    assert "reasoning" not in session.bodies[1]
    assert session.bodies[1]["max_tokens"] == 80
    assert _printed(capsys) == (
        "AI request failed with status 400. Retrying without reasoning settings.\n"
    )


def test_400_without_reasoning_does_not_retry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = FakeSession([_status(400), _ok("later")])
    with pytest.raises(AIError) as caught:
        _run(session, [], reasoning=None)
    assert str(caught.value) == NO_ANSWER
    assert session.calls == 1
    _printed(capsys)


def test_second_400_stops(capsys: pytest.CaptureFixture[str]) -> None:
    session = FakeSession([_status(400), _status(400), _ok("later")])
    with pytest.raises(AIError) as caught:
        _run(session, [], reasoning={"enabled": False})
    assert str(caught.value) == NO_ANSWER
    assert session.calls == 2
    assert "reasoning" not in session.bodies[1]
    text = _printed(capsys)
    assert "Retrying without reasoning settings." in text


def test_reasoning_retry_does_not_spend_a_server_attempt() -> None:
    session = FakeSession([_status(400), _status(500), _status(500), _ok("ok")])
    slept: list[float] = []
    reply = _run(session, slept, reasoning={"effort": "high"})
    assert reply.text == "ok"
    assert session.calls == 4
    assert slept == [1.0, 2.0]
    assert "reasoning" not in session.bodies[1]
