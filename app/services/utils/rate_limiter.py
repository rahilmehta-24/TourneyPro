"""
Rate Limiter Utility for Brute-force & Abuse Prevention (OWASP ASVS SEC-011, SEC-012, SEC-059)
The Baseline Society
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Tuple
from flask import request


_lock = Lock()
_attempts = defaultdict(list)


def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> Tuple[bool, int]:
    """
    Checks if a given key has exceeded the maximum number of requests
    within the specified time window.

    Returns:
        (is_allowed: bool, retry_after_seconds: int)
    """
    now = time.time()
    with _lock:
        timestamps = _attempts[key]
        cutoff = now - window_seconds
        # Retain only timestamps within the current window
        valid_timestamps = [t for t in timestamps if t > cutoff]
        _attempts[key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, retry_after

        valid_timestamps.append(now)
        return True, 0


def get_client_ip() -> str:
    """Safely extracts client IP address accounting for proxies."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def reset_rate_limit(key: str) -> None:
    """Clears rate limit records for a given key upon successful action."""
    with _lock:
        _attempts.pop(key, None)

