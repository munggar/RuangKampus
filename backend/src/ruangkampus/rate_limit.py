from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class InProcessRateLimiter:
    """Fixed-window sliding log guard for single-process deployments.

    This is a per-process guard. Production deployments with multiple workers or
    instances must also apply shared rate limiting at the API gateway/WAF.
    """

    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                return False, retry_after
            events.append(now)
            if len(self._events) > 10_000:
                for stale_key in list(self._events)[:2_000]:
                    stale = self._events[stale_key]
                    while stale and stale[0] <= cutoff:
                        stale.popleft()
                    if not stale:
                        self._events.pop(stale_key, None)
            return True, 0


limiter = InProcessRateLimiter()
