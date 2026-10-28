"""Login rate limiter to prevent brute force attacks."""

import time
from collections import defaultdict

# In-memory attempt tracking: key -> list of timestamps
_failed_attempts = defaultdict(list)


def check_rate_limit(key, max_attempts=5, window_seconds=300):
    """
    Check if a key (e.g. IP or username) has exceeded failed attempt limits.
    Returns (is_allowed, seconds_remaining).
    """
    now = time.time()
    # Filter attempts within the window
    attempts = [t for t in _failed_attempts[key] if now - t < window_seconds]
    _failed_attempts[key] = attempts

    if len(attempts) >= max_attempts:
        oldest = attempts[0]
        remaining = int(window_seconds - (now - oldest))
        return False, max(1, remaining)
    return True, 0


def record_failed_attempt(key):
    """Record a failed login attempt for a key."""
    _failed_attempts[key].append(time.time())


def clear_failed_attempts(key):
    """Clear failed attempts for a key on successful login."""
    if key in _failed_attempts:
        del _failed_attempts[key]
