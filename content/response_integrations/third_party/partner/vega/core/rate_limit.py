"""Linear +2 second wait for consecutive Vega HTTP 429 responses."""

from __future__ import annotations

import time

from .constants import (
    MAX_CONSECUTIVE_429,
    MSG_RATE_LIMIT,
    RATE_LIMIT_INITIAL_WAIT_SECONDS,
    RATE_LIMIT_STEP_SECONDS,
)
from .exceptions import VegaRateLimitException


class RateLimitController:
    """Wait 2s, 4s, 6s... on consecutive 429s; give up on the 8th; reset after success."""

    def __init__(
        self,
        sleeper=time.sleep,
        initial_wait: int = RATE_LIMIT_INITIAL_WAIT_SECONDS,
        step: int = RATE_LIMIT_STEP_SECONDS,
        max_consecutive: int = MAX_CONSECUTIVE_429,
    ) -> None:
        self._sleeper = sleeper
        self._initial_wait = initial_wait
        self._step = step
        self._max_consecutive = max_consecutive
        self.next_wait = initial_wait
        self.consecutive = 0

    def on_success(self) -> None:
        self.next_wait = self._initial_wait
        self.consecutive = 0

    def on_429(self) -> int:
        self.consecutive += 1
        if self.consecutive >= self._max_consecutive:
            raise VegaRateLimitException(MSG_RATE_LIMIT)
        wait_seconds = self.next_wait
        self.next_wait += self._step
        self._sleeper(wait_seconds)
        return wait_seconds
