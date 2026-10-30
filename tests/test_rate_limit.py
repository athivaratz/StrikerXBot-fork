import asyncio
from datetime import datetime, timezone

from bot.ai.rate_limit import (
    BUDGET_MESSAGE,
    RATE_MESSAGE,
    RequestLimit,
    TokenBudget,
    gate,
)
from bot.storage import Store


def test_allows_ten_then_blocks_until_the_window_resets():
    now = [0.0]
    limit = RequestLimit(10, lambda: now[0])
    for _ in range(10):
        assert limit.allow(1) is True
    assert limit.allow(1) is False
    now[0] = 60.0
    assert limit.allow(1) is True


def test_users_have_separate_windows():
    limit = RequestLimit(1, lambda: 0.0)
    assert limit.allow(1) is True
    assert limit.allow(1) is False
    assert limit.allow(2) is True


def test_owner_skips_rate_limit_and_budget(tmp_path):
    limit = RequestLimit(1, lambda: 0.0)
    clock = [datetime(2026, 10, 29, 16, 0, tzinfo=timezone.utc)]
    budget = TokenBudget(10, lambda: clock[0], Store(tmp_path / "budget.db"))
    assert limit.allow(5) is True
    asyncio.run(budget.add(5, 10))
    assert asyncio.run(gate(5, frozenset({5}), limit, budget)) is None
    assert asyncio.run(gate(5, frozenset(), limit, budget)) == RATE_MESSAGE


def test_budget_blocks_at_the_cap(tmp_path):
    clock = [datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)]
    budget = TokenBudget(100, lambda: clock[0], Store(tmp_path / "budget.db"))
    limit = RequestLimit(10, lambda: 0.0)
    asyncio.run(budget.add(1, 100))
    assert asyncio.run(gate(1, frozenset(), limit, budget)) == BUDGET_MESSAGE


def test_budget_persists_and_resets_at_17_utc(tmp_path):
    # 17:00 UTC is midnight at a fixed UTC+7 offset.
    clock = [datetime(2026, 10, 29, 16, 59, tzinfo=timezone.utc)]
    path = tmp_path / "budget.db"
    budget = TokenBudget(100, lambda: clock[0], Store(path))
    asyncio.run(budget.add(1, 100))
    reopened = TokenBudget(100, lambda: clock[0], Store(path))
    assert asyncio.run(reopened.used(1)) == 100
    assert asyncio.run(reopened.allow(1)) is False
    clock[0] = datetime(2026, 10, 29, 17, 0, tzinfo=timezone.utc)
    assert asyncio.run(reopened.allow(1)) is True
    assert asyncio.run(reopened.used(1)) == 0
