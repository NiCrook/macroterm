from __future__ import annotations

import functools
import os
import pickle
import sqlite3
import time
from typing import Any

from macroterm.logger import get_logger

logger = get_logger("cache")

_cache: dict[str, tuple[float, Any]] = {}


class _DiskCache:
    def __init__(self) -> None:
        data_dir = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
            "macroterm",
        )
        os.makedirs(data_dir, exist_ok=True)
        self._db_path = os.path.join(data_dir, "cache.db")
        self._con = sqlite3.connect(self._db_path, check_same_thread=False)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, expires REAL, value BLOB)"
        )
        self._con.execute("DELETE FROM cache WHERE expires < ?", (time.time(),))
        self._con.commit()

    def get(self, key: str) -> tuple[bool, Any]:
        row = self._con.execute(
            "SELECT expires, value FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return False, None
        expires, blob = row
        if time.time() >= expires:
            self._con.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._con.commit()
            return False, None
        return True, pickle.loads(blob)

    def set(self, key: str, value: Any, expires: float) -> None:
        self._con.execute(
            "INSERT OR REPLACE INTO cache (key, expires, value) VALUES (?, ?, ?)",
            (key, expires, pickle.dumps(value)),
        )
        self._con.commit()

    def clear(self, prefix: str | None = None) -> int:
        if prefix is None:
            cur = self._con.execute("DELETE FROM cache")
        else:
            cur = self._con.execute(
                "DELETE FROM cache WHERE key LIKE ?", (prefix + "%",)
            )
        self._con.commit()
        return cur.rowcount

    def __len__(self) -> int:
        row = self._con.execute("SELECT COUNT(*) FROM cache").fetchone()
        return row[0]


_disk_cache = _DiskCache()


def async_ttl_cache(ttl_seconds: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__qualname__}:{repr(args)}:{repr(kwargs)}"
            now = time.time()
            if key in _cache:
                expires, value = _cache[key]
                if now < expires:
                    logger.debug("memory cache hit", extra={"extra_fields": {
                        "func": func.__qualname__,
                    }})
                    return value

            hit, value = _disk_cache.get(key)
            if hit:
                logger.debug("disk cache hit", extra={"extra_fields": {
                    "func": func.__qualname__,
                }})
                _cache[key] = (now + ttl_seconds, value)
                return value

            logger.debug("cache miss", extra={"extra_fields": {
                "func": func.__qualname__,
            }})
            result = await func(*args, **kwargs)
            expires = now + ttl_seconds
            _cache[key] = (expires, result)
            _disk_cache.set(key, result, expires)
            return result
        return wrapper
    return decorator


def clear_cache(prefix: str | None = None) -> int:
    if prefix is None:
        count = len(_cache)
        _cache.clear()
    else:
        keys = [k for k in _cache if k.startswith(prefix)]
        for k in keys:
            del _cache[k]
        count = len(keys)
    count += _disk_cache.clear(prefix)
    logger.info("cache cleared", extra={"extra_fields": {
        "prefix": prefix, "entries_removed": count,
    }})
    return count
