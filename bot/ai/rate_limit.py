"""Per-user request cap and daily token budget.

Request counts stay in memory and clear on restart. Token totals live in
SQLite so a restart does not reset the day. The day is a date at a fixed
UTC+7 offset.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from bot.storage import Store

# Fixed offset. zoneinfo needs the tzdata package on Windows, which we do not install.
UTC_PLUS_7 = timezone(timedelta(hours=7))
WINDOW_SECONDS = 60

RATE_MESSAGE = "Please wait a minute before asking again."
BUDGET_MESSAGE = (
    "You have used today's AI token budget. It resets at midnight (UTC+7)."
)


class RequestLimit:
    """Fixed window. A sliding window is harder to explain for the same cap."""

    def __init__(self, max_requests: int, now: Callable[[], float]) -> None:
        self.max_requests = max_requests
        self._now = now
        self._buckets: dict[int, tuple[int, float]] = {}

    def allow(self, user_id: int) -> bool:
        now = self._now()
        count, reset_at = self._buckets.get(user_id, (0, 0.0))
        if now >= reset_at:
            self._buckets[user_id] = (1, now + WINDOW_SECONDS)
            return True
        if count >= self.max_requests:
            return False
        self._buckets[user_id] = (count + 1, reset_at)
        return True


class TokenBudget:
    """Counts tokens per user until the next midnight at UTC+7."""

    def __init__(
        self, daily_limit: int, now: Callable[[], datetime], store: Store
    ) -> None:
        self.daily_limit = daily_limit
        self._now = now
        self._store = store

    def bind(self, store: Store) -> None:
        self._store = store

    def _day(self) -> str:
        current = self._now()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(UTC_PLUS_7).date().isoformat()

    async def used(self, user_id: int) -> int:
        return await self._store.get_tokens(user_id, self._day())

    async def allow(self, user_id: int) -> bool:
        return await self.used(user_id) < self.daily_limit

    async def add(self, user_id: int, tokens: int) -> None:
        if tokens < 0:
            tokens = 0
        await self._store.add_tokens(user_id, self._day(), tokens)


async def gate(
    user_id: int,
    owners: frozenset[int],
    limiter: RequestLimit,
    budget: TokenBudget,
) -> str | None:
    """Owners skip both limits. A sentence means the user should wait."""
    if user_id in owners:
        return None
    if not limiter.allow(user_id):
        return RATE_MESSAGE
    if not await budget.allow(user_id):
        return BUDGET_MESSAGE
    return None
