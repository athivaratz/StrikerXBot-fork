"""OpenRouter chat client.

Why a thin wrapper: callers should see reply text and token counts, not HTTP.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aiohttp

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
# One reply should fit in a few Discord messages.
MAX_OUTPUT_TOKENS = 1024
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3

BUSY = "The AI service is busy. Please try again in a moment."
TOO_LONG = "The AI service took too long. Please try again."
NO_ANSWER = "The AI service could not answer. Please try again."
CUT_OFF = "The answer was cut off before it finished. Please ask for a shorter answer."


class AIError(Exception):
    """Failure text that is safe to show in Discord."""


@dataclass(frozen=True)
class ChatReply:
    text: str
    prompt_tokens: int
    completion_tokens: int


class _Retry(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


class _RejectedReasoning(Exception):
    """Some models reject the reasoning field. One retry omits it."""


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _reply_from(payload: object) -> ChatReply:
    if not isinstance(payload, dict):
        raise AIError(NO_ANSWER)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIError(NO_ANSWER)
    choice = choices[0]
    if not isinstance(choice, dict):
        raise AIError(NO_ANSWER)
    message = choice.get("message")
    if not isinstance(message, dict):
        raise AIError(NO_ANSWER)
    content = message.get("content")
    if not isinstance(content, str) or content.strip() == "":
        # Reasoning can consume the whole max_tokens budget and leave no text.
        if choice.get("finish_reason") == "length":
            raise AIError(CUT_OFF)
        raise AIError(NO_ANSWER)
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return ChatReply(content, 0, len(content) // 4)
    return ChatReply(
        content,
        _count(usage.get("prompt_tokens")),
        _count(usage.get("completion_tokens")),
    )


async def _post(
    session: aiohttp.ClientSession,
    model: str,
    messages: list[dict[str, str]],
    api_key: str,
    max_tokens: int,
    reasoning: dict | None,
) -> ChatReply:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, object] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if reasoning is not None:
        body["reasoning"] = reasoning
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    async with session.post(
        CHAT_URL, json=body, headers=headers, timeout=timeout
    ) as response:
        status = response.status
        if status == 200:
            try:
                payload = await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError):
                raise AIError(NO_ANSWER) from None
            return _reply_from(payload)
        # Drop the body so the connection can be reused. Do not log it.
        await response.read()
        if status == 400 and reasoning is not None:
            print("AI request failed with status 400. Retrying without reasoning settings.")
            raise _RejectedReasoning
        print(f"AI request failed with status {status}")
        if status == 429 or 500 <= status <= 599:
            raise _Retry(status)
        raise AIError(NO_ANSWER)


async def chat(
    messages: list[dict[str, str]],
    model: str,
    *,
    session: aiohttp.ClientSession,
    api_key: str,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    reasoning: dict | None = None,
) -> ChatReply:
    """Retry only 429 and 5xx. A bad request should not be sent three times."""
    # A rejected reasoning field is one extra try, outside the 429 and 5xx budget.
    attempt = 0
    while attempt < MAX_ATTEMPTS:
        try:
            return await _post(session, model, messages, api_key, max_tokens, reasoning)
        except _RejectedReasoning:
            if reasoning is None:
                raise AIError(NO_ANSWER) from None
            reasoning = None
        except _Retry:
            if attempt == MAX_ATTEMPTS - 1:
                raise AIError(BUSY) from None
            await sleep(1.0 if attempt == 0 else 2.0)
            attempt += 1
        except TimeoutError:
            print("AI request timed out")
            raise AIError(TOO_LONG) from None
        except aiohttp.ClientError:
            print("AI request failed to connect")
            raise AIError(NO_ANSWER) from None
    raise AIError(BUSY)
