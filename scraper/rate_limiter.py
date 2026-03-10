from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

try:
    from fake_useragent import UserAgent as _FakeUA

    _fua = _FakeUA()

    def random_user_agent() -> str:
        try:
            return _fua.random
        except Exception:
            return random.choice(USER_AGENTS)

except ImportError:

    def random_user_agent() -> str:
        return random.choice(USER_AGENTS)


class AsyncRateLimiter:
    def __init__(self, concurrency: int = 1, min_delay: float = 3.0, max_delay: float = 5.0):
        self._sem = asyncio.Semaphore(concurrency)
        self._min_delay = min_delay
        self._max_delay = max_delay

    @asynccontextmanager
    async def throttle(self):
        async with self._sem:
            yield
            await asyncio.sleep(random.uniform(self._min_delay, self._max_delay))
