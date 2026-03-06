from __future__ import annotations

import functools
import time
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}


def async_ttl_cache(ttl_seconds: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__qualname__}:{repr(args)}:{repr(kwargs)}"
            now = time.monotonic()
            if key in _cache:
                expires, value = _cache[key]
                if now < expires:
                    return value
            result = await func(*args, **kwargs)
            _cache[key] = (now + ttl_seconds, result)
            return result
        return wrapper
    return decorator


def clear_cache(prefix: str | None = None) -> int:
    if prefix is None:
        count = len(_cache)
        _cache.clear()
        return count
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
    return len(keys)
