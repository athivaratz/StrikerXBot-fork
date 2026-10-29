"""Per-user request cap and daily token budget.

Why in memory: this phase has no database, and both limits clear on restart.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

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

    def __init__(self, daily_limit: int, now: Callable[[], datetime]) -> None:
        self.daily_limit = daily_limit
        self._now = now
        self._used: dict[int, tuple[object, int]] = {}

    def _today(self):
        current = self._now()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(UTC_PLUS_7).date()

    def used(self, user_id: int) -> int:
        day, amount = self._used.get(user_id, (None, 0))
        if day != self._today():
            return 0
        return amount

    def allow(self, user_id: int) -> bool:
        return self.used(user_id) < self.daily_limit

    def add(self, user_id: int, tokens: int) -> None:
        if tokens < 0:
            tokens = 0
        day = self._today()
        stored_day, amount = self._used.get(user_id, (None, 0))
        if stored_day != day:
            amount = 0
        self._used[user_id] = (day, amount + tokens)


def gate(
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
    if not budget.allow(user_id):
        return BUDGET_MESSAGE
    return None
